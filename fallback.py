"""Фолбэк-роутер: ловит сообщения вне известных сценариев и подсказывает меню."""
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import StateFilter

from keyboards import main_menu

router = Router()


@router.message(StateFilter(None))
async def unknown_message(message: Message):
    await message.answer(
        "Не понял команду. Откройте меню: /work",
        reply_markup=main_menu(),
    )
