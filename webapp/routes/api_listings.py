"""The main JSON API: feed (sort/filter), listing detail, and the
rating/comment/hidden actions."""

from fastapi import APIRouter, Body, HTTPException, Request

from ..categories import CATEGORY_KEYS
from ..deps import get_current_user, get_store
from ..feed_logic import enrich, filter_listings, sort_listings, swipe_queue_for_user

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
    only_matched: bool = False,
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
        only_matched=only_matched,
    )
    listings = sort_listings(listings, sort)

    min_score_val = _parse_int(min_score)
    if min_score_val is not None and not sort.startswith("leaderboard"):
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
def set_hidden(
    request: Request,
    listing_id: int,
    hidden: bool = Body(..., embed=True),
    reason: str = Body("off_market", embed=True),
):
    """Leaderboard-only: disqualifying a matched listing (e.g. it went off
    the market). Reversible via the Passed view's undo. Not used for
    pre-match rejection - that's POST /listings/{id}/swipe instead."""
    user = _require_user(request)
    get_store().set_hidden(listing_id, hidden, user, reason=reason)
    return {"ok": True}


@router.post("/listings/{listing_id}/swipe")
def swipe(request: Request, listing_id: int, direction: str = Body(..., embed=True)):
    """Personal and permanent - this user will never see this listing in
    their own swipe queue again, regardless of direction."""
    user = _require_user(request)
    if direction not in ("left", "right"):
        raise HTTPException(400, f"direction must be 'left' or 'right', got {direction!r}")
    get_store().record_swipe(listing_id, user, direction)
    return {"ok": True}


@router.post("/listings/{listing_id}/category-rating")
def set_category_rating(
    request: Request,
    listing_id: int,
    category: str = Body(...),
    score: int = Body(...),
):
    user = _require_user(request)
    if category not in CATEGORY_KEYS:
        raise HTTPException(400, f"unknown category {category!r}")
    if not 1 <= score <= 5:
        raise HTTPException(400, "score must be 1-5")
    store = get_store()
    store.set_category_rating(listing_id, user, category, score)

    # The overall star rating (used for sorting/leaderboards) follows the
    # average of this user's category scores once they've rated any -
    # category ratings are the detailed "why", the star rating stays the
    # single number everything else already sorts/filters on.
    user_categories = store.get_category_ratings_for_listing(listing_id).get(user, {})
    if user_categories:
        avg_rating = round(sum(user_categories.values()) / len(user_categories))
        store.set_rating(listing_id, user, avg_rating)
    return {"ok": True}


@router.get("/swipe-queue")
def swipe_queue_listings(request: Request):
    """This user's personal one-at-a-time queue: listings they haven't
    swiped on yet, highest AI match first. Independent of what the other
    person has done - swiping is blind."""
    user = _require_user(request)
    store = get_store()
    listings = enrich(store.all_listings(include_hidden=False), store)
    return swipe_queue_for_user(listings, user)


@router.get("/inbox")
def inbox_listings(request: Request):
    """Matches - both people swiped right. Where the deeper category-rating/
    comment review happens, via each one's detail page."""
    _require_user(request)
    store = get_store()
    listings = enrich(store.all_listings(include_hidden=False), store)
    return [listing for listing in listings if listing["match_status"] == "match"]


@router.get("/passed")
def passed_listings(request: Request):
    """Full-transparency audit trail: every listing with at least one "left"
    swipe recorded so far - covers both-passed, a mismatch (one liked, one
    passed), and a partial pass (one passed, the other hasn't swiped yet)."""
    _require_user(request)
    store = get_store()
    listings = enrich(store.all_listings(include_hidden=True), store)
    return [
        listing
        for listing in listings
        if "left" in listing["swipes"].values() and not listing["hidden"]
    ]


@router.get("/off-market")
def off_market_listings(request: Request):
    """Matches later disqualified from the Leaderboard (e.g. went off the
    market) - reversible, unlike a personal swipe."""
    _require_user(request)
    store = get_store()
    listings = [
        listing
        for listing in store.all_listings(include_hidden=True)
        if listing["hidden"] and listing["hidden_reason"] == "off_market"
    ]
    return enrich(listings, store)


@router.get("/needs-scan")
def needs_scan_listings(request: Request):
    """Listings missing a photo or address - shown separately from the main
    feed so incomplete rows don't clutter review, and used as the backfill
    queue for the next browser scan."""
    _require_user(request)
    store = get_store()
    listings = enrich(store.all_listings(include_hidden=True), store)
    return [listing for listing in listings if listing["needs_backfill"]]
