"""Deterministic answer to "what open houses are coming up for our
favorite places" - a real filtered/sorted endpoint, not a chat query."""

from datetime import date

from fastapi import APIRouter, HTTPException, Request

from ..deps import get_current_user, get_store
from ..feed_logic import FAVORITE_THRESHOLD, enrich

router = APIRouter(prefix="/api")


@router.get("/open-houses")
def open_houses(request: Request, favorites_only: bool = False):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401, "no identity")

    store = get_store()
    today = date.today().isoformat()
    listings = [
        listing
        for listing in store.all_listings(include_hidden=False)
        if listing["open_house_date"] and listing["open_house_date"] >= today
    ]
    listings = enrich(listings, store)

    if favorites_only:
        listings = [
            listing
            for listing in listings
            if listing["both_rating"] is not None and listing["both_rating"] >= FAVORITE_THRESHOLD
        ]

    listings.sort(key=lambda listing: listing["open_house_date"])
    return listings
