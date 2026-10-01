"""Pure pricing and stock rules. No I/O here, so everything is easy to test."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

FREE_DELIVERY_CENTS = 4000
COURIER_FEE_CENTS = 300
PROMO_CODES: dict[str, float] = {"WELCOME10": 0.10}


@dataclass(frozen=True)
class Pack:
    grams: int
    price_cents: int


@dataclass(frozen=True)
class Product:
    id: str
    sku: str
    category: str
    name: dict[str, str]
    origin: dict[str, str]
    description: dict[str, str]
    notes: dict[str, str]
    packs: tuple[Pack, ...]
    stock_grams: int
    reorder_grams: int

    def pack(self, grams: int) -> Pack | None:
        return next((p for p in self.packs if p.grams == grams), None)

    @property
    def smallest_pack(self) -> Pack:
        return min(self.packs, key=lambda p: p.grams)

    @property
    def sold_out(self) -> bool:
        return self.stock_grams < self.smallest_pack.grams

    @property
    def low_stock(self) -> bool:
        return not self.sold_out and self.stock_grams <= self.reorder_grams


@dataclass(frozen=True)
class CartLine:
    product_id: str
    grams: int
    qty: int


@dataclass(frozen=True)
class Totals:
    subtotal_cents: int
    discount_cents: int
    delivery_cents: int
    total_cents: int
    free_delivery_left_cents: int
    item_count: int


def normalize_promo(code: str) -> str | None:
    code = code.strip().upper()
    return code if code in PROMO_CODES else None


def reserved_grams(cart: Iterable[CartLine], product_id: str, except_grams: int | None = None) -> int:
    return sum(l.grams * l.qty for l in cart if l.product_id == product_id and l.grams != except_grams)


def max_addable(product: Product, cart: Iterable[CartLine], grams: int) -> int:
    """How many more packs of this size fit into the stock that is not already in the cart."""
    free = product.stock_grams - reserved_grams(cart, product.id)
    return max(0, free // grams)


def max_qty_for_line(product: Product, cart: Iterable[CartLine], grams: int) -> int:
    free = product.stock_grams - reserved_grams(cart, product.id, except_grams=grams)
    return max(0, free // grams)


def compute_totals(
    cart: Iterable[CartLine],
    products: dict[str, Product],
    promo_code: str | None,
    delivery: str = "courier",
) -> Totals:
    subtotal = 0
    items = 0
    for line in cart:
        product = products.get(line.product_id)
        pack = product.pack(line.grams) if product else None
        if not pack:
            continue
        subtotal += pack.price_cents * line.qty
        items += line.qty
    rate = PROMO_CODES.get(promo_code or "", 0.0)
    discount = round(subtotal * rate)
    after = subtotal - discount
    free = after >= FREE_DELIVERY_CENTS
    delivery_fee = 0 if subtotal == 0 or delivery == "pickup" or free else COURIER_FEE_CENTS
    return Totals(
        subtotal_cents=subtotal,
        discount_cents=discount,
        delivery_cents=delivery_fee,
        total_cents=after + delivery_fee,
        free_delivery_left_cents=0 if free else FREE_DELIVERY_CENTS - after,
        item_count=items,
    )


def is_valid_phone(phone: str) -> bool:
    phone = phone.strip()
    digits = [c for c in phone if c.isdigit()]
    allowed = set("+0123456789 ()-")
    return 9 <= len(digits) <= 15 and all(c in allowed for c in phone)


def fmt_money(cents: int, lang: str = "en") -> str:
    value = f"{cents / 100:,.2f}"
    if lang == "ru":
        return value.replace(",", " ").replace(".", ",") + " $"
    return "$" + value


def fmt_pack(grams: int, lang: str = "en") -> str:
    g, kg = ("г", "кг") if lang == "ru" else ("g", "kg")
    if grams >= 1000 and grams % 1000 == 0:
        return f"{grams // 1000} {kg}"
    if grams >= 1000:
        return f"{grams / 1000:.1f} {kg}".replace(".", "," if lang == "ru" else ".")
    return f"{grams} {g}"


def fmt_kg(grams: int, lang: str = "en") -> str:
    kg = "кг" if lang == "ru" else "kg"
    value = grams / 1000
    text = f"{value:.0f}" if value == int(value) else f"{value:.1f}"
    if lang == "ru":
        text = text.replace(".", ",")
    return f"{text} {kg}"
