"""Финансовый учёт (/money, /balance, /history)."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

import db
import keyboards
import utils

router = Router()

TYPE_NAMES = {
    "add": "пополнение",
    "subtract": "списание",
    "set": "установка",
    "process": "процесс",
}


class MoneySG(StatesGroup):
    add = State()
    sub = State()
    setv = State()


# ------------------------------------------------------------------ menu ---
async def show_menu(event):
    await utils.respond(event, "💰 <b>Финансовый учёт</b>", keyboards.money_menu())


@router.message(Command("money"))
async def cmd_money(message: Message, state: FSMContext):
    await state.set_state(None)
    await show_menu(message)


@router.callback_query(F.data.in_({"m:money", "mn:menu"}))
async def cb_menu(cb: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await show_menu(cb)


# --------------------------------------------------------------- balance ---
async def show_balance(event):
    balance = await db.get_balance(event.from_user.id)
    await utils.respond(
        event, f"💰 Текущий баланс: <b>{utils.fmt(balance)}</b>", keyboards.balance_kb()
    )


@router.message(Command("balance"))
async def cmd_balance(message: Message, state: FSMContext):
    await state.set_state(None)
    await show_balance(message)


@router.callback_query(F.data == "mn:balance")
async def cb_balance(cb: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await show_balance(cb)


@router.callback_query(F.data == "mn:add")
async def cb_add(cb: CallbackQuery, state: FSMContext):
    await state.set_state(MoneySG.add)
    await utils.respond(
        cb,
        "Введите сумму для <b>увеличения</b> баланса.\n"
        "Можно с комментарием: <code>100 пополнение</code>",
        keyboards.cancel_kb("mn:balance"),
    )


@router.callback_query(F.data == "mn:sub")
async def cb_sub(cb: CallbackQuery, state: FSMContext):
    await state.set_state(MoneySG.sub)
    await utils.respond(
        cb,
        "Введите сумму для <b>уменьшения</b> баланса.\n"
        "Можно с комментарием: <code>50 расход</code>",
        keyboards.cancel_kb("mn:balance"),
    )


@router.callback_query(F.data == "mn:set")
async def cb_set(cb: CallbackQuery, state: FSMContext):
    await state.set_state(MoneySG.setv)
    await utils.respond(
        cb,
        "Введите новое значение баланса (заменит текущее).\n"
        "Можно с комментарием: <code>1000 корректировка</code>",
        keyboards.cancel_kb("mn:balance"),
    )


@router.message(MoneySG.add)
async def do_add(message: Message, state: FSMContext):
    amount, comment = utils.parse_amount_comment(message.text)
    if amount is None:
        await message.answer("Введите число. Пример: <code>100</code> или <code>100 комментарий</code>")
        return
    balance = await db.change_balance(message.from_user.id, abs(amount), "add", comment)
    await state.set_state(None)
    await message.answer(
        f"➕ Баланс увеличен на {utils.fmt(abs(amount))}.\n"
        f"Текущий баланс: <b>{utils.fmt(balance)}</b>",
        reply_markup=keyboards.balance_kb(),
    )


@router.message(MoneySG.sub)
async def do_sub(message: Message, state: FSMContext):
    amount, comment = utils.parse_amount_comment(message.text)
    if amount is None:
        await message.answer("Введите число.")
        return
    balance = await db.change_balance(message.from_user.id, -abs(amount), "subtract", comment)
    await state.set_state(None)
    await message.answer(
        f"➖ Баланс уменьшен на {utils.fmt(abs(amount))}.\n"
        f"Текущий баланс: <b>{utils.fmt(balance)}</b>",
        reply_markup=keyboards.balance_kb(),
    )


@router.message(MoneySG.setv)
async def do_set(message: Message, state: FSMContext):
    amount, comment = utils.parse_amount_comment(message.text)
    if amount is None:
        await message.answer("Введите число.")
        return
    balance = await db.set_balance(message.from_user.id, amount, comment)
    await state.set_state(None)
    await message.answer(
        f"✏️ Баланс установлен.\nТекущий баланс: <b>{utils.fmt(balance)}</b>",
        reply_markup=keyboards.balance_kb(),
    )


# --------------------------------------------------------------- history ---
async def show_history(event):
    rows = await db.list_transactions(event.from_user.id, 20)
    if not rows:
        await utils.respond(event, "📜 История операций пуста.", keyboards.balance_kb())
        return
    lines = ["📜 <b>История операций</b> (последние 20):", ""]
    for r in rows:
        amount = r["amount"]
        sign = "+" if amount >= 0 else ""
        date, _, time = r["created_at"].partition(" ")
        comment = f" — {r['comment']}" if r["comment"] else ""
        lines.append(
            f"{date} {time} | {sign}{utils.fmt(amount)} | "
            f"{TYPE_NAMES.get(r['type'], r['type'])}{comment}"
        )
    await utils.respond(event, "\n".join(lines), keyboards.balance_kb())


@router.message(Command("history"))
async def cmd_history(message: Message, state: FSMContext):
    await state.set_state(None)
    await show_history(message)


@router.callback_query(F.data == "mn:history")
async def cb_history(cb: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await show_history(cb)
