"""Store-owner tools. Only Telegram accounts listed in ADMIN_IDS can use them."""

from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject, Filter
from aiogram.types import CallbackQuery, Message, TelegramObject

from .. import keyboards as kb
from ..callbacks import AdminCb, AdminOrderCb
from ..db import STATUSES, Database
from ..pricing import fmt_kg
from ..texts import STATUS_EMOJI, t
from ..views import admin_order_text, dashboard_text, low_stock_text
from .utils import answer_callback, show

router = Router(name="admin")
log = logging.getLogger(__name__)



class IsAdmin(Filter):
    """Passes only for accounts in ADMIN_IDS (the middleware sets `is_admin`)."""

    async def __call__(self, event: TelegramObject, is_admin: bool = False) -> bool:
        return is_admin


router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(Command("admin"))
async def cmd_admin(message: Message, db: Database) -> None:
    await message.answer(dashboard_text(await db.stats()), reply_markup=kb.admin_dashboard())


@router.message(Command("stock"))
async def cmd_stock(message: Message, db: Database) -> None:
    await message.answer(low_stock_text(await db.low_stock()))


@router.message(Command("receive"))
async def cmd_receive(message: Message, command: CommandObject, db: Database) -> None:
    usage = "Usage: <code>/receive SKU KG</code>, for example <code>/receive NT-WAL-01 12.5</code>"
    parts = (command.args or "").split()
    if len(parts) != 2:
        await message.answer(usage)
        return
    sku, amount = parts
    try:
        kg = float(amount.replace(",", "."))
    except ValueError:
        await message.answer(usage)
        return
    if kg <= 0 or kg > 10_000:
        await message.answer("The amount must be between 0 and 10 000 kg.")
        return
    product = await db.get_product_by_sku(sku)
    if product is None:
        await message.answer(f"No product with SKU <code>{sku}</code>. Send /stock to see SKUs that need restocking.")
        return
    updated = await db.receive_stock(product.id, round(kg * 1000))
    assert updated is not None
    await message.answer(
        f"✅ Added {fmt_kg(round(kg * 1000))} to {product.name['en']}.\nNow in stock: <b>{fmt_kg(updated.stock_grams)}</b>"
    )


@router.callback_query(AdminCb.filter())
async def on_admin_nav(callback: CallbackQuery, callback_data: AdminCb, db: Database) -> None:
    await answer_callback(callback)
    if callback_data.action == "open":
        orders = await db.open_orders()
        text = f"<b>Open orders: {len(orders)}</b>" if orders else "No open orders right now. 🎉"
        await show(callback, text, kb.admin_open_orders(orders))
    elif callback_data.action == "stock":
        await show(callback, low_stock_text(await db.low_stock()), kb.admin_open_orders([]))
    else:
        await show(callback, dashboard_text(await db.stats()), kb.admin_dashboard())


@router.callback_query(AdminOrderCb.filter())
async def on_admin_order(callback: CallbackQuery, callback_data: AdminOrderCb, db: Database, bot: Bot) -> None:
    if callback_data.status and callback_data.status in STATUSES:
        order = await db.set_status(callback_data.order_id, callback_data.status)
        if order is None:
            await answer_callback(callback, "This order was already updated.", alert=True)
            order = await db.get_order(callback_data.order_id)
        else:
            await answer_callback(callback, f"{order.number}: {t('en', 'status.' + order.status)}")
            await notify_customer(bot, db, order.user_id, order.number, order.status)
    else:
        order = await db.get_order(callback_data.order_id)
        await answer_callback(callback)
    if order:
        await show(callback, admin_order_text(order), kb.admin_order(order))


async def notify_customer(bot: Bot, db: Database, user_id: int, number: str, status: str) -> None:
    lang = await db.ensure_user(user_id, "ru")
    text = t(lang, "status.notify", emoji=STATUS_EMOJI[status], number=number, status=t(lang, "status." + status))
    extra = t(lang, "status.notify." + status) if status != "new" else ""
    try:
        await bot.send_message(user_id, f"{text}\n{extra}".strip())
    except Exception:  # the customer may have blocked the bot
        log.warning("Could not notify customer %s about %s", user_id, number)
