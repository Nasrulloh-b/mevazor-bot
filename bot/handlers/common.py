"""/start, language, main menu buttons and the fallback for anything unexpected."""

from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import keyboards as kb
from ..callbacks import LangCb
from ..config import Config
from ..db import Database
from ..texts import all_variants, t
from .cart import show_cart
from .catalog import show_categories
from .checkout import start_checkout
from .orders import show_orders
from .utils import answer_callback

# Menu buttons and commands work from any state, so they also get the user out of an unfinished checkout.
menu = Router(name="menu")
fallback = Router(name="fallback")


@menu.message(CommandStart(), StateFilter("*"))
async def cmd_start(message: Message, state: FSMContext, config: Config, lang: str) -> None:
    await state.clear()
    name = escape(message.from_user.first_name) if message.from_user else ""
    await message.answer(t(lang, "welcome", name=name, shop=config.shop_name), reply_markup=kb.main_menu(lang))


@menu.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await message.answer(t(lang, "cancel.done"), reply_markup=kb.main_menu(lang))


@menu.message(Command("lang"), StateFilter("*"))
@menu.message(F.text.in_(all_variants("menu.lang")), StateFilter("*"))
async def cmd_lang(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(t("ru", "choose_lang"), reply_markup=kb.languages())


@menu.callback_query(LangCb.filter())
async def on_lang(callback: CallbackQuery, callback_data: LangCb, db: Database) -> None:
    lang = callback_data.lang if callback_data.lang in ("ru", "en") else "ru"
    await db.set_lang(callback.from_user.id, lang)
    await answer_callback(callback, t(lang, "lang_set"))
    if isinstance(callback.message, Message):
        await callback.message.answer(t(lang, "menu.hint"), reply_markup=kb.main_menu(lang))


@menu.message(Command("catalog"), StateFilter("*"))
@menu.message(F.text.in_(all_variants("menu.catalog")), StateFilter("*"))
async def menu_catalog(message: Message, state: FSMContext, db: Database, lang: str) -> None:
    await state.clear()
    await show_categories(message, db, lang)


@menu.message(Command("cart"), StateFilter("*"))
@menu.message(F.text.in_(all_variants("menu.cart")), StateFilter("*"))
async def menu_cart(message: Message, state: FSMContext, db: Database, lang: str) -> None:
    assert message.from_user
    await state.clear()
    await show_cart(message, db, lang, message.from_user.id)


@menu.message(Command("checkout"), StateFilter("*"))
async def menu_checkout(message: Message, state: FSMContext, db: Database, lang: str) -> None:
    assert message.from_user
    await start_checkout(message, state, db, lang, message.from_user.id)


@menu.message(Command("orders"), StateFilter("*"))
@menu.message(F.text.in_(all_variants("menu.orders")), StateFilter("*"))
async def menu_orders(message: Message, state: FSMContext, db: Database, lang: str) -> None:
    assert message.from_user
    await state.clear()
    await show_orders(message, db, lang, message.from_user.id)


@menu.message(Command("contact"), StateFilter("*"))
@menu.message(F.text.in_(all_variants("menu.contact")), StateFilter("*"))
async def menu_contact(message: Message, state: FSMContext, config: Config, lang: str) -> None:
    await state.clear()
    await message.answer(t(lang, "contact", phone=escape(config.support_phone)))


@menu.message(Command("myid"), StateFilter("*"))
async def cmd_myid(message: Message) -> None:
    """Shows the sender's Telegram id, which the owner needs for ADMIN_IDS."""
    assert message.from_user
    await message.answer(f"Your Telegram id: <code>{message.from_user.id}</code>")


@fallback.message()
async def unknown_message(message: Message, lang: str) -> None:
    await message.answer(t(lang, "unknown"), reply_markup=kb.main_menu(lang))


@fallback.callback_query()
async def unknown_callback(callback: CallbackQuery) -> None:
    await answer_callback(callback)
