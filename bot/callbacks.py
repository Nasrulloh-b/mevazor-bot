"""Callback data for inline buttons and the checkout conversation states."""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import State, StatesGroup


class LangCb(CallbackData, prefix="lang"):
    lang: str


class CategoryCb(CallbackData, prefix="cat"):
    id: str  # category id, or "all" for the category list


class ProductCb(CallbackData, prefix="p"):
    """Product card. `action` is view (redraw with this pack/qty) or add."""

    action: str
    id: str
    grams: int
    qty: int = 1


class CartCb(CallbackData, prefix="c"):
    """Cart actions: show, inc, dec, del, clear, promo, unpromo, checkout."""

    action: str
    id: str = ""
    grams: int = 0


class CheckoutCb(CallbackData, prefix="co"):
    """Choices during checkout: delivery, city, payment, confirm, cancel."""

    step: str
    value: str = ""


class AdminOrderCb(CallbackData, prefix="ao"):
    order_id: int
    status: str = ""  # empty = open the order card


class AdminCb(CallbackData, prefix="adm"):
    action: str  # open | stock | dash


class Checkout(StatesGroup):
    name = State()
    phone = State()
    delivery = State()
    city = State()
    address = State()
    payment = State()
    confirm = State()


class PromoInput(StatesGroup):
    code = State()
