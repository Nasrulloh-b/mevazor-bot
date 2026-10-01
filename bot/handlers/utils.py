"""Small helpers shared by handlers."""

from __future__ import annotations

from contextlib import suppress

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message


async def show(target: Message | CallbackQuery, text: str, markup: InlineKeyboardMarkup | None = None) -> None:
    """Edits the inline message when the user pressed a button, otherwise sends a new message."""
    if isinstance(target, CallbackQuery):
        message = target.message
        if isinstance(message, Message):
            try:
                await message.edit_text(text, reply_markup=markup)
                return
            except TelegramBadRequest as err:
                if "message is not modified" in str(err):
                    return
                # The message may be too old to edit; fall back to a new one.
            await message.answer(text, reply_markup=markup)
        return
    await target.answer(text, reply_markup=markup)


async def answer_callback(callback: CallbackQuery, text: str | None = None, alert: bool = False) -> None:
    with suppress(TelegramBadRequest):
        await callback.answer(text, show_alert=alert)
