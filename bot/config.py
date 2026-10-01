"""Settings read from environment variables (or a .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # python-dotenv is optional; plain environment variables work too.
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def _parse_ids(raw: str) -> frozenset[int]:
    ids = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            ids.add(int(part))
    return frozenset(ids)


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: frozenset[int] = field(default_factory=frozenset)
    db_path: Path = Path("data/mevazor.db")
    default_lang: str = "ru"
    shop_name: str = "Mevazor"
    support_phone: str = "+992 92 000 0000"

    @classmethod
    def from_env(cls) -> "Config":
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise SystemExit("BOT_TOKEN is not set. Copy .env.example to .env and paste the token from @BotFather.")
        return cls(
            bot_token=token,
            admin_ids=_parse_ids(os.getenv("ADMIN_IDS", "")),
            db_path=Path(os.getenv("DB_PATH", "data/mevazor.db")),
            default_lang=os.getenv("DEFAULT_LANG", "ru") if os.getenv("DEFAULT_LANG") in ("ru", "en") else "ru",
            shop_name=os.getenv("SHOP_NAME", "Mevazor"),
            support_phone=os.getenv("SUPPORT_PHONE", "+992 92 000 0000"),
        )
