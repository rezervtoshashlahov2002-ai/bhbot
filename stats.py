"""Статистика пользователя (/stats)."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import db
import keyboards
import utils

router = Router()


async def show_stats(event):
    s = await db.stats(event.from_user.id)
    avg = utils.format_duration(s["avg_duration"]) if s["completed"] else "—"
    text = (
        "📊 <b>Статистика</b>\n\n"
        f"Завершённых процессов: <b>{s['completed']}</b>\n"
        f"Сумма прибыли/убытка: <b>{utils.fmt(s['profit'])}</b>\n"
        f"Нажатий «Табла»: <b>{s['tabla']}</b>\n"
        f"Среднее время процесса: <b>{avg}</b>"
    )
    await utils.respond(event, text, keyboards.back_menu())


@router.message(Command("stats"))
async def cmd_stats(message: Message, state: FSMContext):
    await state.set_state(None)
    await show_stats(message)


@router.callback_query(F.data == "m:stats")
async def cb_stats(cb: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await show_stats(cb)
