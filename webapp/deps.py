"""Shared dependencies for the JSON API: the one ListingStore instance
and current-user resolution from an unsigned cookie. No passwords/signed
sessions - see plan doc for why that's the right call for exactly 2
known users."""

from fastapi import Request

from apt_agent.store import ListingStore

from .config import load_webapp_config
from .ranking import KNOWN_USERS

_store: ListingStore | None = None


def get_store() -> ListingStore:
    global _store
    if _store is None:
        cfg = load_webapp_config()
        _store = ListingStore(cfg["storage"]["db_path"])
    return _store


def get_current_user(request: Request) -> str | None:
    user = request.cookies.get("user")
    return user if user in KNOWN_USERS else None
