import pytest

from bot.db import CheckoutData, StockError

USER = 7
CHECKOUT = CheckoutData(name="Madina", phone="+992 92 123 4567", delivery="courier", city="Khujand", address="Rudaki 12", payment="cash")


async def test_catalog_is_seeded_once(db):
    products = await db.all_products()
    assert len(products) == 18
    await db.seed_products()  # running again must not duplicate or reset stock
    assert len(await db.all_products()) == 18


async def test_cart_merges_lines_and_respects_stock(db):
    await db.ensure_user(USER, "ru")
    assert await db.add_to_cart(USER, "isfara-apricots", 250, 1) == 1
    assert await db.add_to_cart(USER, "isfara-apricots", 250, 2) == 2
    assert [(l.product_id, l.qty) for l in await db.get_cart(USER)] == [("isfara-apricots", 3)]
    # Sold out: walnuts start with zero stock.
    assert await db.add_to_cart(USER, "walnut-halves", 250, 1) == 0
    # Herb tea has 2.6 kg, so at most 26 packs of 100 g.
    assert await db.add_to_cart(USER, "mountain-herb-tea", 100, 50) == 26


async def test_place_order_deducts_stock_and_clears_cart(db):
    await db.ensure_user(USER, "ru")
    before = (await db.get_product("kanibadam-almonds")).stock_grams
    await db.add_to_cart(USER, "kanibadam-almonds", 500, 2)
    await db.set_promo(USER, "welcome10")
    order = await db.place_order(USER, CHECKOUT)

    assert order.number.startswith("MZ-")
    assert order.discount_cents == 224
    assert order.items[0].qty == 2
    assert (await db.get_product("kanibadam-almonds")).stock_grams == before - 1000
    assert await db.get_cart(USER) == []
    assert await db.get_promo(USER) is None
    assert await db.get_contact(USER) == ("Madina", "+992 92 123 4567")


async def test_place_order_fails_when_stock_ran_out(db):
    await db.ensure_user(USER, "ru")
    await db.add_to_cart(USER, "mountain-herb-tea", 100, 20)
    await db.conn.execute("UPDATE products SET stock_grams = 500 WHERE id = 'mountain-herb-tea'")
    with pytest.raises(StockError) as err:
        await db.place_order(USER, CHECKOUT)
    assert err.value.available_grams == 500
    # Nothing was saved and the cart is untouched.
    assert await db.user_orders(USER) == []
    assert len(await db.get_cart(USER)) == 1


async def test_cancelling_returns_stock_and_is_final(db):
    await db.ensure_user(USER, "ru")
    before = (await db.get_product("golden-raisins")).stock_grams
    await db.add_to_cart(USER, "golden-raisins", 1000, 3)
    order = await db.place_order(USER, CHECKOUT)
    assert (await db.set_status(order.id, "packed")).status == "packed"
    assert (await db.set_status(order.id, "cancelled")).status == "cancelled"
    assert (await db.get_product("golden-raisins")).stock_grams == before
    assert await db.set_status(order.id, "shipped") is None


async def test_receive_stock_and_low_stock_list(db):
    low = {p.id for p in await db.low_stock()}
    assert low == {"walnut-halves", "apricot-kernels", "whole-apricots", "mountain-herb-tea"}
    await db.receive_stock("walnut-halves", 12_500)
    assert "walnut-halves" not in {p.id for p in await db.low_stock()}


async def test_stats(db):
    await db.ensure_user(USER, "ru")
    await db.add_to_cart(USER, "isfara-apricots", 1000, 3)
    await db.place_order(USER, CHECKOUT)
    stats = await db.stats()
    assert stats["orders_today"] == 1
    assert stats["revenue_period"] == 4770
    assert stats["open"] == 1
