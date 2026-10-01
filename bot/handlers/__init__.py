"""Collects all routers in the order they should be tried."""

from aiogram import Router

from . import admin, cart, catalog, checkout, common


def build_router() -> Router:
    """Call once per process: aiogram routers can belong to only one parent."""
    root = Router(name="root")
    root.include_routers(
        common.menu,  # menu buttons and commands win over any half-finished conversation
        admin.router,
        checkout.router,
        cart.router,
        catalog.router,
        common.fallback,  # must stay last
    )
    return root
