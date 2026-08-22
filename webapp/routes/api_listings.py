"""The main JSON API: feed (sort/filter), listing detail, and the
rating/comment/hidden actions."""

from fastapi import APIRouter, Body, HTTPException, Request

from ..deps import get_current_user, get_store
from ..feed_logic import enrich, filter_listings, sort_listings

router = APIRouter(prefix="/api")


def _require_user(request: Request) -> str:
    user = get_current_user(request)
    if not user:
        raise HTTPException(401, "no identity - POST /api/whoami first")
    return user


def _parse_int(raw: str | None) -> int | None:
    """Query params arrive as strings - an empty string (a cleared HTML
    number input) is "unset", not a parse error, so this needs to handle
    that before FastAPI's automatic int coercion ever sees it."""
    if raw is None or raw == "":
        return None
    return int(raw)


@router.get("/listings")
def list_listings(
    request: Request,
    sort: str = "ai",
    min_score: str | None = None,
    neighborhood: str | None = None,
    price_min: str | None = None,
    price_max: str | None = None,
    available_before: str | None = None,
    needs_review: str | None = None,
):
    user = _require_user(request)
    store = get_store()
    listings = enrich(store.all_listings(include_hidden=False), store)
    listings = filter_listings(
        listings,
        neighborhood=neighborhood,
        price_min=_parse_int(price_min),
        price_max=_parse_int(price_max),
        available_before=available_before,
        needs_review=needs_review,
        viewer=user,
    )
    listings = sort_listings(listings, sort)

    min_score_val = _parse_int(min_score)
    if min_score_val is not None and sort != "leaderboard":
        key = "ai_score" if sort == "ai" else "both_rating"
        listings = [
            listing
            for listing in listings
            if listing.get(key) is not None and listing[key] >= min_score_val
        ]

    return listings


@router.get("/listings/{listing_id}")
def get_listing(request: Request, listing_id: int):
    _require_user(request)
    store = get_store()
    matches = [
        listing
        for listing in store.all_listings(include_hidden=True)
        if listing["id"] == listing_id
    ]
    if not matches:
        raise HTTPException(404, "not found")
    return enrich(matches, store)[0]


@router.post("/listings/{listing_id}/rating")
def set_rating(request: Request, listing_id: int, rating: int = Body(..., embed=True)):
    user = _require_user(request)
    get_store().set_rating(listing_id, user, rating)
    return {"ok": True}


@router.post("/listings/{listing_id}/comment")
def set_comment(request: Request, listing_id: int, comment: str = Body(..., embed=True)):
    user = _require_user(request)
    get_store().set_comment(listing_id, user, comment)
    return {"ok": True}


@router.post("/listings/{listing_id}/hidden")
def set_hidden(request: Request, listing_id: int, hidden: bool = Body(..., embed=True)):
    user = _require_user(request)
    get_store().set_hidden(listing_id, hidden, user)
    return {"ok": True}


@router.get("/hidden")
def hidden_listings(request: Request):
    _require_user(request)
    store = get_store()
    listings = [listing for listing in store.all_listings(include_hidden=True) if listing["hidden"]]
    return enrich(listings, store)


@router.get("/neighborhoods")
def neighborhoods(request: Request):
    _require_user(request)
    store = get_store()
    listings = store.all_listings(include_hidden=True)
    return sorted({listing["neighborhood"] for listing in listings if listing.get("neighborhood")})
