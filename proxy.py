"""Список ресурсов (/proxy) — хранение и управление."""
import re

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

import db
import keyboards
import utils

router = Router()


class ProxySG(StatesGroup):
    add = State()
    delete = State()


async def show_menu(event):
    await utils.respond(
        event,
        "🗂 <b>Список ресурсов</b>\nХранение и управление списком ресурсов.",
        keyboards.proxy_menu(),
    )


@router.message(Command("proxy"))
async def cmd_proxy(message: Message, state: FSMContext):
    await state.set_state(None)
    await show_menu(message)


@router.callback_query(F.data.in_({"m:proxy", "px:menu"}))
async def cb_menu(cb: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await show_menu(cb)


async def show_list(event):
    rows = await db.list_resources(event.from_user.id)
    if not rows:
        await utils.respond(
            event, "Список пуст. Нажмите «Добавить», чтобы внести ресурсы.",
            keyboards.proxy_menu(),
        )
        return
    lines = ["🗂 <b>Ресурсы</b>:", ""]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. <code>{r['value']}</code>")
    await utils.respond(event, "\n".join(lines), keyboards.proxy_menu())


@router.callback_query(F.data == "px:list")
async def cb_list(cb: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await show_list(cb)


@router.callback_query(F.data == "px:add")
async def cb_add(cb: CallbackQuery, state: FSMContext):
    await state.set_state(ProxySG.add)
    await utils.respond(
        cb,
        "Отправьте ресурсы — по одному в строке. Пример:\n"
        "<code>45.11.127.213:9524:D3w1M0:Yzv5Yn</code>",
        keyboards.cancel_kb("px:menu"),
    )


@router.message(ProxySG.add)
async def do_add(message: Message, state: FSMContext):
    items = [line.strip() for line in (message.text or "").splitlines() if line.strip()]
    if not items:
        await message.answer("Не найдено ни одной непустой строки. Повторите ввод.")
        return
    count = await db.add_resources(message.from_user.id, items)
    await state.set_state(None)
    await message.answer(f"✅ Добавлено элементов: {count}.", reply_markup=keyboards.proxy_menu())


@router.callback_query(F.data == "px:del")
async def cb_del(cb: CallbackQuery, state: FSMContext):
    await state.set_state(ProxySG.delete)
    await utils.respond(
        cb,
        "Введите номер(а) для удаления — через пробел или запятую. "
        "Нумерация — как в списке (/proxy → Список).",
        keyboards.cancel_kb("px:menu"),
    )


@router.message(ProxySG.delete)
async def do_del(message: Message, state: FSMContext):
    numbers = [int(x) for x in re.findall(r"\d+", message.text or "")]
    if not numbers:
        await message.answer("Введите хотя бы один номер.")
        return
    deleted = await db.delete_resources_by_numbers(message.from_user.id, numbers)
    await state.set_state(None)
    await message.answer(f"🗑 Удалено элементов: {deleted}.", reply_markup=keyboards.proxy_menu())
