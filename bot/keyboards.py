"""Keyboards (reply menu and inline buttons)."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

from .callbacks import AdminCb, AdminOrderCb, CartCb, CategoryCb, CheckoutCb, LangCb, ProductCb
from .db import Order
from .pricing import COURIER_FEE_CENTS, FREE_DELIVERY_CENTS, CartLine, Product, fmt_money, fmt_pack
from .texts import CATEGORY_EMOJI, STATUS_EMOJI, t

NEXT_STATUS = {"new": "packed", "packed": "shipped", "shipped": "delivered"}


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "menu.catalog")), KeyboardButton(text=t(lang, "menu.cart"))],
            [KeyboardButton(text=t(lang, "menu.orders")), KeyboardButton(text=t(lang, "menu.contact"))],
            [KeyboardButton(text=t(lang, "menu.lang"))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def remove() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def languages() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data=LangCb(lang="ru").pack()),
                InlineKeyboardButton(text="🇬🇧 English", callback_data=LangCb(lang="en").pack()),
            ]
        ]
    )


def categories(lang: str, cats: list[dict], counts: dict[str, int]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{CATEGORY_EMOJI.get(c['id'], '•')} {c['name'][lang]} ({counts.get(c['id'], 0)})",
                callback_data=CategoryCb(id=c["id"]).pack(),
            )
        ]
        for c in cats
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_list(lang: str, products: list[Product]) -> InlineKeyboardMarkup:
    rows = []
    for p in products:
        pack = p.smallest_pack
        mark = "⛔️ " if p.sold_out else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark}{p.name[lang]} · {fmt_pack(pack.grams, lang)} {fmt_money(pack.price_cents, lang)}",
                    callback_data=ProductCb(action="view", id=p.id, grams=pack.grams, qty=1).pack(),
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=t(lang, "catalog.back"), callback_data=CategoryCb(id="all").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_card(lang: str, p: Product, grams: int, qty: int, max_qty: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if len(p.packs) > 1:
        rows.append(
            [
                InlineKeyboardButton(
                    text=("● " if pack.grams == grams else "") + fmt_pack(pack.grams, lang),
                    callback_data=ProductCb(action="view", id=p.id, grams=pack.grams, qty=1).pack(),
                )
                for pack in p.packs
            ]
        )
    if not p.sold_out and max_qty > 0:
        pack = p.pack(grams) or p.smallest_pack
        rows.append(
            [
                InlineKeyboardButton(text="➖", callback_data=ProductCb(action="view", id=p.id, grams=grams, qty=max(1, qty - 1)).pack()),
                InlineKeyboardButton(text=str(qty), callback_data=ProductCb(action="view", id=p.id, grams=grams, qty=qty).pack()),
                InlineKeyboardButton(text="➕", callback_data=ProductCb(action="view", id=p.id, grams=grams, qty=min(max_qty, qty + 1)).pack()),
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(lang, "product.add", total=fmt_money(pack.price_cents * qty, lang)),
                    callback_data=ProductCb(action="add", id=p.id, grams=grams, qty=qty).pack(),
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(text=t(lang, "product.back"), callback_data=CategoryCb(id=p.category).pack()),
            InlineKeyboardButton(text=t(lang, "product.open_cart"), callback_data=CartCb(action="show").pack()),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cart(lang: str, lines: list[CartLine], products: dict[str, Product], has_promo: bool) -> InlineKeyboardMarkup:
    rows = []
    for line in lines:
        p = products[line.product_id]
        label = f"{p.name[lang][:22]} {fmt_pack(line.grams, lang)}"
        rows.append([InlineKeyboardButton(text=label, callback_data=ProductCb(action="view", id=p.id, grams=line.grams, qty=1).pack())])
        rows.append(
            [
                InlineKeyboardButton(text="➖", callback_data=CartCb(action="dec", id=p.id, grams=line.grams).pack()),
                InlineKeyboardButton(text=f"× {line.qty}", callback_data=CartCb(action="show").pack()),
                InlineKeyboardButton(text="➕", callback_data=CartCb(action="inc", id=p.id, grams=line.grams).pack()),
                InlineKeyboardButton(text="✖️", callback_data=CartCb(action="del", id=p.id, grams=line.grams).pack()),
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=t(lang, "cart.promo_remove" if has_promo else "cart.promo"),
                callback_data=CartCb(action="unpromo" if has_promo else "promo").pack(),
            ),
            InlineKeyboardButton(text=t(lang, "cart.clear"), callback_data=CartCb(action="clear").pack()),
        ]
    )
    rows.append([InlineKeyboardButton(text=t(lang, "cart.checkout"), callback_data=CartCb(action="checkout").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ask_name(name: str | None) -> ReplyKeyboardMarkup | ReplyKeyboardRemove:
    if not name:
        return ReplyKeyboardRemove()
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=name)]], resize_keyboard=True, one_time_keyboard=True)


def ask_phone(lang: str, saved: str | None) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=t(lang, "checkout.share_phone"), request_contact=True)]]
    if saved:
        rows.append([KeyboardButton(text=saved)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)


def delivery(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "checkout.courier", fee=fmt_money(COURIER_FEE_CENTS, lang), free=fmt_money(FREE_DELIVERY_CENTS, lang)),
                    callback_data=CheckoutCb(step="delivery", value="courier").pack(),
                )
            ],
            [InlineKeyboardButton(text=t(lang, "checkout.pickup"), callback_data=CheckoutCb(step="delivery", value="pickup").pack())],
            [InlineKeyboardButton(text=t(lang, "checkout.cancel"), callback_data=CheckoutCb(step="cancel").pack())],
        ]
    )


def cities(lang: str, city_list: list[dict]) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(text=c[lang], callback_data=CheckoutCb(step="city", value=c["en"]).pack()) for c in city_list]
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(text=t(lang, "checkout.cancel"), callback_data=CheckoutCb(step="cancel").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "checkout.cash"), callback_data=CheckoutCb(step="payment", value="cash").pack())],
            [InlineKeyboardButton(text=t(lang, "checkout.card"), callback_data=CheckoutCb(step="payment", value="card").pack())],
            [InlineKeyboardButton(text=t(lang, "checkout.cancel"), callback_data=CheckoutCb(step="cancel").pack())],
        ]
    )


def confirm(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "checkout.confirm"), callback_data=CheckoutCb(step="confirm").pack())],
            [InlineKeyboardButton(text=t(lang, "checkout.cancel"), callback_data=CheckoutCb(step="cancel").pack())],
        ]
    )


# ----------------------------------------------------------------- admin


def admin_dashboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Open orders", callback_data=AdminCb(action="open").pack()),
                InlineKeyboardButton(text="📉 Low stock", callback_data=AdminCb(action="stock").pack()),
            ],
            [InlineKeyboardButton(text="🔄 Refresh", callback_data=AdminCb(action="dash").pack())],
        ]
    )


def admin_open_orders(orders: list[Order]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{STATUS_EMOJI[o.status]} {o.number} · {o.name[:18]} · {fmt_money(o.total_cents)}",
                callback_data=AdminOrderCb(order_id=o.id).pack(),
            )
        ]
        for o in orders
    ]
    rows.append([InlineKeyboardButton(text="← Dashboard", callback_data=AdminCb(action="dash").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_order(order: Order) -> InlineKeyboardMarkup:
    rows = []
    nxt = NEXT_STATUS.get(order.status)
    if nxt:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{STATUS_EMOJI[nxt]} Mark {t('en', 'status.' + nxt).lower()}",
                    callback_data=AdminOrderCb(order_id=order.id, status=nxt).pack(),
                )
            ]
        )
    if order.status in ("new", "packed", "shipped"):
        rows.append([InlineKeyboardButton(text="❌ Cancel order", callback_data=AdminOrderCb(order_id=order.id, status="cancelled").pack())])
    rows.append([InlineKeyboardButton(text="← Open orders", callback_data=AdminCb(action="open").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)
