"""SQLite storage: products and stock, carts, orders."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from .pricing import CartLine, Pack, Product, compute_totals, max_addable, max_qty_for_line, normalize_promo

CATALOG_FILE = Path(__file__).parent / "data" / "catalog.json"

STATUSES = ("new", "packed", "shipped", "delivered", "cancelled")
OPEN_STATUSES = ("new", "packed", "shipped")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY,          -- Telegram user id
    lang        TEXT NOT NULL DEFAULT 'ru',
    name        TEXT,
    phone       TEXT,
    promo_code  TEXT,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS products (
    id             TEXT PRIMARY KEY,
    sku            TEXT NOT NULL UNIQUE,
    category       TEXT NOT NULL,
    data           TEXT NOT NULL,             -- names, origin, description, packs as JSON
    stock_grams    INTEGER NOT NULL,
    reorder_grams  INTEGER NOT NULL,
    position       INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS cart_items (
    user_id     INTEGER NOT NULL,
    product_id  TEXT NOT NULL REFERENCES products(id),
    grams       INTEGER NOT NULL,
    qty         INTEGER NOT NULL CHECK (qty > 0),
    PRIMARY KEY (user_id, product_id, grams)
);
CREATE TABLE IF NOT EXISTS orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    created_at      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'new',
    delivery        TEXT NOT NULL,
    payment         TEXT NOT NULL,
    name            TEXT NOT NULL,
    phone           TEXT NOT NULL,
    city            TEXT NOT NULL,
    address         TEXT NOT NULL DEFAULT '',
    comment         TEXT NOT NULL DEFAULT '',
    promo_code      TEXT,
    subtotal_cents  INTEGER NOT NULL,
    discount_cents  INTEGER NOT NULL,
    delivery_cents  INTEGER NOT NULL,
    total_cents     INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS order_items (
    order_id    INTEGER NOT NULL REFERENCES orders(id),
    product_id  TEXT NOT NULL,
    sku         TEXT NOT NULL,
    name_en     TEXT NOT NULL,
    name_ru     TEXT NOT NULL,
    grams       INTEGER NOT NULL,
    qty         INTEGER NOT NULL,
    unit_cents  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
"""

# Order numbers shown to people start at MZ-2001 so the first customer is not "order #1".
ORDER_NUMBER_OFFSET = 2000


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class OrderItem:
    product_id: str
    sku: str
    name: dict[str, str]
    grams: int
    qty: int
    unit_cents: int


@dataclass
class Order:
    id: int
    user_id: int
    created_at: str
    status: str
    delivery: str
    payment: str
    name: str
    phone: str
    city: str
    address: str
    comment: str
    promo_code: str | None
    subtotal_cents: int
    discount_cents: int
    delivery_cents: int
    total_cents: int
    items: list[OrderItem] = field(default_factory=list)

    @property
    def number(self) -> str:
        return f"MZ-{self.id + ORDER_NUMBER_OFFSET}"


@dataclass
class CheckoutData:
    name: str
    phone: str
    delivery: str  # courier | pickup
    city: str
    address: str
    payment: str  # cash | card
    comment: str = ""


class StockError(Exception):
    def __init__(self, product: Product, available_grams: int):
        super().__init__(f"Not enough {product.sku}")
        self.product = product
        self.available_grams = available_grams


class EmptyCartError(Exception):
    pass


def _row_to_product(row: aiosqlite.Row) -> Product:
    data = json.loads(row["data"])
    return Product(
        id=row["id"],
        sku=row["sku"],
        category=row["category"],
        name=data["name"],
        origin=data["origin"],
        description=data["description"],
        notes=data["notes"],
        packs=tuple(Pack(p["grams"], p["priceCents"]) for p in data["packs"]),
        stock_grams=row["stock_grams"],
        reorder_grams=row["reorder_grams"],
    )


def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG_FILE.read_text(encoding="utf-8"))


