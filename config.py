"""Загрузка конфигурации из переменных окружения (.env)."""
import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "bot.db").strip()
DEFAULT_PASSWORD: str = os.getenv("DEFAULT_PASSWORD", "changeme")

_admin = os.getenv("INITIAL_ADMIN_ID", "").strip()
INITIAL_ADMIN_ID = int(_admin) if _admin.lstrip("-").isdigit() else None

# Себестоимость одного круга: вычитается из прибыли каждого завершённого процесса.
_cost = os.getenv("CIRCLE_COST", "375").strip().replace(",", ".")
try:
    CIRCLE_COST: float = float(_cost)
except ValueError:
    CIRCLE_COST = 375.0

# (необязательно) Резервное хранение БД в GitHub Gist — для хостинга без
# постоянного диска. Нужен токен с правом 'gist'.
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "").strip()
GIST_ID: str = os.getenv("GIST_ID", "").strip()
GIST_FILENAME: str = os.getenv("GIST_FILENAME", "bot_db.b64").strip() or "bot_db.b64"
_interval = os.getenv("GIST_SYNC_INTERVAL", "120").strip()
GIST_SYNC_INTERVAL: int = int(_interval) if _interval.isdigit() else 120

if not BOT_TOKEN:
    raise RuntimeError(
        "Не задан BOT_TOKEN. Укажите его в переменных окружения или в файле .env"
    )
