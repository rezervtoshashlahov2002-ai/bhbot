"""Загрузка конфигурации из переменных окружения (.env)."""
import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "bot.db").strip()
DEFAULT_PASSWORD: str = os.getenv("DEFAULT_PASSWORD", "changeme")

_admin = os.getenv("INITIAL_ADMIN_ID", "").strip()
INITIAL_ADMIN_ID = int(_admin) if _admin.lstrip("-").isdigit() else None

if not BOT_TOKEN:
    raise RuntimeError(
        "Не задан BOT_TOKEN. Укажите его в переменных окружения или в файле .env"
    )