class Database:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self._conn: aiosqlite.Connection | None = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        return self._conn

    async def connect(self) -> None:
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        # Autocommit mode: single statements commit immediately, multi-step changes use explicit BEGIN IMMEDIATE.
        self._conn = await aiosqlite.connect(self.path, isolation_level=None)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()
        await self.seed_products()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def seed_products(self) -> None:
        """Loads the starting catalog on first run. Existing stock is never overwritten."""
        async with self.conn.execute("SELECT COUNT(*) FROM products") as cur:
            (count,) = await cur.fetchone()
        if count:
            return
        catalog = load_catalog()
        for position, p in enumerate(catalog["products"]):
            data = {k: p[k] for k in ("name", "origin", "description", "notes", "packs")}
            await self.conn.execute(
                "INSERT INTO products (id, sku, category, data, stock_grams, reorder_grams, position) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (p["id"], p["sku"], p["category"], json.dumps(data, ensure_ascii=False), p["stockGrams"], p["reorderGrams"], position),
            )
        await self.conn.commit()

    # ---------------------------------------------------------------- users

    async def ensure_user(self, user_id: int, default_lang: str) -> str:
        """Creates the user on first contact and returns their language."""
        await self.conn.execute(
            "INSERT OR IGNORE INTO users (id, lang, created_at) VALUES (?, ?, ?)",
            (user_id, default_lang, now_iso()),
        )
        await self.conn.commit()
        async with self.conn.execute("SELECT lang FROM users WHERE id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        return row["lang"]

    async def set_lang(self, user_id: int, lang: str) -> None:
        await self.conn.execute("UPDATE users SET lang = ? WHERE id = ?", (lang, user_id))
        await self.conn.commit()

    async def get_contact(self, user_id: int) -> tuple[str | None, str | None]:
        async with self.conn.execute("SELECT name, phone FROM users WHERE id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        return (row["name"], row["phone"]) if row else (None, None)

    async def save_contact(self, user_id: int, name: str, phone: str) -> None:
        await self.conn.execute("UPDATE users SET name = ?, phone = ? WHERE id = ?", (name, phone, user_id))
        await self.conn.commit()

    async def get_promo(self, user_id: int) -> str | None:
        async with self.conn.execute("SELECT promo_code FROM users WHERE id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        return row["promo_code"] if row else None

    async def set_promo(self, user_id: int, code: str | None) -> str | None:
        """Stores a valid promo code (or clears it with None). Returns the stored code or None if invalid."""
        normalized = normalize_promo(code) if code else None
        if code and not normalized:
            return None
        await self.conn.execute("UPDATE users SET promo_code = ? WHERE id = ?", (normalized, user_id))
        await self.conn.commit()
        return normalized

    # ------------------------------------------------------------- products

    async def all_products(self) -> dict[str, Product]:
        async with self.conn.execute("SELECT * FROM products ORDER BY position") as cur:
            rows = await cur.fetchall()
        return {r["id"]: _row_to_product(r) for r in rows}

    async def products_in(self, category: str) -> list[Product]:
        async with self.conn.execute("SELECT * FROM products WHERE category = ? ORDER BY position", (category,)) as cur:
            rows = await cur.fetchall()
        return [_row_to_product(r) for r in rows]

    async def get_product(self, product_id: str) -> Product | None:
        async with self.conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cur:
            row = await cur.fetchone()
        return _row_to_product(row) if row else None

    async def get_product_by_sku(self, sku: str) -> Product | None:
        async with self.conn.execute("SELECT * FROM products WHERE UPPER(sku) = UPPER(?)", (sku.strip(),)) as cur:
            row = await cur.fetchone()
        return _row_to_product(row) if row else None

    async def receive_stock(self, product_id: str, grams: int) -> Product | None:
        if grams <= 0:
            return await self.get_product(product_id)
        await self.conn.execute("UPDATE products SET stock_grams = stock_grams + ? WHERE id = ?", (grams, product_id))
        await self.conn.commit()
        return await self.get_product(product_id)

    async def low_stock(self) -> list[Product]:
        products = await self.all_products()
        items = [p for p in products.values() if p.sold_out or p.low_stock]
        return sorted(items, key=lambda p: p.stock_grams / max(p.reorder_grams, 1))

    # ----------------------------------------------------------------- cart

    async def get_cart(self, user_id: int) -> list[CartLine]:
        async with self.conn.execute(
            "SELECT c.product_id, c.grams, c.qty FROM cart_items c JOIN products p ON p.id = c.product_id "
            "WHERE c.user_id = ? ORDER BY p.position, c.grams",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
        return [CartLine(r["product_id"], r["grams"], r["qty"]) for r in rows]

    async def add_to_cart(self, user_id: int, product_id: str, grams: int, qty: int) -> int:
        """Adds up to `qty` packs, limited by stock. Returns how many were actually added."""
        product = await self.get_product(product_id)
        if not product or not product.pack(grams) or qty <= 0:
            return 0
        cart = await self.get_cart(user_id)
        added = min(qty, max_addable(product, cart, grams))
        if added <= 0:
            return 0
        await self.conn.execute(
            "INSERT INTO cart_items (user_id, product_id, grams, qty) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (user_id, product_id, grams) DO UPDATE SET qty = qty + excluded.qty",
            (user_id, product_id, grams, added),
        )
        await self.conn.commit()
        return added

    async def set_qty(self, user_id: int, product_id: str, grams: int, qty: int) -> int:
        """Sets a line's quantity (0 removes it), capped at stock. Returns the stored quantity."""
        product = await self.get_product(product_id)
        if not product:
            return 0
        cart = await self.get_cart(user_id)
        qty = max(0, min(qty, max_qty_for_line(product, cart, grams)))
        if qty == 0:
            await self.conn.execute(
                "DELETE FROM cart_items WHERE user_id = ? AND product_id = ? AND grams = ?", (user_id, product_id, grams)
            )
        else:
            await self.conn.execute(
                "UPDATE cart_items SET qty = ? WHERE user_id = ? AND product_id = ? AND grams = ?",
                (qty, user_id, product_id, grams),
            )
        await self.conn.commit()
        return qty

    async def clear_cart(self, user_id: int) -> None:
        await self.conn.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
        await self.conn.commit()

    # --------------------------------------------------------------- orders

    async def place_order(self, user_id: int, data: CheckoutData) -> Order:
        """Checks stock, deducts it, saves the order and empties the cart, all in one transaction."""
        await self.conn.execute("BEGIN IMMEDIATE")
        try:
            cart = await self.get_cart(user_id)
            if not cart:
                raise EmptyCartError()
            products = await self.all_products()
            needed: dict[str, int] = {}
            for line in cart:
                needed[line.product_id] = needed.get(line.product_id, 0) + line.grams * line.qty
            for pid, grams in needed.items():
                if grams > products[pid].stock_grams:
                    raise StockError(products[pid], products[pid].stock_grams)

            promo = await self.get_promo(user_id)
            totals = compute_totals(cart, products, promo, data.delivery)
            cur = await self.conn.execute(
                "INSERT INTO orders (user_id, created_at, status, delivery, payment, name, phone, city, address, comment, "
                "promo_code, subtotal_cents, discount_cents, delivery_cents, total_cents) "
                "VALUES (?, ?, 'new', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    now_iso(),
                    data.delivery,
                    data.payment,
                    data.name.strip(),
                    data.phone.strip(),
                    data.city,
                    data.address.strip() if data.delivery == "courier" else "",
                    data.comment.strip(),
                    promo,
                    totals.subtotal_cents,
                    totals.discount_cents,
                    totals.delivery_cents,
                    totals.total_cents,
                ),
            )
            order_id = cur.lastrowid
            for line in cart:
                p = products[line.product_id]
                pack = p.pack(line.grams)
                await self.conn.execute(
                    "INSERT INTO order_items (order_id, product_id, sku, name_en, name_ru, grams, qty, unit_cents) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (order_id, p.id, p.sku, p.name["en"], p.name["ru"], line.grams, line.qty, pack.price_cents),
                )
            for pid, grams in needed.items():
                await self.conn.execute("UPDATE products SET stock_grams = stock_grams - ? WHERE id = ?", (grams, pid))
            await self.conn.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
            await self.conn.execute(
                "UPDATE users SET promo_code = NULL, name = ?, phone = ? WHERE id = ?",
                (data.name.strip(), data.phone.strip(), user_id),
            )
            await self.conn.commit()
        except Exception:
            await self.conn.rollback()
            raise
        order = await self.get_order(order_id)
        assert order is not None
        return order

    async def get_order(self, order_id: int) -> Order | None:
        async with self.conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return None
        order = Order(**{k: row[k] for k in row.keys()})
        async with self.conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)) as cur:
            items = await cur.fetchall()
        order.items = [
            OrderItem(i["product_id"], i["sku"], {"en": i["name_en"], "ru": i["name_ru"]}, i["grams"], i["qty"], i["unit_cents"])
            for i in items
        ]
        return order

    async def user_orders(self, user_id: int, limit: int = 5) -> list[Order]:
        async with self.conn.execute(
            "SELECT id FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)
        ) as cur:
            ids = [r["id"] for r in await cur.fetchall()]
        return [o for o in [await self.get_order(i) for i in ids] if o]

    async def open_orders(self, limit: int = 20) -> list[Order]:
        placeholders = ",".join("?" * len(OPEN_STATUSES))
        async with self.conn.execute(
            f"SELECT id FROM orders WHERE status IN ({placeholders}) ORDER BY id LIMIT ?", (*OPEN_STATUSES, limit)
        ) as cur:
            ids = [r["id"] for r in await cur.fetchall()]
        return [o for o in [await self.get_order(i) for i in ids] if o]

    async def set_status(self, order_id: int, status: str) -> Order | None:
        """Moves an order to a new status. Cancelling returns the goods to stock. Cancelled orders are final."""
        if status not in STATUSES:
            raise ValueError(status)
        order = await self.get_order(order_id)
        if not order or order.status == status or order.status == "cancelled":
            return None
        await self.conn.execute("BEGIN IMMEDIATE")
        try:
            await self.conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
            if status == "cancelled":
                for item in order.items:
                    await self.conn.execute(
                        "UPDATE products SET stock_grams = stock_grams + ? WHERE id = ?",
                        (item.grams * item.qty, item.product_id),
                    )
            await self.conn.commit()
        except Exception:
            await self.conn.rollback()
            raise
        return await self.get_order(order_id)

    async def stats(self, days: int = 7) -> dict[str, int]:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
        today = datetime.now(timezone.utc).date().isoformat()
        async with self.conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(total_cents), 0) AS revenue FROM orders "
            "WHERE status != 'cancelled' AND created_at >= ?",
            (since,),
        ) as cur:
            week = await cur.fetchone()
        async with self.conn.execute(
            "SELECT COUNT(*) AS n FROM orders WHERE status != 'cancelled' AND substr(created_at, 1, 10) = ?", (today,)
        ) as cur:
            today_row = await cur.fetchone()
        placeholders = ",".join("?" * len(OPEN_STATUSES))
        async with self.conn.execute(f"SELECT COUNT(*) AS n FROM orders WHERE status IN ({placeholders})", OPEN_STATUSES) as cur:
            open_row = await cur.fetchone()
        return {
            "orders_today": today_row["n"],
            "orders_period": week["n"],
            "revenue_period": week["revenue"],
            "average": round(week["revenue"] / week["n"]) if week["n"] else 0,
            "open": open_row["n"],
            "low_stock": len(await self.low_stock()),
        }
