"""FastAPI entry point.

    uvicorn webapp.app:app --reload   # local dev
    uvicorn webapp.app:app --host 0.0.0.0 --port 8080   # production (see Dockerfile)
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routes import feed, hidden, identity, listing, open_houses

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Apartment Hunt")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(identity.router)
app.include_router(feed.router)
app.include_router(listing.router)
app.include_router(hidden.router)
app.include_router(open_houses.router)
