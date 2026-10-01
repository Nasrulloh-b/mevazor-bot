"""Checkout conversation: name → phone → delivery → city/address → payment → confirm."""

from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import keyboards as kb
from ..callbacks import CartCb, Checkout, CheckoutCb
from ..config import Config
from ..db import CheckoutData, Database, EmptyCartError, StockError, load_catalog
from ..pricing import compute_totals, fmt_kg, fmt_money, is_valid_phone
from ..texts import t
from ..views import admin_order_text, cart_lines_text, totals_text
from .utils import answer_callback, show

router = Router(name="checkout")
log = logging.getLogger(__name__)
CITIES = load_catalog()["cities"]
PICKUP_CITY = "Khujand"


async def start_checkout(target: Message | CallbackQuery, state: FSMContext, db: Database, lang: str, user_id: int) -> None:
    message = target.message if isinstance(target, CallbackQuery) else target
    if not isinstance(message, Message):
        return
    if not await db.get_cart(user_id):
        await message.answer(t(lang, "checkout.empty"))
        return
    saved_name, saved_phone = await db.get_contact(user_id)
    suggested = saved_name or (target.from_user.full_name if target.from_user else None)
    await state.clear()
    await state.update_data(saved_phone=saved_phone)
    await state.set_state(Checkout.name)
    await message.answer(t(lang, "checkout.name"), reply_markup=kb.ask_name(suggested))


@router.callback_query(CartCb.filter(F.action == "checkout"))
async def on_checkout(callback: CallbackQuery, state: FSMContext, db: Database, lang: str) -> None:
    await answer_callback(callback)
    await start_checkout(callback, state, db, lang, callback.from_user.id)


@router.message(Checkout.name, F.text)
async def on_name(message: Message, state: FSMContext, lang: str) -> None:
    name = (message.text or "").strip()
    if len(name) < 2 or len(name) > 60:
        await message.answer(t(lang, "checkout.name_bad"))
        return
    await state.update_data(name=name)
    await state.set_state(Checkout.phone)
    data = await state.get_data()
    await message.answer(t(lang, "checkout.phone"), reply_markup=kb.ask_phone(lang, data.get("saved_phone")))


@router.message(Checkout.phone, F.contact)
async def on_phone_contact(message: Message, state: FSMContext, lang: str) -> None:
    assert message.contact
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await _save_phone(message, state, lang, phone)


@router.message(Checkout.phone, F.text)
async def on_phone_text(message: Message, state: FSMContext, lang: str) -> None:
    phone = (message.text or "").strip()
    if not is_valid_phone(phone):
        await message.answer(t(lang, "checkout.phone_bad"))
        return
    await _save_phone(message, state, lang, phone)


async def _save_phone(message: Message, state: FSMContext, lang: str, phone: str) -> None:
    await state.update_data(phone=phone)
    await state.set_state(Checkout.delivery)
    await message.answer(f"✅ {escape(phone)}", reply_markup=kb.remove())
    await message.answer(t(lang, "checkout.delivery"), reply_markup=kb.delivery(lang))


@router.callback_query(Checkout.delivery, CheckoutCb.filter(F.step == "delivery"))
async def on_delivery(callback: CallbackQuery, callback_data: CheckoutCb, state: FSMContext, lang: str) -> None:
    await answer_callback(callback)
    if callback_data.value == "pickup":
        await state.update_data(delivery="pickup", city=PICKUP_CITY, address="")
        await state.set_state(Checkout.payment)
        await show(callback, t(lang, "checkout.payment"), kb.payment(lang))
    else:
        await state.update_data(delivery="courier")
        await state.set_state(Checkout.city)
        await show(callback, t(lang, "checkout.city"), kb.cities(lang, CITIES))


@router.callback_query(Checkout.city, CheckoutCb.filter(F.step == "city"))
async def on_city(callback: CallbackQuery, callback_data: CheckoutCb, state: FSMContext, lang: str) -> None:
    await answer_callback(callback)
    if not any(c["en"] == callback_data.value for c in CITIES):
        return
    await state.update_data(city=callback_data.value)
    await state.set_state(Checkout.address)
    city = next(c[lang] for c in CITIES if c["en"] == callback_data.value)
    await show(callback, f"📍 {escape(city)}\n\n{t(lang, 'checkout.address')}")


