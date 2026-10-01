"""Builds the bot and dispatcher. Kept apart from __main__ so tests can create the same setup."""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault, ErrorEvent

from .config import Config
from .db import Database
from .handlers import build_router
from .middleware import ContextMiddleware
from .texts import t

log = logging.getLogger(__name__)


def create_dispatcher(db: Database, config: Config) -> Dispatcher:
    # db and config become "workflow data": every handler can ask for them by argument name.
    dp = Dispatcher(storage=MemoryStorage(), db=db, config=config)
    dp.update.outer_middleware(ContextMiddleware())
    dp.include_router(build_router())

    @dp.errors()
    async def on_error(event: ErrorEvent, lang: str = "ru") -> bool:
        log.exception("Error while handling update %s", event.update.update_id, exc_info=event.exception)
        message = event.update.message or (event.update.callback_query and event.update.callback_query.message)
        if message is not None:
            try:
                await message.answer(t(lang, "error"))
            except Exception:
                pass
        return True

    return dp


def create_bot(config: Config) -> Bot:
    return Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


async def set_commands(bot: Bot, config: Config) -> None:
    for lang in ("ru", "en"):
        ru = lang == "ru"
        commands = [
            BotCommand(command="start", description="Главное меню" if ru else "Main menu"),
            BotCommand(command="catalog", description="Каталог" if ru else "Catalog"),
            BotCommand(command="cart", description="Корзина" if ru else "Cart"),
            BotCommand(command="orders", description="Мои заказы" if ru else "My orders"),
            BotCommand(command="lang", description="Язык / Language"),
            BotCommand(command="cancel", description="Отменить действие" if ru else "Cancel"),
        ]
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault(), language_code=None if ru else "en")
    admin_commands = [
        BotCommand(command="admin", description="Store dashboard"),
        BotCommand(command="stock", description="Products to reorder"),
        BotCommand(command="receive", description="Add stock: /receive SKU KG"),
        BotCommand(command="start", description="Main menu"),
    ]
    for admin_id in config.admin_ids:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception:
            log.warning("Admin %s has not opened the bot yet; their command menu will appear after /start", admin_id)
