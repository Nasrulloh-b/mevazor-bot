"""Every piece of text the bot sends, in Russian and English. Messages use Telegram HTML formatting."""

from __future__ import annotations

TEXTS: dict[str, dict[str, str]] = {
    "ru": {
        "welcome": (
            "Салам, {name}! 👋\n\n"
            "Это <b>{shop}</b>: курага, орехи, чай и специи из Ферганской долины с доставкой.\n\n"
            "Выберите раздел в меню ниже."
        ),
        "choose_lang": "Выберите язык / Choose your language",
        "lang_set": "Язык: русский 🇷🇺",
        "menu.catalog": "🛍 Каталог",
        "menu.cart": "🛒 Корзина",
        "menu.orders": "📦 Мои заказы",
        "menu.contact": "☎️ Связаться",
        "menu.lang": "🌐 Language",
        "menu.hint": "Выберите раздел в меню ниже 👇",
        "contact": "Звоните или пишите: <code>{phone}</code>\nРаботаем каждый день с 9:00 до 20:00.\nСамовывоз: базар Панчшанбе, место 14.",
        "catalog.title": "<b>Каталог</b>\nВыберите категорию:",
        "catalog.category": "<b>{category}</b>\nВыберите товар:",
        "catalog.back": "← Категории",
        "product.back": "← Назад",
        "product.card": (
            "<b>{name}</b>\n"
            "<i>{origin}</i>\n\n"
            "{description}\n\n"
            "Вкус: {notes}\n"
            "Артикул: <code>{sku}</code>\n\n"
            "Фасовка: <b>{pack}</b> · {price}\n"
            "Количество: <b>{qty}</b> → <b>{line_total}</b>"
        ),
        "product.stock_low": "⚠️ Осталось {kg}",
        "product.sold_out": "⛔️ Нет в наличии",
        "product.add": "🛒 В корзину · {total}",
        "product.added": "Добавлено: {name}, {qty} × {pack}",
        "product.not_enough": "На складе только {kg}. Уменьшите количество.",
        "product.open_cart": "🛒 Открыть корзину",
        "cart.empty": "Корзина пуста. Загляните в каталог 🛍",
        "cart.title": "<b>Корзина</b>\n",
        "cart.line": "• {name}, {pack} × {qty} = <b>{total}</b>",
        "cart.subtotal": "Товары: {amount}",
        "cart.discount": "Скидка {code}: −{amount}",
        "cart.delivery_hint": "До бесплатной доставки: {amount}",
        "cart.delivery_free": "Доставка курьером бесплатная ✅",
        "cart.total": "<b>Итого: {amount}</b>",
        "cart.checkout": "✅ Оформить заказ",
        "cart.clear": "🗑 Очистить",
        "cart.promo": "🏷 Промокод",
        "cart.promo_remove": "🏷 Убрать промокод",
        "cart.cleared": "Корзина очищена",
        "cart.promo_ask": "Отправьте промокод одним сообщением.\nДля новых покупателей: <code>WELCOME10</code>",
        "cart.promo_ok": "Промокод {code} применён: скидка 10% ✅",
        "cart.promo_bad": "Такого промокода нет. Проверьте написание или отправьте /cancel.",
        "cart.promo_removed": "Промокод убран",
        "checkout.name": "Как вас зовут? Напишите имя или нажмите кнопку ниже.",
        "checkout.name_bad": "Имя должно быть не короче 2 букв.",
        "checkout.phone": "Номер телефона для курьера. Нажмите «📱 Отправить номер» или введите вручную.",
        "checkout.share_phone": "📱 Отправить номер",
        "checkout.phone_bad": "Нужно минимум 9 цифр, например <code>+992 92 123 4567</code>.",
        "checkout.delivery": "Как получить заказ?",
        "checkout.courier": "🚚 Курьер ({fee}, бесплатно от {free})",
        "checkout.pickup": "🏪 Самовывоз с базара, бесплатно",
        "checkout.city": "Выберите город:",
        "checkout.address": "Адрес: улица, дом, квартира.",
        "checkout.address_bad": "Укажите улицу и номер дома.",
        "checkout.payment": "Как будете платить?",
        "checkout.cash": "💵 Наличными курьеру",
        "checkout.card": "💳 Картой при получении",
        "checkout.summary": (
            "<b>Проверьте заказ</b>\n\n"
            "{lines}\n\n"
            "{totals}\n\n"
            "👤 {name}, <code>{phone}</code>\n"
            "{delivery}\n"
            "💰 {payment}"
        ),
        "checkout.to_address": "🚚 {city}, {address}",
        "checkout.to_pickup": "🏪 Самовывоз: базар Панчшанбе, место 14",
        "checkout.confirm": "✅ Подтвердить заказ",
        "checkout.cancel": "✖️ Отменить",
        "checkout.cancelled": "Оформление отменено. Корзина сохранена.",
        "checkout.stock": "Пока вы оформляли, товар «{name}» закончился: осталось {kg}. Измените количество в корзине.",
        "checkout.empty": "Корзина пуста, оформлять нечего.",
        "checkout.done": (
            "🎉 <b>Заказ {number} принят!</b>\n\n"
            "Сумма: <b>{total}</b>\n"
            "{next_step}\n\n"
            "Мы пришлём сообщение, когда статус изменится."
        ),
        "checkout.next_courier": "Курьер позвонит на {phone} перед доставкой.",
        "checkout.next_pickup": "Заказ будет готов к выдаче примерно через 2 часа.",
        "orders.empty": "У вас пока нет заказов.",
        "orders.title": "<b>Ваши последние заказы</b>\n",
        "orders.line": "{emoji} <b>{number}</b> · {date} · {total}\n     {status}",
        "status.new": "Новый",
        "status.packed": "Собран",
        "status.shipped": "В пути",
        "status.delivered": "Доставлен",
        "status.cancelled": "Отменён",
        "status.notify": "{emoji} Заказ <b>{number}</b>: {status}",
        "status.notify.packed": "Заказ собран и ждёт курьера.",
        "status.notify.shipped": "Курьер уже в пути.",
        "status.notify.delivered": "Спасибо за покупку! Будем рады видеть снова.",
        "status.notify.cancelled": "Если это ошибка, свяжитесь с нами.",
        "cancel.done": "Действие отменено.",
        "unknown": "Не понял 🤔 Выберите раздел в меню или отправьте /start.",
        "error": "Что-то пошло не так. Попробуйте ещё раз или отправьте /start.",
    },
    "en": {
        "welcome": (
            "Salam, {name}! 👋\n\n"
            "This is <b>{shop}</b>: dried apricots, nuts, tea and spices from the Fergana Valley, delivered.\n\n"
            "Pick a section from the menu below."
        ),
        "choose_lang": "Выберите язык / Choose your language",
        "lang_set": "Language: English 🇬🇧",
        "menu.catalog": "🛍 Catalog",
        "menu.cart": "🛒 Cart",
        "menu.orders": "📦 My orders",
        "menu.contact": "☎️ Contact",
        "menu.lang": "🌐 Язык",
        "menu.hint": "Pick a section from the menu below 👇",
        "contact": "Call or message us: <code>{phone}</code>\nOpen daily 9:00–20:00.\nPickup: Panjshanbe bazaar, stall 14.",
        "catalog.title": "<b>Catalog</b>\nChoose a category:",
        "catalog.category": "<b>{category}</b>\nChoose a product:",
        "catalog.back": "← Categories",
        "product.back": "← Back",
        "product.card": (
            "<b>{name}</b>\n"
            "<i>{origin}</i>\n\n"
            "{description}\n\n"
            "Tasting notes: {notes}\n"
            "SKU: <code>{sku}</code>\n\n"
            "Pack: <b>{pack}</b> · {price}\n"
            "Quantity: <b>{qty}</b> → <b>{line_total}</b>"
        ),
        "product.stock_low": "⚠️ Only {kg} left",
        "product.sold_out": "⛔️ Sold out",
        "product.add": "🛒 Add to cart · {total}",
        "product.added": "Added: {name}, {qty} × {pack}",
        "product.not_enough": "Only {kg} in stock. Lower the quantity.",
        "product.open_cart": "🛒 Open cart",
        "cart.empty": "Your cart is empty. Have a look at the catalog 🛍",
        "cart.title": "<b>Your cart</b>\n",
        "cart.line": "• {name}, {pack} × {qty} = <b>{total}</b>",
        "cart.subtotal": "Items: {amount}",
        "cart.discount": "Discount {code}: −{amount}",
        "cart.delivery_hint": "Add {amount} more for free delivery",
        "cart.delivery_free": "Courier delivery is free ✅",
        "cart.total": "<b>Total: {amount}</b>",
        "cart.checkout": "✅ Checkout",
        "cart.clear": "🗑 Clear",
        "cart.promo": "🏷 Promo code",
        "cart.promo_remove": "🏷 Remove promo code",
        "cart.cleared": "Cart cleared",
        "cart.promo_ask": "Send the promo code as one message.\nNew customers: <code>WELCOME10</code>",
        "cart.promo_ok": "Code {code} applied: 10% off ✅",
        "cart.promo_bad": "That code doesn't exist. Check the spelling or send /cancel.",
        "cart.promo_removed": "Promo code removed",
        "checkout.name": "What's your name? Type it or tap the button below.",
        "checkout.name_bad": "The name needs at least 2 letters.",
        "checkout.phone": "Phone number for the courier. Tap «📱 Share my number» or type it.",
        "checkout.share_phone": "📱 Share my number",
        "checkout.phone_bad": "Use at least 9 digits, for example <code>+992 92 123 4567</code>.",
        "checkout.delivery": "How would you like to get your order?",
        "checkout.courier": "🚚 Courier ({fee}, free from {free})",
        "checkout.pickup": "🏪 Pick up at the bazaar, free",
        "checkout.city": "Choose your city:",
        "checkout.address": "Address: street, building, apartment.",
        "checkout.address_bad": "Enter a street and building number.",
        "checkout.payment": "How will you pay?",
        "checkout.cash": "💵 Cash to the courier",
        "checkout.card": "💳 Card on delivery",
        "checkout.summary": (
            "<b>Check your order</b>\n\n"
            "{lines}\n\n"
            "{totals}\n\n"
            "👤 {name}, <code>{phone}</code>\n"
            "{delivery}\n"
            "💰 {payment}"
        ),
        "checkout.to_address": "🚚 {city}, {address}",
        "checkout.to_pickup": "🏪 Pickup: Panjshanbe bazaar, stall 14",
        "checkout.confirm": "✅ Confirm order",
        "checkout.cancel": "✖️ Cancel",
        "checkout.cancelled": "Checkout cancelled. Your cart is saved.",
        "checkout.stock": "While you were checking out, «{name}» ran low: {kg} left. Change the quantity in your cart.",
        "checkout.empty": "Your cart is empty, so there is nothing to check out.",
        "checkout.done": (
            "🎉 <b>Order {number} received!</b>\n\n"
            "Total: <b>{total}</b>\n"
            "{next_step}\n\n"
            "We'll message you when the status changes."
        ),
        "checkout.next_courier": "The courier will call {phone} before delivery.",
        "checkout.next_pickup": "Your order will be ready for pickup in about 2 hours.",
        "orders.empty": "You have no orders yet.",
        "orders.title": "<b>Your recent orders</b>\n",
        "orders.line": "{emoji} <b>{number}</b> · {date} · {total}\n     {status}",
        "status.new": "New",
        "status.packed": "Packed",
        "status.shipped": "On the way",
        "status.delivered": "Delivered",
        "status.cancelled": "Cancelled",
        "status.notify": "{emoji} Order <b>{number}</b>: {status}",
        "status.notify.packed": "Your order is packed and waiting for the courier.",
        "status.notify.shipped": "The courier is on the way.",
        "status.notify.delivered": "Thanks for shopping with us!",
        "status.notify.cancelled": "If this is a mistake, please contact us.",
        "cancel.done": "Cancelled.",
        "unknown": "I didn't catch that 🤔 Pick a section from the menu or send /start.",
        "error": "Something went wrong. Please try again or send /start.",
    },
}

CATEGORY_EMOJI = {"dried-fruit": "🍇", "nuts": "🥜", "tea": "🍵", "sweets": "🍬", "spices": "🌶"}
STATUS_EMOJI = {"new": "🆕", "packed": "📦", "shipped": "🚚", "delivered": "✅", "cancelled": "❌"}


def t(lang: str, key: str, **kwargs: object) -> str:
    table = TEXTS.get(lang) or TEXTS["ru"]
    text = table.get(key) or TEXTS["en"].get(key) or key
    return text.format(**kwargs) if kwargs else text


def all_variants(key: str) -> set[str]:
    """The same button label in every language, so menu buttons work whatever language the keyboard was sent in."""
    return {table[key] for table in TEXTS.values() if key in table}
