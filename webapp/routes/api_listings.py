"""The main JSON API: swipe queue, Matches, the Leaderboard,
listing detail, and the comment/hidden/swipe/category-rating actions."""

from fastapi import APIRouter, Body, HTTPException, Request

from apt_agent.store import ListingStore

from ..categories import CATEGORY_KEYS
from ..deps import get_current_user, get_store
from ..feed_logic import enrich, filter_listings, sort_listings, swipe_queue_for_user

router = APIRouter(prefix="/api")


def _require_user(request: Request) -> str:
    user = get_current_user(request)
    if not user:
        raise HTTPException(401, "no identity - POST /api/whoami first")
    return user


def _enriched_listings(store: ListingStore, *, include_hidden: bool) -> list[dict]:
    return enrich(store.all_listings(include_hidden=include_hidden), store)


@router.get("/listings")
def list_listings(request: Request, sort: str = "leaderboard_shared", only_matched: bool = False):
    """Only used by the Leaderboard's four tabs now - filtering/sorting for
    the old grid-browse Feed page was removed along with that page."""
    _require_user(request)
    store = get_store()
    listings = _enriched_listings(store, include_hidden=False)
    listings = filter_listings(listings, only_matched=only_matched)
    return sort_listings(listings, sort)


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
    # single number everything else already sorts/filters on. Round half
    # up (not Python's round-half-to-even default) so e.g. a 2-and-3
    # average of 2.5 becomes 3, matching what a user would expect.
    user_categories = store.get_category_ratings_for_listing(listing_id).get(user, {})
    if user_categories:
        avg_rating = int(sum(user_categories.values()) / len(user_categories) + 0.5)
        store.set_rating(listing_id, user, avg_rating)
    return {"ok": True}


@router.get("/swipe-queue")
def swipe_queue_listings(request: Request):
    """This user's personal one-at-a-time queue: listings they haven't
    swiped on yet, highest AI match first. Independent of what the other
    person has done - swiping is blind."""
    user = _require_user(request)
    store = get_store()
    listings = _enriched_listings(store, include_hidden=False)
    return swipe_queue_for_user(listings, user)


@router.get("/matches")
def matches_listings(request: Request):
    """Matches - both people swiped right. Where the deeper category-rating/
    comment review happens, via each one's detail page."""
    _require_user(request)
    store = get_store()
    listings = _enriched_listings(store, include_hidden=False)
    return [listing for listing in listings if listing["match_status"] == "match"]


@router.get("/passed")
def passed_listings(request: Request):
    """Full-transparency audit trail: every listing with at least one "left"
    swipe recorded so far - covers both-passed, a mismatch (one liked, one
    passed), and a partial pass (one passed, the other hasn't swiped yet)."""
    _require_user(request)
    store = get_store()
    listings = _enriched_listings(store, include_hidden=True)
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
    """Listings missing a photo or address - shown separately from the
    swipe queue so incomplete rows don't clutter review, and used as the
    backfill queue for the next browser scan."""
    _require_user(request)
    store = get_store()
    listings = _enriched_listings(store, include_hidden=True)
    return [listing for listing in listings if listing["needs_backfill"]]
