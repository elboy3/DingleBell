"""Shared dependencies for webapp routes: the one ListingStore instance,
current-user resolution from an unsigned cookie, and the Jinja2 templates
environment. No passwords/signed sessions - see plan doc for why that's
the right call for exactly 2 known users."""
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from apt_agent.store import ListingStore

from .config import load_webapp_config

BASE_DIR = Path(__file__).resolve().parent
KNOWN_USERS = ["elliott", "madison"]

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

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
