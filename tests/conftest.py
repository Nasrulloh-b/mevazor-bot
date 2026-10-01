"""Test helpers: a fake Telegram connection so conversations can be tested without the internet."""

from __future__ import annotations

import itertools
from datetime import datetime, timezone
from typing import Any

import pytest
import pytest_asyncio
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import TelegramMethod
from aiogram.types import CallbackQuery, Chat, Contact, Message, Update, User

from bot.app import create_dispatcher
from bot.config import Config
from bot.db import Database

ADMIN_ID = 900
CUSTOMER_ID = 101


class FakeSession(BaseSession):
    """Records every Telegram API call and returns plausible results instead of going online."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []
        self._ids = itertools.count(1000)

    async def make_request(self, bot: Bot, method: TelegramMethod[Any], timeout: int | None = None) -> Any:
        self.calls.append(method)
        name = type(method).__name__
        if name == "GetMe":
            return User(id=bot.id, is_bot=True, first_name="Mevazor", username="mevazor_test_bot")
        if name in ("SendMessage", "EditMessageText"):
            chat_id = getattr(method, "chat_id", None) or CUSTOMER_ID
            return Message(
                message_id=getattr(method, "message_id", None) or next(self._ids),
                date=datetime.now(timezone.utc),
                chat=Chat(id=int(chat_id), type="private"),
                text=method.text,
            )
        return True

    async def close(self) -> None:
        pass

    async def stream_content(self, *args: Any, **kwargs: Any):  # pragma: no cover
        raise NotImplementedError
        yield b""

    # ---- helpers for assertions

    def sent(self, kind: str = "SendMessage", chat_id: int | None = None) -> list[Any]:
        return [c for c in self.calls if type(c).__name__ == kind and (chat_id is None or getattr(c, "chat_id", None) == chat_id)]

    def texts(self, chat_id: int | None = None) -> list[str]:
        return [c.text for c in self.calls if type(c).__name__ in ("SendMessage", "EditMessageText") and (chat_id is None or c.chat_id == chat_id)]

    def last_text(self) -> str:
        return self.texts()[-1]

    def last_markup(self) -> Any:
        for c in reversed(self.calls):
            if type(c).__name__ in ("SendMessage", "EditMessageText"):
                return c.reply_markup
        return None

    def callback_answers(self) -> list[str | None]:
        return [c.text for c in self.calls if type(c).__name__ == "AnswerCallbackQuery"]

    def reset(self) -> None:
        self.calls.clear()


class Chatter:
    """Plays the role of a Telegram user talking to the bot."""

    def __init__(self, dp, bot: Bot, session: FakeSession, user_id: int, first_name: str, lang: str = "ru") -> None:
        self.dp, self.bot, self.session = dp, bot, session
        self.user = User(id=user_id, is_bot=False, first_name=first_name, language_code=lang)
        self.chat = Chat(id=user_id, type="private")
        self._update_ids = itertools.count(1)
        self._message_ids = itertools.count(1)

    def _message(self, **kwargs: Any) -> Message:
        return Message(
            message_id=next(self._message_ids), date=datetime.now(timezone.utc), chat=self.chat, from_user=self.user, **kwargs
        )

    async def say(self, text: str) -> None:
        await self.dp.feed_update(self.bot, Update(update_id=next(self._update_ids), message=self._message(text=text)))

    async def share_contact(self, phone: str) -> None:
        contact = Contact(phone_number=phone, first_name=self.user.first_name, user_id=self.user.id)
        await self.dp.feed_update(self.bot, Update(update_id=next(self._update_ids), message=self._message(contact=contact)))

    async def press(self, data: str) -> None:
        query = CallbackQuery(
            id=str(next(self._update_ids)),
            from_user=self.user,
            chat_instance="test",
            data=data,
            message=self._message(text="…"),
        )
        await self.dp.feed_update(self.bot, Update(update_id=next(self._update_ids), callback_query=query))

    def button(self, contains: str) -> str:
        """Finds callback data of a button on the last keyboard whose label contains `contains`."""
        markup = self.session.last_markup()
        for row in getattr(markup, "inline_keyboard", []) or []:
            for btn in row:
                if contains in btn.text:
                    return btn.callback_data
        raise AssertionError(f"No button containing {contains!r}")


@pytest_asyncio.fixture
async def db():
    database = Database(":memory:")
    await database.connect()
    yield database
    await database.close()


@pytest.fixture
def config() -> Config:
    return Config(bot_token="42:TEST", admin_ids=frozenset({ADMIN_ID}), shop_name="Mevazor", support_phone="+992 92 000 0000")


_dispatcher = None


def get_dispatcher(db: Database, config: Config):
    """One dispatcher per test run (routers can only be attached once); fresh data and state per test."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = create_dispatcher(db, config)
    else:
        _dispatcher["db"] = db
        _dispatcher["config"] = config
        _dispatcher.fsm.storage = MemoryStorage()
    return _dispatcher


@pytest_asyncio.fixture
async def world(db, config):
    session = FakeSession()
    bot = Bot(token=config.bot_token, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = get_dispatcher(db, config)
    customer = Chatter(dp, bot, session, CUSTOMER_ID, "Madina", "ru")
    admin = Chatter(dp, bot, session, ADMIN_ID, "Owner", "en")
    return {"db": db, "session": session, "bot": bot, "dp": dp, "customer": customer, "admin": admin}
