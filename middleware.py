"""Middleware авторизации: пароль, бан, изоляция доступа."""
import logging

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

import db

logger = logging.getLogger("auth")


class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        row = await db.get_or_create_user(user.id, user.username)

        # заблокированные пользователи
        if row["is_banned"]:
            if isinstance(event, Message):
                await event.answer("🚫 Вы заблокированы и не можете пользоваться ботом.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Вы заблокированы.", show_alert=True)
            return

        # неавторизованные: запрос пароля
        if not row["is_authorized"]:
            if isinstance(event, Message):
                text = (event.text or "").strip()
                if text.startswith("/start") or text.startswith("/help"):
                    await event.answer("🔒 Доступ закрыт.\nВведите пароль для входа:")
                    return
                if text and await db.check_password(text):
                    await db.set_authorized(user.id, True)
                    await event.answer(
                        "✅ Пароль верный! Доступ открыт.\n"
                        "Откройте главное меню командой /work"
                    )
                else:
                    await event.answer("❌ Неверный пароль. Попробуйте ещё раз:")
                return
            if isinstance(event, CallbackQuery):
                await event.answer(
                    "Сначала авторизуйтесь: отправьте пароль сообщением.",
                    show_alert=True,
                )
                return

        data["db_user"] = row
        return await handler(event, data)
