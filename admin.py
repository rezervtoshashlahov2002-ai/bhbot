"""Админ-панель (/admin)."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

import db
import keyboards
import utils

router = Router()


class AdminSG(StatesGroup):
    add_admin = State()
    del_admin = State()
    grant = State()
    revoke = State()
    ban = State()
    unban = State()
    delete = State()
    passwd = State()


# callback -> (состояние, текст запроса)
ACTIONS = {
    "a:addadmin": (AdminSG.add_admin, "Введите Telegram ID для назначения администратором:"),
    "a:deladmin": (AdminSG.del_admin, "Введите Telegram ID для снятия прав администратора:"),
    "a:grant": (AdminSG.grant, "Введите Telegram ID для выдачи доступа:"),
    "a:revoke": (AdminSG.revoke, "Введите Telegram ID для отзыва доступа:"),
    "a:ban": (AdminSG.ban, "Введите Telegram ID для блокировки:"),
    "a:unban": (AdminSG.unban, "Введите Telegram ID для разблокировки:"),
    "a:del": (AdminSG.delete, "Введите Telegram ID для УДАЛЕНИЯ пользователя (необратимо):"),
    "a:passwd": (AdminSG.passwd, "Введите новый пароль доступа:"),
}


def _is_admin(db_user) -> bool:
    return bool(db_user and db_user["is_admin"])


async def show_menu(event):
    await utils.respond(event, "🛠 <b>Админ-панель</b>", keyboards.admin_menu())


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext, db_user=None):
    if not _is_admin(db_user):
        await message.answer("Недостаточно прав.")
        return
    await state.set_state(None)
    await show_menu(message)


@router.callback_query(F.data == "a:menu")
async def cb_menu(cb: CallbackQuery, state: FSMContext, db_user=None):
    if not _is_admin(db_user):
        await cb.answer("Недостаточно прав.", show_alert=True)
        return
    await state.set_state(None)
    await show_menu(cb)


@router.callback_query(F.data == "a:users")
async def cb_users(cb: CallbackQuery, db_user=None):
    if not _is_admin(db_user):
        await cb.answer("Недостаточно прав.", show_alert=True)
        return
    rows = await db.list_users()
    lines = ["👥 <b>Пользователи</b>:", ""]
    for r in rows:
        flags = []
        if r["is_admin"]:
            flags.append("админ")
        if r["is_authorized"]:
            flags.append("доступ")
        if r["is_banned"]:
            flags.append("бан")
        uname = f"@{r['username']}" if r["username"] else "—"
        lines.append(f"<code>{r['telegram_id']}</code> {uname} [{', '.join(flags) or 'нет доступа'}]")
    await utils.respond(cb, "\n".join(lines), keyboards.admin_menu())


@router.callback_query(F.data == "a:stats")
async def cb_user_stats(cb: CallbackQuery, db_user=None):
    if not _is_admin(db_user):
        await cb.answer("Недостаточно прав.", show_alert=True)
        return
    rows = await db.list_users()
    lines = ["📊 <b>Статистика пользователей</b>:", ""]
    for r in rows:
        s = await db.stats(r["telegram_id"])
        who = f"@{r['username']}" if r["username"] else str(r["telegram_id"])
        avg = utils.format_duration(s["avg_duration"]) if s["completed"] else "—"
        lines.append(
            f"{who}: процессов {s['completed']}, P/L {utils.fmt(s['profit'])}, "
            f"табл {s['tabla']}, ср.время {avg}"
        )
    await utils.respond(cb, "\n".join(lines), keyboards.admin_menu())


@router.callback_query(F.data.in_(set(ACTIONS)))
async def cb_action(cb: CallbackQuery, state: FSMContext, db_user=None):
    if not _is_admin(db_user):
        await cb.answer("Недостаточно прав.", show_alert=True)
        return
    new_state, prompt = ACTIONS[cb.data]
    await state.set_state(new_state)
    await utils.respond(cb, prompt, keyboards.cancel_kb("a:menu"))


async def _parse_id(message: Message):
    text = (message.text or "").strip()
    if not text.lstrip("-").isdigit():
        await message.answer("Введите числовой Telegram ID.")
        return None
    return int(text)


@router.message(AdminSG.add_admin)
async def m_add_admin(message: Message, state: FSMContext, db_user=None):
    if not _is_admin(db_user):
        return
    uid = await _parse_id(message)
    if uid is None:
        return
    await db.ensure_user(uid)
    await db.set_admin(uid, True)
    await db.set_authorized(uid, True)
    await state.set_state(None)
    await message.answer(f"✅ Пользователь {uid} назначен администратором.", reply_markup=keyboards.admin_menu())


@router.message(AdminSG.del_admin)
async def m_del_admin(message: Message, state: FSMContext, db_user=None):
    if not _is_admin(db_user):
        return
    uid = await _parse_id(message)
    if uid is None:
        return
    await db.set_admin(uid, False)
    await state.set_state(None)
    await message.answer(f"✅ С пользователя {uid} сняты права администратора.", reply_markup=keyboards.admin_menu())


@router.message(AdminSG.grant)
async def m_grant(message: Message, state: FSMContext, db_user=None):
    if not _is_admin(db_user):
        return
    uid = await _parse_id(message)
    if uid is None:
        return
    await db.ensure_user(uid)
    await db.set_authorized(uid, True)
    await state.set_state(None)
    await message.answer(f"✅ Доступ выдан пользователю {uid}.", reply_markup=keyboards.admin_menu())


@router.message(AdminSG.revoke)
async def m_revoke(message: Message, state: FSMContext, db_user=None):
    if not _is_admin(db_user):
        return
    uid = await _parse_id(message)
    if uid is None:
        return
    await db.set_authorized(uid, False)
    await state.set_state(None)
    await message.answer(f"✅ Доступ отозван у пользователя {uid}.", reply_markup=keyboards.admin_menu())


@router.message(AdminSG.ban)
async def m_ban(message: Message, state: FSMContext, db_user=None):
    if not _is_admin(db_user):
        return
    uid = await _parse_id(message)
    if uid is None:
        return
    await db.ensure_user(uid)
    await db.set_banned(uid, True)
    await state.set_state(None)
    await message.answer(f"🚫 Пользователь {uid} заблокирован.", reply_markup=keyboards.admin_menu())


@router.message(AdminSG.unban)
async def m_unban(message: Message, state: FSMContext, db_user=None):
    if not _is_admin(db_user):
        return
    uid = await _parse_id(message)
    if uid is None:
        return
    await db.set_banned(uid, False)
    await state.set_state(None)
    await message.answer(f"♻️ Пользователь {uid} разблокирован.", reply_markup=keyboards.admin_menu())


@router.message(AdminSG.delete)
async def m_delete(message: Message, state: FSMContext, db_user=None):
    if not _is_admin(db_user):
        return
    uid = await _parse_id(message)
    if uid is None:
        return
    await db.delete_user(uid)
    await state.set_state(None)
    await message.answer(f"🗑 Пользователь {uid} и все его данные удалены.", reply_markup=keyboards.admin_menu())


@router.message(AdminSG.passwd)
async def m_passwd(message: Message, state: FSMContext, db_user=None):
    if not _is_admin(db_user):
        return
    new_password = (message.text or "").strip()
    if not new_password:
        await message.answer("Пароль не может быть пустым. Введите ещё раз:")
        return
    await db.set_password(new_password)
    await state.set_state(None)
    await message.answer("🔑 Пароль доступа изменён.", reply_markup=keyboards.admin_menu())
