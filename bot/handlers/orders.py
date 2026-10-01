"""Customer's order history."""

from __future__ import annotations

from aiogram.types import CallbackQuery, Message

from ..db import Database
from ..pricing import fmt_money
from ..texts import STATUS_EMOJI, t
from ..views import order_date
from .utils import show


async def show_orders(target: Message | CallbackQuery, db: Database, lang: str, user_id: int) -> None:
    orders = await db.user_orders(user_id, limit=5)
    if not orders:
        await show(target, t(lang, "orders.empty"))
        return
    lines = [t(lang, "orders.title")]
    for o in orders:
        lines.append(
            t(
                lang,
                "orders.line",
                emoji=STATUS_EMOJI[o.status],
                number=o.number,
                date=order_date(o),
                total=fmt_money(o.total_cents, lang),
                status=t(lang, "status." + o.status),
            )
        )
    await show(target, "\n".join(lines))
