# Mevazor Order Bot

A Telegram bot for a small shop that sells dried fruit, nuts, tea and spices by weight. Customers browse the catalog, fill a cart and place orders without leaving Telegram. The owner gets every new order in a private chat, moves it through its statuses with one tap, and the customer is notified at each step.

Built with **Python 3.11+, aiogram 3 and SQLite**. It is the companion to the [Mevazor web store](../   (https://github.com/Nasrulloh-b/mevazor-store)) and uses the same catalog and pricing rules.

## Features

**For customers**
- Russian and English interface, picked from the Telegram app language and switchable with /lang
- Catalog by category, product cards with origin and tasting notes, pack sizes (100 g to 1 kg) and a quantity picker
- Cart with ➖ ➕ controls, promo codes (`WELCOME10` gives 10% off) and a free-delivery hint
- Guided checkout: name → phone (one-tap "share my number") → courier or pickup → city and address → cash or card on delivery → confirmation
- Order history and a message every time the order status changes

**For the store owner**
- Instant notification of each new order, with buttons to mark it packed → on the way → delivered, or cancel it
- `/admin` dashboard: orders today, 7-day revenue, average order, open orders, products to reorder
- `/stock` lists products at or below their reorder level
- `/receive SKU KG` adds a delivery to stock, for example `/receive NT-WAL-01 12.5`

**Rules the bot enforces**
- Stock is kept in grams; every pack size draws from the same bulk stock
- Customers can't add more than is on the shelf, and stock is checked again at the moment of ordering
- Placing an order deducts stock in a single database transaction; cancelling returns it
- Tapping a menu button in the middle of checkout leaves checkout instead of being read as an answer

## Run it

### 1. Create the bot in Telegram
1. Open [@BotFather](https://t.me/BotFather), send `/newbot`, choose a name and a username ending in `bot`.
2. Copy the token it gives you. Treat it like a password.

### 2. Install
```bash
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure
Copy `.env.example` to `.env` and paste your token into `BOT_TOKEN`.

To become the admin: start the bot once, send it `/myid`, put that number into `ADMIN_IDS` in `.env`, and restart the bot.

### 4. Start
```bash
python -m bot
```
Open your bot in Telegram and send `/start`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

21 tests cover pricing, stock and the database, plus full conversations (browsing, promo codes, checkout, sold-out items, admin status changes, language switching). The conversation tests replace the Telegram connection with a fake one, so they run offline in under a second.

## Project structure

```
bot/
  __main__.py      entry point (python -m bot)
  app.py           builds the bot and dispatcher, error handler, command menus
  config.py        settings from .env
  db.py            SQLite schema and all queries (orders, stock, cart)
  pricing.py       totals, promo codes, stock limits, formatting (pure functions)
  texts.py         every message in Russian and English
  keyboards.py     reply and inline keyboards
  callbacks.py     button payloads and checkout states
  views.py         turns data into message text
  middleware.py    adds the user's language and admin flag to every update
  handlers/        catalog, cart, checkout, admin, menu
  data/catalog.json   starting catalog, loaded into the database on first run
tests/
```

## Deploy

The bot uses long polling, so any machine that stays online works: a small VPS, a home server or a Raspberry Pi. With Docker:

```bash
docker build -t mevazor-bot .
docker run -d --name mevazor-bot --env-file .env -v mevazor-data:/app/data --restart unless-stopped mevazor-bot
```

The database lives in the `mevazor-data` volume, so orders survive restarts and updates.

## Adapting it for another shop

- Replace `bot/data/catalog.json` with the shop's products (delete the `.db` file so it reloads).
- Edit texts in `bot/texts.py`, delivery fee and free-delivery threshold in `bot/pricing.py`.
- Swap SQLite for PostgreSQL when several staff members or a website need to share the same orders.

## License

MIT
