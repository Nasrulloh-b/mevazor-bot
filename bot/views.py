"""Builds message texts from data. Kept separate from handlers so they stay short and testable."""

from __future__ import annotations

from datetime import datetime
from html import escape

from .db import Order
from .pricing import CartLine, Product, Totals, fmt_kg, fmt_money, fmt_pack
from .texts import STATUS_EMOJI, t


def product_text(lang: str, p: Product, grams: int, qty: int) -> str:
    pack = p.pack(grams) or p.smallest_pack
    text = t(
        lang,
        "product.card",
        name=escape(p.name[lang]),
        origin=escape(p.origin[lang]),
        description=escape(p.description[lang]),
        notes=escape(p.notes[lang]),
        sku=p.sku,
        pack=fmt_pack(pack.grams, lang),
        price=fmt_money(pack.price_cents, lang),
        qty=qty,
        line_total=fmt_money(pack.price_cents * qty, lang),
    )
    if p.sold_out:
        text += "\n\n" + t(lang, "product.sold_out")
    elif p.low_stock:
        text += "\n\n" + t(lang, "product.stock_low", kg=fmt_kg(p.stock_grams, lang))
    return text


def totals_text(lang: str, totals: Totals, promo: str | None) -> str:
    parts = [t(lang, "cart.subtotal", amount=fmt_money(totals.subtotal_cents, lang))]
    if totals.discount_cents:
        parts.append(t(lang, "cart.discount", code=promo or "", amount=fmt_money(totals.discount_cents, lang)))
    if totals.delivery_cents:
        parts.append(f"{'Доставка' if lang == 'ru' else 'Delivery'}: {fmt_money(totals.delivery_cents, lang)}")
    parts.append(t(lang, "cart.total", amount=fmt_money(totals.total_cents, lang)))
    return "\n".join(parts)


def cart_lines_text(lang: str, lines: list[CartLine], products: dict[str, Product]) -> str:
    out = []
    for line in lines:
        p = products[line.product_id]
        pack = p.pack(line.grams)
        if not pack:
            continue
        out.append(
            t(
                lang,
                "cart.line",
                name=escape(p.name[lang]),
                pack=fmt_pack(line.grams, lang),
                qty=line.qty,
                total=fmt_money(pack.price_cents * line.qty, lang),
            )
        )
    return "\n".join(out)


def cart_text(lang: str, lines: list[CartLine], products: dict[str, Product], totals: Totals, promo: str | None) -> str:
    hint = (
        t(lang, "cart.delivery_free")
        if totals.free_delivery_left_cents == 0
        else t(lang, "cart.delivery_hint", amount=fmt_money(totals.free_delivery_left_cents, lang))
    )
    return "\n".join([t(lang, "cart.title"), cart_lines_text(lang, lines, products), "", totals_text(lang, totals, promo), "", hint])


def order_date(order: Order) -> str:
    return datetime.fromisoformat(order.created_at).strftime("%d.%m %H:%M")


def admin_order_text(order: Order) -> str:
    items = "\n".join(
        f"• {escape(i.name['en'])} <code>{i.sku}</code> — {i.qty} × {fmt_pack(i.grams)} = {fmt_money(i.unit_cents * i.qty)}"
        for i in order.items
    )
    where = f"🚚 Courier: {escape(order.city)}, {escape(order.address)}" if order.delivery == "courier" else f"🏪 Pickup ({escape(order.city)})"
    lines = [
        f"{STATUS_EMOJI[order.status]} <b>Order {order.number}</b> · {t('en', 'status.' + order.status)}",
        f"🕒 {order_date(order)} UTC",
        "",
        items,
        "",
        f"Subtotal: {fmt_money(order.subtotal_cents)}",
    ]
    if order.discount_cents:
        lines.append(f"Discount {order.promo_code}: −{fmt_money(order.discount_cents)}")
    lines += [
        f"Delivery: {fmt_money(order.delivery_cents)}",
        f"<b>Total: {fmt_money(order.total_cents)}</b> · {'cash' if order.payment == 'cash' else 'card on delivery'}",
        "",
        f"👤 {escape(order.name)} · <code>{escape(order.phone)}</code>",
        where,
    ]
    if order.comment:
        lines.append(f"💬 {escape(order.comment)}")
    return "\n".join(lines)


def low_stock_text(products: list[Product]) -> str:
    if not products:
        return "✅ Every product is above its reorder level."
    rows = ["<b>Reorder soon</b>", ""]
    for p in products:
        mark = "⛔️" if p.sold_out else "⚠️"
        rows.append(f"{mark} {escape(p.name['en'])} <code>{p.sku}</code>\n     {fmt_kg(p.stock_grams)} left, reorder at {fmt_kg(p.reorder_grams)}")
    rows += ["", "Add stock with <code>/receive SKU KG</code>, for example <code>/receive NT-WAL-01 12.5</code>"]
    return "\n".join(rows)


def dashboard_text(stats: dict[str, int]) -> str:
    return "\n".join(
        [
            "<b>📊 Store dashboard</b>",
            "",
            f"Orders today: <b>{stats['orders_today']}</b>",
            f"Orders, last 7 days: <b>{stats['orders_period']}</b>",
            f"Revenue, last 7 days: <b>{fmt_money(stats['revenue_period'])}</b>",
            f"Average order: <b>{fmt_money(stats['average'])}</b>",
            f"Open orders: <b>{stats['open']}</b>",
            f"Products to reorder: <b>{stats['low_stock']}</b>",
        ]
    )
