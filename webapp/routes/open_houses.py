"""Deterministic answer to "what open houses are coming up for our
favorite places" - a real filtered/sorted view, not a chat query."""

from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from ..deps import get_current_user, get_store, templates
from ..ranking import compute_rating_summary

router = APIRouter()

FAVORITE_THRESHOLD = 4  # both_rating >= this counts as "a favorite" - adjust to taste


@router.get("/open-houses")
def open_houses(request: Request, favorites_only: bool = False):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/whoami")

    store = get_store()
    today = date.today().isoformat()
    listings = []
    for listing in store.all_listings(include_hidden=False):
        if not listing["open_house_date"] or listing["open_house_date"] < today:
            continue
        reactions = store.get_reactions_for_listing(listing["id"])
        listing["reactions"] = reactions
        listing.update(compute_rating_summary(reactions))
        if favorites_only and (
            listing["both_rating"] is None or listing["both_rating"] < FAVORITE_THRESHOLD
        ):
            continue
        listings.append(listing)

    listings.sort(key=lambda listing: listing["open_house_date"])

    return templates.TemplateResponse(
        request,
        "open_houses.html",
        {"listings": listings, "user": user, "favorites_only": favorites_only},
    )