@router.message(Checkout.address, F.text)
async def on_address(message: Message, state: FSMContext, lang: str) -> None:
    address = (message.text or "").strip()
    if len(address) < 4 or not any(ch.isdigit() for ch in address):
        await message.answer(t(lang, "checkout.address_bad"))
        return
    await state.update_data(address=address[:200])
    await state.set_state(Checkout.payment)
    await message.answer(t(lang, "checkout.payment"), reply_markup=kb.payment(lang))


@router.callback_query(Checkout.payment, CheckoutCb.filter(F.step == "payment"))
async def on_payment(callback: CallbackQuery, callback_data: CheckoutCb, state: FSMContext, db: Database, lang: str) -> None:
    await answer_callback(callback)
    payment = "card" if callback_data.value == "card" else "cash"
    await state.update_data(payment=payment)
    await state.set_state(Checkout.confirm)

    data = await state.get_data()
    user_id = callback.from_user.id
    lines = await db.get_cart(user_id)
    if not lines:
        await state.clear()
        await show(callback, t(lang, "checkout.empty"))
        return
    products = await db.all_products()
    promo = await db.get_promo(user_id)
    totals = compute_totals(lines, products, promo, data["delivery"])
    city = next((c[lang] for c in CITIES if c["en"] == data["city"]), data["city"])
    where = (
        t(lang, "checkout.to_address", city=escape(city), address=escape(data["address"]))
        if data["delivery"] == "courier"
        else t(lang, "checkout.to_pickup")
    )
    text = t(
        lang,
        "checkout.summary",
        lines=cart_lines_text(lang, lines, products),
        totals=totals_text(lang, totals, promo),
        name=escape(data["name"]),
        phone=escape(data["phone"]),
        delivery=where,
        payment=t(lang, "checkout.card" if payment == "card" else "checkout.cash"),
    )
    await show(callback, text, kb.confirm(lang))


@router.callback_query(Checkout.confirm, CheckoutCb.filter(F.step == "confirm"))
async def on_confirm(
    callback: CallbackQuery, state: FSMContext, db: Database, config: Config, bot: Bot, lang: str
) -> None:
    data = await state.get_data()
    user_id = callback.from_user.id
    checkout = CheckoutData(
        name=data["name"],
        phone=data["phone"],
        delivery=data["delivery"],
        city=data["city"],
        address=data.get("address", ""),
        payment=data["payment"],
    )
    try:
        order = await db.place_order(user_id, checkout)
    except StockError as err:
        await state.clear()
        await answer_callback(callback)
        await show(callback, t(lang, "checkout.stock", name=escape(err.product.name[lang]), kg=fmt_kg(err.available_grams, lang)))
        await _back_to_menu(callback, lang)
        return
    except EmptyCartError:
        await state.clear()
        await answer_callback(callback)
        await show(callback, t(lang, "checkout.empty"))
        await _back_to_menu(callback, lang)
        return

    await state.clear()
    await answer_callback(callback, "✅")
    next_step = (
        t(lang, "checkout.next_courier", phone=escape(order.phone))
        if order.delivery == "courier"
        else t(lang, "checkout.next_pickup")
    )
    await show(callback, t(lang, "checkout.done", number=order.number, total=fmt_money(order.total_cents, lang), next_step=next_step))
    await _back_to_menu(callback, lang)

    for admin_id in config.admin_ids:
        try:
            await bot.send_message(admin_id, "🔔 " + admin_order_text(order), reply_markup=kb.admin_order(order))
        except Exception:  # an admin who never opened the bot can't receive messages
            log.warning("Could not notify admin %s about order %s", admin_id, order.number)


@router.callback_query(CheckoutCb.filter(F.step == "cancel"))
async def on_cancel(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.clear()
    await answer_callback(callback)
    await show(callback, t(lang, "checkout.cancelled"))
    await _back_to_menu(callback, lang)


@router.callback_query(CheckoutCb.filter())
async def on_stale_button(callback: CallbackQuery, lang: str) -> None:
    """A button from an old checkout message was pressed after the conversation moved on."""
    await answer_callback(callback, t(lang, "cancel.done"))


async def _back_to_menu(callback: CallbackQuery, lang: str) -> None:
    if isinstance(callback.message, Message):
        await callback.message.answer(t(lang, "menu.hint"), reply_markup=kb.main_menu(lang))
