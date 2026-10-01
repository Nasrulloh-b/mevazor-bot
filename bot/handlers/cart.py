"""Cart: view, change quantities, promo codes."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import keyboards as kb
from ..callbacks import CartCb, PromoInput
from ..db import Database
from ..pricing import compute_totals, fmt_kg
from ..texts import t
from ..views import cart_text
from .utils import answer_callback, show

router = Router(name="cart")


async def show_cart(target: Message | CallbackQuery, db: Database, lang: str, user_id: int) -> None:
    lines = await db.get_cart(user_id)
    if not lines:
        await show(target, t(lang, "cart.empty"))
        return
    products = await db.all_products()
    promo = await db.get_promo(user_id)
    totals = compute_totals(lines, products, promo)
    await show(target, cart_text(lang, lines, products, totals, promo), kb.cart(lang, lines, products, bool(promo)))


@router.callback_query(CartCb.filter(F.action.in_({"show", "inc", "dec", "del", "clear", "unpromo"})))
async def on_cart_action(callback: CallbackQuery, callback_data: CartCb, db: Database, lang: str) -> None:
    user_id = callback.from_user.id
    action = callback_data.action
    note = None
    if action in ("inc", "dec", "del"):
        lines = await db.get_cart(user_id)
        line = next((l for l in lines if l.product_id == callback_data.id and l.grams == callback_data.grams), None)
        if line:
            new_qty = {"inc": line.qty + 1, "dec": line.qty - 1, "del": 0}[action]
            stored = await db.set_qty(user_id, line.product_id, line.grams, new_qty)
            if action == "inc" and stored == line.qty:
                product = await db.get_product(line.product_id)
                if product:
                    note = t(lang, "product.not_enough", kg=fmt_kg(product.stock_grams, lang))
    elif action == "clear":
        await db.clear_cart(user_id)
        note = t(lang, "cart.cleared")
    elif action == "unpromo":
        await db.set_promo(user_id, None)
        note = t(lang, "cart.promo_removed")
    await answer_callback(callback, note)
    await show_cart(callback, db, lang, user_id)


@router.callback_query(CartCb.filter(F.action == "promo"))
async def on_promo_start(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.set_state(PromoInput.code)
    await answer_callback(callback)
    if isinstance(callback.message, Message):
        await callback.message.answer(t(lang, "cart.promo_ask"))


@router.message(PromoInput.code, F.text)
async def on_promo_code(message: Message, state: FSMContext, db: Database, lang: str) -> None:
    assert message.from_user and message.text
    code = await db.set_promo(message.from_user.id, message.text)
    if code is None:
        await message.answer(t(lang, "cart.promo_bad"))
        return
    await state.clear()
    await message.answer(t(lang, "cart.promo_ok", code=code))
    await show_cart(message, db, lang, message.from_user.id)
