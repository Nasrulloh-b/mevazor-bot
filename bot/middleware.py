"""Middleware that gives every handler the database, settings and the user's language."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from .config import Config
from .db import Database


class ContextMiddleware(BaseMiddleware):
    """Reads `db` and `config` from the dispatcher's workflow data and adds `lang` and `is_admin`."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        db: Database = data["db"]
        config: Config = data["config"]
        user: User | None = data.get("event_from_user")
        if user is not None:
            data["lang"] = await db.ensure_user(user.id, self._guess_lang(user, config))
            data["is_admin"] = user.id in config.admin_ids
        else:
            data["lang"] = config.default_lang
            data["is_admin"] = False
        return await handler(event, data)

    @staticmethod
    def _guess_lang(user: User, config: Config) -> str:
        code = (user.language_code or "").lower()
        if code.startswith("en"):
            return "en"
        if code.startswith(("ru", "uk", "be", "kk", "ky", "uz", "tg")):
            return "ru"
        return config.default_lang
