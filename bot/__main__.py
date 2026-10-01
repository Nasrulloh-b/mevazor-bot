"""Entry point: `python -m bot`."""

from __future__ import annotations

import asyncio
import logging

from .app import create_bot, create_dispatcher, set_commands
from .config import Config
from .db import Database


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = Config.from_env()
    db = Database(config.db_path)
    await db.connect()
    bot = create_bot(config)
    dp = create_dispatcher(db, config)
    try:
        await set_commands(bot, config)
        me = await bot.get_me()
        logging.info("Bot @%s is running. Admins: %s", me.username, ", ".join(map(str, config.admin_ids)) or "none")
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
