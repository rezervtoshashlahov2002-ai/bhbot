"""Inline-клавиатуры для навигации."""
from aiogram.utils.keyboard import InlineKeyboardBuilder

import process_steps


def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="▶️ Начать процесс", callback_data="m:circle")
    kb.button(text="💰 Финансовый учёт", callback_data="m:money")
    kb.button(text="🗂 Список ресурсов", callback_data="m:proxy")
    kb.button(text="📊 Статистика", callback_data="m:stats")
    kb.adjust(1)
    return kb.as_markup()


def back_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ В меню", callback_data="m:back")
    return kb.as_markup()


def cancel_kb(callback_data: str = "m:back"):
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Отмена", callback_data=callback_data)
    return kb.as_markup()


# ---------------------------------------------------------------- circle ---
def resource_pick_kb(resources, max_label: int = 40):
    """Кнопки выбора прокси на шаге процесса. callback_data: cr:<id>."""
    kb = InlineKeyboardBuilder()
    for i, r in enumerate(resources, start=1):
        value = r["value"]
        label = value if len(value) <= max_label else value[: max_label - 1] + "…"
        kb.button(text=f"{i}. {label}", callback_data=f"cr:{r['id']}")
    kb.button(text="❌ Назад", callback_data="c:back")
    kb.adjust(1)
    return kb.as_markup()


def step_kb(step_idx: int):
    step = process_steps.STEPS[step_idx]
    kb = InlineKeyboardBuilder()
    if step.get("input"):
        kb.button(text="❌ Назад", callback_data="c:back")
        kb.adjust(1)
    else:
        kb.button(text="✅ Выполнено", callback_data="c:done")
        kb.button(text="❌ Назад", callback_data="c:back")
        if step.get("tabla"):
            kb.button(text="🟥 Табла", callback_data="c:tabla")
            kb.adjust(2, 1)
        else:
            kb.adjust(2)
    return kb.as_markup()


# ----------------------------------------------------------------- money ---
def money_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Баланс", callback_data="mn:balance")
    kb.button(text="📜 История", callback_data="mn:history")
    kb.button(text="⬅️ В меню", callback_data="m:back")
    kb.adjust(2, 1)
    return kb.as_markup()


def balance_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Увеличить", callback_data="mn:add")
    kb.button(text="➖ Уменьшить", callback_data="mn:sub")
    kb.button(text="✏️ Задать", callback_data="mn:set")
    kb.button(text="📜 История", callback_data="mn:history")
    kb.button(text="⬅️ Назад", callback_data="mn:menu")
    kb.adjust(3, 1, 1)
    return kb.as_markup()


# ----------------------------------------------------------------- proxy ---
def proxy_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Список", callback_data="px:list")
    kb.button(text="➕ Добавить", callback_data="px:add")
    kb.button(text="🗑 Удалить", callback_data="px:del")
    kb.button(text="⬅️ В меню", callback_data="m:back")
    kb.adjust(1, 2, 1)
    return kb.as_markup()


# ----------------------------------------------------------------- admin ---
def admin_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="👥 Пользователи", callback_data="a:users")
    kb.button(text="📊 Стат. пользователей", callback_data="a:stats")
    kb.button(text="➕ Добавить админа", callback_data="a:addadmin")
    kb.button(text="➖ Снять админа", callback_data="a:deladmin")
    kb.button(text="✅ Выдать доступ", callback_data="a:grant")
    kb.button(text="⛔ Отозвать доступ", callback_data="a:revoke")
    kb.button(text="🚫 Бан", callback_data="a:ban")
    kb.button(text="♻️ Разбан", callback_data="a:unban")
    kb.button(text="🗑 Удалить пользователя", callback_data="a:del")
    kb.button(text="🔑 Изменить пароль", callback_data="a:passwd")
    kb.adjust(2)
    return kb.as_markup()
