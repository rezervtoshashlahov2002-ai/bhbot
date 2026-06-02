"""Резервное хранение БД в GitHub Gist.

Позволяет переживать перезапуски на хостинге без постоянного диска
(например, бесплатный Railway без Volume). При старте БД скачивается из gist,
во время работы периодически и при остановке выгружается обратно.

Файл в gist хранит SQLite-базу в base64. Используйте СЕКРЕТНЫЙ gist и держите
токен и GIST_ID в тайне — в базе лежат данные пользователей.
"""
import asyncio
import base64
import hashlib
import logging

import aiohttp

import config
import db

logger = logging.getLogger("gist")

API = "https://api.github.com"
_SQLITE_HEADER = b"SQLite format 3\x00"

_last_hash = None
_task = None


def enabled() -> bool:
    return bool(config.GITHUB_TOKEN and config.GIST_ID)


def _headers():
    return {
        "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def create_gist():
    """Создаёт новый секретный gist и возвращает его id (или None)."""
    if not config.GITHUB_TOKEN:
        return None
    payload = {
        "description": "Telegram bot DB backup",
        "public": False,
        "files": {config.GIST_FILENAME: {"content": "init"}},
    }
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{API}/gists", headers=_headers(), json=payload) as r:
                if r.status not in (200, 201):
                    logger.warning("Не удалось создать gist (%s): %s", r.status, await r.text())
                    return None
                data = await r.json()
                return data.get("id")
    except Exception as e:  # noqa: BLE001
        logger.exception("Ошибка при создании gist: %s", e)
        return None


async def restore_to(path: str) -> bool:
    """Скачивает БД из gist и пишет в path. True — если восстановлено."""
    if not enabled():
        return False
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{API}/gists/{config.GIST_ID}", headers=_headers()) as r:
                if r.status != 200:
                    logger.warning("Gist GET вернул %s: %s", r.status, await r.text())
                    return False
                data = await r.json()
            f = (data.get("files") or {}).get(config.GIST_FILENAME)
            if not f:
                logger.info("В gist нет файла %s — старт с чистой БД.", config.GIST_FILENAME)
                return False
            if f.get("truncated"):
                async with s.get(f["raw_url"], headers=_headers()) as r:
                    content = await r.text()
            else:
                content = f.get("content", "")
        raw = base64.b64decode(content)
        if not raw.startswith(_SQLITE_HEADER):
            logger.info("Содержимое gist не похоже на БД — старт с чистой БД.")
            return False
        with open(path, "wb") as out:
            out.write(raw)
        logger.info("БД восстановлена из gist (%d байт).", len(raw))
        return True
    except Exception as e:  # noqa: BLE001
        logger.exception("Не удалось восстановить БД из gist: %s", e)
        return False


async def push(force: bool = False) -> bool:
    """Выгружает текущую БД в gist. Пропускает выгрузку, если данные не менялись."""
    global _last_hash
    if not enabled():
        return False
    try:
        raw = await db.snapshot_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if not force and digest == _last_hash:
            return False
        b64 = base64.b64encode(raw).decode("ascii")
        payload = {"files": {config.GIST_FILENAME: {"content": b64}}}
        async with aiohttp.ClientSession() as s:
            async with s.patch(
                f"{API}/gists/{config.GIST_ID}", headers=_headers(), json=payload
            ) as r:
                if r.status not in (200, 201):
                    logger.warning("Gist PATCH вернул %s: %s", r.status, await r.text())
                    return False
        _last_hash = digest
        logger.info("БД сохранена в gist (%d байт).", len(raw))
        return True
    except Exception as e:  # noqa: BLE001
        logger.exception("Не удалось сохранить БД в gist: %s", e)
        return False


async def _loop():
    while True:
        await asyncio.sleep(config.GIST_SYNC_INTERVAL)
        await push()


def start_background():
    global _task
    if enabled() and _task is None:
        _task = asyncio.create_task(_loop())
        logger.info(
            "Фоновая синхронизация с gist включена (каждые %d c).",
            config.GIST_SYNC_INTERVAL,
        )


async def stop_background():
    global _task
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
