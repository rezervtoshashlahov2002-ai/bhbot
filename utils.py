"""Вспомогательные функции: парсинг чисел, форматирование, ответы."""
from typing import Optional, Tuple

from aiogram.types import CallbackQuery


def parse_number(text: Optional[str]) -> Optional[float]:
    try:
        return float((text or "").strip().replace(",", "."))
    except (ValueError, AttributeError):
        return None


def parse_amount_comment(text: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    parts = (text or "").strip().split(maxsplit=1)
    if not parts:
        return None, None
    return parse_number(parts[0]), (parts[1] if len(parts) > 1 else None)


def format_duration(seconds: Optional[float]) -> str:
    total = int(round(seconds or 0))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}ч {minutes}м {secs}с"
    if minutes:
        return f"{minutes}м {secs}с"
    return f"{secs}с"


def fmt(value) -> str:
    """Аккуратный вывод числа без лишних нулей."""
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)


async def respond(event, text: str, kb=None) -> None:
    """Отправить ответ: для callback — отредактировать сообщение, иначе — новое."""
    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=kb)
        except Exception:
            await event.message.answer(text, reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb)
