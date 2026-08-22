"""The main shared feed: sortable by AI score or by our own ratings, with
a non-destructive threshold filter. Hidden listings never appear here -
see routes/hidden.py for reviewing/undoing those."""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from ..deps import get_current_user, get_store, templates
from ..ranking import compute_rating_summary

router = APIRouter()


def _enrich(listing: dict, store) -> dict:
    reactions = store.get_reactions_for_listing(listing["id"])
    listing["reactions"] = reactions
    listing.update(compute_rating_summary(reactions))
    return listing


@router.get("/")
def feed(request: Request, sort: str = "ai", min_score: int | None = None):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/whoami")

    store = get_store()
    listings = [_enrich(l, store) for l in store.all_listings(include_hidden=False)]

    sort_key = "ai_score" if sort == "ai" else "both_rating"
    listings.sort(key=lambda l: (l[sort_key] is None, -(l[sort_key] or 0)))

    if min_score is not None:
        listings = [l for l in listings if l[sort_key] is not None and l[sort_key] >= min_score]

    return templates.TemplateResponse(
        request,
        "feed.html",
        {"listings": listings, "user": user, "sort": sort, "min_score": min_score},
    )
