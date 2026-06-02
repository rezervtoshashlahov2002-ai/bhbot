"""Точка входа: инициализация БД, диспетчера, роутеров и запуск polling."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
import db
from middleware import AuthMiddleware

import menu
import circle
import money
import proxy
import stats
import admin
import fallback

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("bot")


async def main() -> None:
    await db.connect()
    logger.info("База данных инициализирована: %s", config.DATABASE_PATH)

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # авторизация и изоляция доступа
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # порядок важен: фолбэк подключается последним
    dp.include_router(menu.router)
    dp.include_router(circle.router)
    dp.include_router(money.router)
    dp.include_router(proxy.router)
    dp.include_router(stats.router)
    dp.include_router(admin.router)
    dp.include_router(fallback.router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Бот запущен, начинаю polling.")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await db.close()
        logger.info("Бот остановлен, соединения закрыты.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger("bot").info("Остановка по сигналу прерывания.")
