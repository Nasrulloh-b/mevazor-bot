from bot.pricing import (
    COURIER_FEE_CENTS,
    CartLine,
    Pack,
    Product,
    compute_totals,
    fmt_kg,
    fmt_money,
    fmt_pack,
    is_valid_phone,
    max_addable,
    normalize_promo,
)


def make_product(stock=42_000, reorder=10_000, packs=((250, 450), (500, 840), (1000, 1590))) -> Product:
    return Product(
        id="apricots",
        sku="DF-APR-01",
        category="dried-fruit",
        name={"en": "Apricots", "ru": "Курага"},
        origin={"en": "", "ru": ""},
        description={"en": "", "ru": ""},
        notes={"en": "", "ru": ""},
        packs=tuple(Pack(g, c) for g, c in packs),
        stock_grams=stock,
        reorder_grams=reorder,
    )


def test_totals_with_courier_fee_and_promo():
    p = make_product()
    cart = [CartLine("apricots", 500, 5)]
    totals = compute_totals(cart, {p.id: p}, "WELCOME10")
    assert totals.subtotal_cents == 4200
    assert totals.discount_cents == 420
    # 37.80 after discount is below the 40.00 threshold, so courier delivery is charged.
    assert totals.delivery_cents == COURIER_FEE_CENTS
    assert totals.total_cents == 4200 - 420 + COURIER_FEE_CENTS


def test_free_delivery_and_pickup():
    p = make_product()
    assert compute_totals([CartLine("apricots", 1000, 3)], {p.id: p}, None).delivery_cents == 0
    assert compute_totals([CartLine("apricots", 250, 1)], {p.id: p}, None, "pickup").delivery_cents == 0


def test_stock_limits():
    p = make_product(stock=2600, packs=((100, 440),))
    assert max_addable(p, [], 100) == 26
    assert max_addable(p, [CartLine("apricots", 100, 20)], 100) == 6
    assert make_product(stock=0).sold_out
    assert make_product(stock=5000, reorder=8000).low_stock


def test_promo_and_phone_validation():
    assert normalize_promo(" welcome10 ") == "WELCOME10"
    assert normalize_promo("free") is None
    assert is_valid_phone("+992 92 123 4567")
    assert not is_valid_phone("12345")
    assert not is_valid_phone("call me maybe")


def test_formatting():
    assert fmt_money(123456) == "$1,234.56"
    assert fmt_money(123456, "ru") == "1 234,56 $"
    assert fmt_pack(250, "ru") == "250 г"
    assert fmt_pack(1000) == "1 kg"
    assert fmt_kg(6500, "ru") == "6,5 кг"
