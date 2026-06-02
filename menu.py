"""Главное меню и авторизованный /start."""
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import keyboards

router = Router()

WELCOME = (
    "✅ Доступ открыт.\n\n"
    "Команда /work — открыть главное меню.\n"
    "Команды: /circle, /money, /proxy, /stats"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(WELCOME, reply_markup=keyboards.main_menu())


@router.message(Command("work"))
async def cmd_work(message: Message, state: FSMContext):
    await state.set_state(None)
    await message.answer("Главное меню:", reply_markup=keyboards.main_menu())


@router.callback_query(F.data == "m:back")
async def cb_back(cb: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    try:
        await cb.message.edit_text("Главное меню:", reply_markup=keyboards.main_menu())
    except Exception:
        await cb.message.answer("Главное меню:", reply_markup=keyboards.main_menu())
    await cb.answer()
