"""Слой доступа к данным (SQLite через aiosqlite).

Все данные изолированы по user_id (Telegram ID). База создаётся автоматически
при первом запуске; данные переживают перезапуск бота.
"""
import hashlib
from datetime import datetime
from typing import Optional, Iterable

import aiosqlite

import config

_db: Optional[aiosqlite.Connection] = None


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def connect() -> None:
    global _db
    _db = await aiosqlite.connect(config.DATABASE_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA foreign_keys = ON")
    await _init()


async def close() -> None:
    if _db is not None:
        await _db.close()


async def _init() -> None:
    await _db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            telegram_id   INTEGER PRIMARY KEY,
            username      TEXT,
            is_authorized INTEGER NOT NULL DEFAULT 0,
            is_banned     INTEGER NOT NULL DEFAULT 0,
            is_admin      INTEGER NOT NULL DEFAULT 0,
            balance       REAL    NOT NULL DEFAULT 0,
            tabla_count   INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            amount        REAL    NOT NULL,
            balance_after REAL    NOT NULL,
            type          TEXT    NOT NULL,
            comment       TEXT,
            created_at    TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS resources (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            value      TEXT    NOT NULL,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS active_process (
            user_id         INTEGER PRIMARY KEY,
            current_step    INTEGER NOT NULL DEFAULT 0,
            started_at      TEXT,
            resource_number INTEGER,
            result_value    REAL,
            profit          REAL
        );

        CREATE TABLE IF NOT EXISTS processes (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            started_at       TEXT,
            finished_at      TEXT,
            duration_seconds REAL,
            profit           REAL,
            resource_number  INTEGER,
            result_value     REAL,
            status           TEXT
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_tx_user      ON transactions(user_id);
        CREATE INDEX IF NOT EXISTS idx_res_user     ON resources(user_id);
        CREATE INDEX IF NOT EXISTS idx_proc_user    ON processes(user_id);
        """
    )
    await _db.commit()
    if await get_setting("password_hash") is None:
        await set_password(config.DEFAULT_PASSWORD)


# ---------------------------------------------------------------- settings ---
async def get_setting(key: str) -> Optional[str]:
    cur = await _db.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = await cur.fetchone()
    return row["value"] if row else None


async def set_setting(key: str, value: str) -> None:
    await _db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    await _db.commit()


async def set_password(password: str) -> None:
    await set_setting("password_hash", _hash_password(password))


async def check_password(password: str) -> bool:
    stored = await get_setting("password_hash")
    return stored is not None and stored == _hash_password(password)


# ------------------------------------------------------------------- users ---
async def get_user(uid: int):
    cur = await _db.execute("SELECT * FROM users WHERE telegram_id = ?", (uid,))
    return await cur.fetchone()


async def get_or_create_user(uid: int, username: Optional[str]):
    row = await get_user(uid)
    if row is None:
        is_admin = 1 if config.INITIAL_ADMIN_ID and uid == config.INITIAL_ADMIN_ID else 0
        is_auth = is_admin  # первый администратор авторизуется автоматически
        await _db.execute(
            "INSERT INTO users (telegram_id, username, is_authorized, is_admin, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (uid, username, is_auth, is_admin, now_iso()),
        )
        await _db.commit()
        return await get_user(uid)

    # поддерживаем username в актуальном состоянии
    if username and row["username"] != username:
        await _db.execute(
            "UPDATE users SET username = ? WHERE telegram_id = ?", (username, uid)
        )
        await _db.commit()
    # гарантируем права для первого администратора
    if config.INITIAL_ADMIN_ID and uid == config.INITIAL_ADMIN_ID and not row["is_admin"]:
        await _db.execute(
            "UPDATE users SET is_admin = 1, is_authorized = 1 WHERE telegram_id = ?",
            (uid,),
        )
        await _db.commit()
    return await get_user(uid)


async def ensure_user(uid: int) -> None:
    """Создать пустую запись пользователя, если её ещё нет (для админ-действий)."""
    if await get_user(uid) is None:
        await _db.execute(
            "INSERT INTO users (telegram_id, created_at) VALUES (?, ?)",
            (uid, now_iso()),
        )
        await _db.commit()


async def list_users():
    cur = await _db.execute("SELECT * FROM users ORDER BY created_at")
    return await cur.fetchall()


async def set_authorized(uid: int, value: bool) -> None:
    await _db.execute(
        "UPDATE users SET is_authorized = ? WHERE telegram_id = ?",
        (1 if value else 0, uid),
    )
    await _db.commit()


async def set_banned(uid: int, value: bool) -> None:
    await _db.execute(
        "UPDATE users SET is_banned = ? WHERE telegram_id = ?",
        (1 if value else 0, uid),
    )
    await _db.commit()


async def set_admin(uid: int, value: bool) -> None:
    await _db.execute(
        "UPDATE users SET is_admin = ? WHERE telegram_id = ?",
        (1 if value else 0, uid),
    )
    await _db.commit()


async def delete_user(uid: int) -> None:
    for table in ("transactions", "resources", "active_process", "processes"):
        await _db.execute(f"DELETE FROM {table} WHERE user_id = ?", (uid,))
    await _db.execute("DELETE FROM users WHERE telegram_id = ?", (uid,))
    await _db.commit()


# ---------------------------------------------------------------- balance ---
async def get_balance(uid: int) -> float:
    row = await get_user(uid)
    return float(row["balance"]) if row else 0.0


async def add_transaction(uid, amount, balance_after, type_, comment) -> None:
    await _db.execute(
        "INSERT INTO transactions (user_id, amount, balance_after, type, comment, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (uid, amount, balance_after, type_, comment, now_iso()),
    )
    await _db.commit()


async def change_balance(uid: int, delta: float, type_: str, comment=None) -> float:
    new_balance = await get_balance(uid) + delta
    await _db.execute(
        "UPDATE users SET balance = ? WHERE telegram_id = ?", (new_balance, uid)
    )
    await _db.commit()
    await add_transaction(uid, delta, new_balance, type_, comment)
    return new_balance


async def set_balance(uid: int, value: float, comment=None) -> float:
    delta = value - await get_balance(uid)
    await _db.execute(
        "UPDATE users SET balance = ? WHERE telegram_id = ?", (value, uid)
    )
    await _db.commit()
    await add_transaction(
        uid, delta, value, "set", comment or f"Установлен баланс: {value:g}"
    )
    return value


async def list_transactions(uid: int, limit: int = 20):
    cur = await _db.execute(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (uid, limit),
    )
    return await cur.fetchall()


# -------------------------------------------------------------- resources ---
async def add_resources(uid: int, items: Iterable[str]) -> int:
    count = 0
    for item in items:
        await _db.execute(
            "INSERT INTO resources (user_id, value, created_at) VALUES (?, ?, ?)",
            (uid, item, now_iso()),
        )
        count += 1
    await _db.commit()
    return count


async def list_resources(uid: int):
    cur = await _db.execute(
        "SELECT * FROM resources WHERE user_id = ? ORDER BY id", (uid,)
    )
    return await cur.fetchall()


async def get_resource_by_number(uid: int, number: int):
    rows = await list_resources(uid)
    if 1 <= number <= len(rows):
        return rows[number - 1]
    return None


async def delete_resources_by_numbers(uid: int, numbers: Iterable[int]) -> int:
    rows = await list_resources(uid)
    ids = [rows[n - 1]["id"] for n in sorted(set(numbers)) if 1 <= n <= len(rows)]
    for rid in ids:
        await _db.execute(
            "DELETE FROM resources WHERE id = ? AND user_id = ?", (rid, uid)
        )
    await _db.commit()
    return len(ids)


# ---------------------------------------------------------- active process ---
async def get_active(uid: int):
    cur = await _db.execute("SELECT * FROM active_process WHERE user_id = ?", (uid,))
    return await cur.fetchone()


async def start_process(uid: int) -> None:
    await _db.execute(
        "INSERT INTO active_process (user_id, current_step, started_at) VALUES (?, 0, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET current_step = 0, started_at = excluded.started_at, "
        "resource_number = NULL, result_value = NULL, profit = NULL",
        (uid, now_iso()),
    )
    await _db.commit()


async def set_step(uid: int, step: int) -> None:
    await _db.execute(
        "UPDATE active_process SET current_step = ? WHERE user_id = ?", (step, uid)
    )
    await _db.commit()


async def set_active_field(uid: int, field: str, value) -> None:
    if field not in ("resource_number", "result_value", "profit"):
        raise ValueError(f"Недопустимое поле процесса: {field}")
    await _db.execute(
        f"UPDATE active_process SET {field} = ? WHERE user_id = ?", (value, uid)
    )
    await _db.commit()


async def clear_active(uid: int) -> None:
    await _db.execute("DELETE FROM active_process WHERE user_id = ?", (uid,))
    await _db.commit()


# --------------------------------------------------- tabla / processes / stats
async def inc_tabla(uid: int) -> None:
    await _db.execute(
        "UPDATE users SET tabla_count = tabla_count + 1 WHERE telegram_id = ?", (uid,)
    )
    await _db.commit()


async def get_tabla(uid: int) -> int:
    row = await get_user(uid)
    return int(row["tabla_count"]) if row else 0


async def complete_process(
    uid, started_at, finished_at, duration, profit, resource_number, result_value
) -> None:
    await _db.execute(
        "INSERT INTO processes (user_id, started_at, finished_at, duration_seconds, "
        "profit, resource_number, result_value, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'completed')",
        (uid, started_at, finished_at, duration, profit, resource_number, result_value),
    )
    await _db.commit()


async def stats(uid: int) -> dict:
    cur = await _db.execute(
        "SELECT COUNT(*) AS c, COALESCE(SUM(profit), 0) AS p, "
        "COALESCE(AVG(duration_seconds), 0) AS a "
        "FROM processes WHERE user_id = ? AND status = 'completed'",
        (uid,),
    )
    row = await cur.fetchone()
    return {
        "completed": row["c"],
        "profit": row["p"],
        "avg_duration": row["a"],
        "tabla": await get_tabla(uid),
    }
