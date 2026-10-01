"""End-to-end conversations with the bot, using the fake Telegram connection from conftest.py."""

from bot.callbacks import AdminOrderCb, CartCb, CategoryCb, CheckoutCb, ProductCb

from .conftest import ADMIN_ID, CUSTOMER_ID


async def test_start_shows_welcome_and_menu(world):
    await world["customer"].say("/start")
    text = world["session"].last_text()
    assert "Салам, Madina" in text
    keyboard = world["session"].last_markup().keyboard
    assert keyboard[0][0].text == "🛍 Каталог"


async def test_browse_and_add_to_cart(world):
    c, s = world["customer"], world["session"]
    await c.say("🛍 Каталог")
    assert "Каталог" in s.last_text()
    await c.press(CategoryCb(id="dried-fruit").pack())
    assert "Сухофрукты" in s.last_text()

    await c.press(c.button("Курага из Исфары"))
    assert "Исфара, Таджикистан" in s.last_text()
    await c.press(c.button("500 г"))  # choose the 500 g pack
    await c.press(c.button("➕"))  # quantity 2
    assert "Количество: <b>2</b>" in s.last_text()
    await c.press(c.button("В корзину"))
    assert any("Добавлено" in (a or "") for a in s.callback_answers())

    cart = await world["db"].get_cart(CUSTOMER_ID)
    assert [(l.product_id, l.grams, l.qty) for l in cart] == [("isfara-apricots", 500, 2)]


async def test_sold_out_product_cannot_be_added(world):
    c, s = world["customer"], world["session"]
    await c.say("/start")
    await c.press(ProductCb(action="add", id="walnut-halves", grams=250, qty=1).pack())
    assert "На складе только 0 кг" in (s.callback_answers()[-1] or "")
    assert await world["db"].get_cart(CUSTOMER_ID) == []


async def test_promo_code(world):
    c, s = world["customer"], world["session"]
    await c.say("/start")
    await c.press(ProductCb(action="add", id="isfara-apricots", grams=250, qty=2).pack())
    await c.press(CartCb(action="promo").pack())
    await c.say("FREEMONEY")
    assert "Такого промокода нет" in s.last_text()
    await c.say("welcome10")
    texts = s.texts()
    assert any("WELCOME10 применён" in x for x in texts)
    assert "Скидка WELCOME10" in s.last_text()


async def test_full_checkout_and_admin_updates_status(world):
    c, a, s, db = world["customer"], world["admin"], world["session"], world["db"]
    await c.say("/start")
    await c.press(ProductCb(action="add", id="kanibadam-almonds", grams=1000, qty=2).pack())
    almonds_before = (await db.get_product("kanibadam-almonds")).stock_grams

    await c.press(CartCb(action="checkout").pack())
    assert "Как вас зовут" in s.last_text()
    await c.say("Madina Saidova")
    await c.say("123")  # invalid phone
    assert "минимум 9 цифр" in s.last_text()
    await c.share_contact("992921234567")
    await c.press(CheckoutCb(step="delivery", value="courier").pack())
    await c.press(CheckoutCb(step="city", value="Khujand").pack())
    await c.say("Rudaki Ave 12, apt 4")
    await c.press(CheckoutCb(step="payment", value="cash").pack())
    summary = s.last_text()
    assert "Проверьте заказ" in summary and "Худжанд, Rudaki Ave 12, apt 4" in summary
    assert "+992921234567" in summary

    s.reset()
    await c.press(CheckoutCb(step="confirm").pack())
    customer_texts = s.texts(CUSTOMER_ID)
    assert any("Заказ MZ-2001 принят" in x for x in customer_texts)
    admin_texts = s.texts(ADMIN_ID)
    assert len(admin_texts) == 1 and "Order MZ-2001" in admin_texts[0] and "Madina Saidova" in admin_texts[0]
    assert (await db.get_product("kanibadam-almonds")).stock_grams == almonds_before - 2000
    assert await db.get_cart(CUSTOMER_ID) == []

    # The owner marks the order as packed; the customer is told.
    s.reset()
    await a.press(AdminOrderCb(order_id=1, status="packed").pack())
    assert any("MZ-2001" in x and "Собран" in x for x in s.texts(CUSTOMER_ID))
    assert (await db.get_order(1)).status == "packed"


async def test_pickup_skips_address(world):
    c, s, db = world["customer"], world["session"], world["db"]
    await c.say("/start")
    await c.press(ProductCb(action="add", id="green-tea-95", grams=100, qty=1).pack())
    await c.press(CartCb(action="checkout").pack())
    await c.say("Aziz")
    await c.say("+992 93 555 1234")
    await c.press(CheckoutCb(step="delivery", value="pickup").pack())
    assert "Как будете платить" in s.last_text()
    await c.press(CheckoutCb(step="payment", value="card").pack())
    await c.press(CheckoutCb(step="confirm").pack())
    order = (await db.user_orders(CUSTOMER_ID))[0]
    assert order.delivery == "pickup" and order.address == "" and order.delivery_cents == 0


async def test_menu_button_leaves_checkout(world):
    c, s = world["customer"], world["session"]
    await c.say("/start")
    await c.press(ProductCb(action="add", id="green-tea-95", grams=100, qty=1).pack())
    await c.press(CartCb(action="checkout").pack())
    await c.say("🛒 Корзина")  # must open the cart, not be taken as the customer's name
    assert "Корзина" in s.last_text() and "Зелёный чай" in s.last_text()


async def test_admin_tools_are_hidden_from_customers(world):
    c, a, s, db = world["customer"], world["admin"], world["session"], world["db"]
    await c.say("/admin")
    assert "Не понял" in s.last_text()

    await a.say("/admin")
    assert "Store dashboard" in s.last_text()
    await a.say("/receive NT-WAL-01 12.5")
    assert "Now in stock: <b>12.5 kg</b>" in s.last_text()
    assert (await db.get_product("walnut-halves")).stock_grams == 12_500


async def test_language_switch(world):
    c, s = world["customer"], world["session"]
    await c.say("/lang")
    await c.press("lang:en")
    assert s.last_markup().keyboard[0][0].text == "🛍 Catalog"
    await c.say("🛍 Catalog")
    assert "Choose a category" in s.last_text()
