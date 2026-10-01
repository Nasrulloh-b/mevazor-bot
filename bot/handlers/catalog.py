"""Catalog: categories, product lists and product cards."""

from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery, Message

from .. import keyboards as kb
from ..callbacks import CategoryCb, ProductCb
from ..db import Database, load_catalog
from ..pricing import fmt_kg, fmt_pack, max_addable
from ..texts import CATEGORY_EMOJI, t
from ..views import product_text
from .utils import answer_callback, show

router = Router(name="catalog")
CATEGORIES = load_catalog()["categories"]


async def show_categories(target: Message | CallbackQuery, db: Database, lang: str) -> None:
    products = await db.all_products()
    counts: dict[str, int] = {}
    for p in products.values():
        counts[p.category] = counts.get(p.category, 0) + 1
    await show(target, t(lang, "catalog.title"), kb.categories(lang, CATEGORIES, counts))


@router.callback_query(CategoryCb.filter())
async def on_category(callback: CallbackQuery, callback_data: CategoryCb, db: Database, lang: str) -> None:
    if callback_data.id == "all":
        await show_categories(callback, db, lang)
    else:
        category = next((c for c in CATEGORIES if c["id"] == callback_data.id), None)
        if category is None:
            await answer_callback(callback)
            return
        products = await db.products_in(category["id"])
        title = f"{CATEGORY_EMOJI.get(category['id'], '')} {category['name'][lang]}".strip()
        await show(callback, t(lang, "catalog.category", category=title), kb.product_list(lang, products))
    await answer_callback(callback)


@router.callback_query(ProductCb.filter())
async def on_product(callback: CallbackQuery, callback_data: ProductCb, db: Database, lang: str) -> None:
    product = await db.get_product(callback_data.id)
    if product is None:
        await answer_callback(callback)
        return
    grams = callback_data.grams if product.pack(callback_data.grams) else product.smallest_pack.grams
    user_id = callback.from_user.id

    if callback_data.action == "add":
        added = await db.add_to_cart(user_id, product.id, grams, callback_data.qty)
        if added:
            await answer_callback(
                callback, t(lang, "product.added", name=product.name[lang], qty=added, pack=fmt_pack(grams, lang))
            )
        else:
            await answer_callback(callback, t(lang, "product.not_enough", kg=fmt_kg(product.stock_grams, lang)), alert=True)
        qty = 1
    else:
        qty = max(1, callback_data.qty)
        await answer_callback(callback)

    cart = await db.get_cart(user_id)
    max_qty = max_addable(product, cart, grams)
    qty = min(qty, max(1, max_qty))
    await show(callback, product_text(lang, product, grams, qty), kb.product_card(lang, product, grams, qty, max_qty))
