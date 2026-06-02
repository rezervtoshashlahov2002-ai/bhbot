"""Пошаговый процесс (/circle) — интерактивный чек-лист."""
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

import config
import db
import keyboards
import process_steps
import utils

router = Router()

STEPS = process_steps.STEPS


class CircleSG(StatesGroup):
    waiting_input = State()


def step_text(idx: int) -> str:
    step = STEPS[idx]
    return f"<b>Шаг {idx + 1}/{len(STEPS)}. {step['title']}</b>\n\n{step['text']}"


async def enter_step(event, state: FSMContext, uid: int, idx: int) -> None:
    idx = max(0, min(idx, len(STEPS) - 1))
    await db.set_step(uid, idx)
    step = STEPS[idx]
    if step.get("input"):
        await state.set_state(CircleSG.waiting_input)
    else:
        await state.set_state(None)

    if step.get("input") == "resource":
        resources = await db.list_resources(uid)
        text = step_text(idx)
        if resources:
            text += "\n\nВыберите прокси кнопкой ниже (или отправьте его номер):"
        else:
            text += (
                "\n\n⚠️ Список ресурсов пуст. Нажмите «Назад», добавьте прокси "
                "через /proxy и начните процесс заново."
            )
        await utils.respond(event, text, keyboards.resource_pick_kb(resources))
    else:
        await utils.respond(event, step_text(idx), keyboards.step_kb(idx))


async def start_or_resume(event, state: FSMContext) -> None:
    uid = event.from_user.id
    active = await db.get_active(uid)
    if active is None:
        await db.start_process(uid)
        idx = 0
    else:
        idx = active["current_step"]
    await enter_step(event, state, uid, idx)


@router.message(Command("circle"))
async def cmd_circle(message: Message, state: FSMContext):
    await start_or_resume(message, state)


@router.callback_query(F.data == "m:circle")
async def cb_circle(cb: CallbackQuery, state: FSMContext):
    await start_or_resume(cb, state)


@router.callback_query(F.data == "c:done")
async def cb_done(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    active = await db.get_active(uid)
    if active is None:
        await cb.answer("Активный процесс не найден. Запустите заново.", show_alert=True)
        return
    idx = active["current_step"]
    if idx + 1 >= len(STEPS):
        await cb.answer()
        return
    await enter_step(cb, state, uid, idx + 1)


@router.callback_query(F.data == "c:back")
async def cb_back(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    active = await db.get_active(uid)
    if active is None:
        await cb.answer()
        return
    idx = active["current_step"]
    if idx == 0:
        await db.clear_active(uid)
        await state.set_state(None)
        await utils.respond(cb, "Процесс отменён.\n\nГлавное меню:", keyboards.main_menu())
        return
    await enter_step(cb, state, uid, idx - 1)


@router.callback_query(F.data == "c:tabla")
async def cb_tabla(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    await db.inc_tabla(uid)
    await db.clear_active(uid)  # «Табла» прерывает текущий процесс и выходит в меню
    await state.set_state(None)
    total = await db.get_tabla(uid)
    await utils.respond(
        cb,
        f"🟥 Засчитана «Табла». Всего: {total}.\n\nГлавное меню:",
        keyboards.main_menu(),
    )


@router.callback_query(F.data.startswith("cr:"))
async def cb_pick_resource(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    active = await db.get_active(uid)
    if active is None:
        await cb.answer("Активный процесс не найден. Запустите заново.", show_alert=True)
        return
    idx = active["current_step"]
    if STEPS[idx].get("input") != "resource":
        await cb.answer()
        return
    try:
        rid = int(cb.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await cb.answer("Некорректный выбор.", show_alert=True)
        return
    resource = await db.get_resource(uid, rid)
    if resource is None:
        await cb.answer("Этот ресурс уже недоступен, список обновлён.", show_alert=True)
        await enter_step(cb, state, uid, idx)  # перерисовать актуальный список
        return
    pos = await db.resource_position(uid, rid) or 0
    await db.set_active_field(uid, "resource_number", pos)
    await db.delete_resource(uid, rid)  # использованный ресурс удаляется из списка
    await cb.answer("Ресурс взят.")
    await cb.message.answer(
        f"✅ Взят ресурс: <code>{resource['value']}</code>\n"
        "Ресурс использован и удалён из списка."
    )
    await enter_step(cb, state, uid, idx + 1)


async def _finalize(message: Message, state: FSMContext, uid: int, active, profit: float):
    started = active["started_at"]
    finished = db.now_iso()
    try:
        dt0 = datetime.strptime(started, "%Y-%m-%d %H:%M:%S")
        dt1 = datetime.strptime(finished, "%Y-%m-%d %H:%M:%S")
        duration = (dt1 - dt0).total_seconds()
    except (TypeError, ValueError):
        duration = 0.0
    cost = config.CIRCLE_COST
    net = profit - cost  # себестоимость круга вычитается из прибыли
    await db.complete_process(
        uid, started, finished, duration, net,
        active["resource_number"], active["result_value"],
    )
    new_balance = await db.change_balance(
        uid, net, "process", f"Прибыль/убыток по процессу (себестоимость −{utils.fmt(cost)})"
    )
    await db.clear_active(uid)
    await state.set_state(None)
    sign = "+" if net >= 0 else ""
    await message.answer(
        "🏁 <b>Процесс завершён.</b>\n\n"
        f"Введено: {utils.fmt(profit)}\n"
        f"Себестоимость круга: −{utils.fmt(cost)}\n"
        f"Итог: {sign}{utils.fmt(net)}\n"
        f"Баланс: {utils.fmt(new_balance)}\n\n"
        "Главное меню:",
        reply_markup=keyboards.main_menu(),
    )


@router.message(CircleSG.waiting_input)
async def on_input(message: Message, state: FSMContext):
    uid = message.from_user.id
    active = await db.get_active(uid)
    if active is None:
        await state.set_state(None)
        return
    idx = active["current_step"]
    kind = STEPS[idx].get("input")

    if kind == "resource":
        text = (message.text or "").strip()
        if not text.isdigit():
            await message.answer("Введите номер ресурса (целое число) из списка /proxy.")
            return
        number = int(text)
        resource = await db.get_resource_by_number(uid, number)
        if resource is None:
            count = len(await db.list_resources(uid))
            await message.answer(
                f"Ресурс №{number} не найден. Доступно элементов: {count}. "
                "Проверьте список командой /proxy."
            )
            return
        await db.set_active_field(uid, "resource_number", number)
        await db.delete_resources_by_numbers(uid, [number])  # использованный ресурс удаляется из списка
        await message.answer(
            f"✅ Взят ресурс №{number}: <code>{resource['value']}</code>\n"
            "Ресурс использован и удалён из списка."
        )
        await enter_step(message, state, uid, idx + 1)

    elif kind == "result":
        value = utils.parse_number(message.text)
        if value is None:
            await message.answer("Введите числовое значение результата.")
            return
        await db.set_active_field(uid, "result_value", value)
        await message.answer(f"✅ Результат сохранён: {utils.fmt(value)}")
        await enter_step(message, state, uid, idx + 1)

    elif kind == "profit":
        value = utils.parse_number(message.text)
        if value is None:
            await message.answer("Введите число (прибыль/убыток). Можно отрицательное.")
            return
        await db.set_active_field(uid, "profit", value)
        await _finalize(message, state, uid, active, value)

    else:
        await state.set_state(None)
