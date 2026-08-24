"""Shared listing enrichment/filter/sort logic for the JSON API - defined
once here rather than duplicated across route handlers."""

import random

from apt_agent.store import ListingStore

from .ranking import KNOWN_USERS, compute_rating_summary


def match_status(swipes: dict[str, str]) -> str:
    """ "pending" until both known users have swiped; then "match" if both
    swiped right, else "miss" (either one or both swiped left)."""
    if len(swipes) < len(KNOWN_USERS):
        return "pending"
    return "match" if all(direction == "right" for direction in swipes.values()) else "miss"


def is_mismatch(swipes: dict[str, str]) -> bool:
    """True when both people have swiped and disagreed (one right, one
    left) - distinct from a "miss" where both passed. Both swipes are
    already final by the time this is ever true, so surfacing this after
    the fact carries no blind-judgment risk (unlike a "pending" listing -
    see waiting_on() below)."""
    return (
        len(swipes) == len(KNOWN_USERS) and "right" in swipes.values() and "left" in swipes.values()
    )


def waiting_on(swipes: dict[str, str], user: str) -> str | None:
    """If this user swiped right and is the only one who's swiped so far,
    returns the name of whoever they're waiting on - otherwise None.

    Deliberately per-viewer, not a shared/global flag: showing user A that
    user B already liked something A hasn't swiped on yet would leak B's
    opinion into A's still-blind decision - exactly what this project's
    swipe model is designed to avoid (see DECISIONS.md, "Dating-app swipe
    model"). This only ever tells a user about *their own* swipe waiting
    on a decision that hasn't happened yet, never the reverse."""
    if swipes.get(user) != "right" or len(swipes) != 1:
        return None
    others = [u for u in KNOWN_USERS if u != user]
    return others[0] if others else None


def enrich(listings: list[dict], store: ListingStore) -> list[dict]:
    for listing in listings:
        reactions = store.get_reactions_for_listing(listing["id"])
        listing["reactions"] = reactions
        listing.update(compute_rating_summary(reactions))
        listing["category_ratings"] = store.get_category_ratings_for_listing(listing["id"])
        listing["needs_backfill"] = not listing.get("photo_url") or not listing.get("address")
        listing["swipes"] = store.all_swipes_for_listing(listing["id"])
        listing["match_status"] = match_status(listing["swipes"])
        listing["mismatch"] = is_mismatch(listing["swipes"])
    return listings


def matches_for_user(listings: list[dict], user: str) -> list[dict]:
    """Real matches (both swiped right) plus, for this viewer only,
    listings they swiped right on that their partner hasn't decided on
    yet - tagged via `waiting_on` so the frontend can show "Matched" vs
    "Waiting on {partner}" as distinct groups. Never includes a listing
    the *other* person liked that this viewer hasn't swiped on - that
    stays hidden in their own swipe queue until they decide, same
    blind-judgment reasoning as waiting_on() above."""
    result = []
    for listing in listings:
        if listing["match_status"] == "match":
            listing["waiting_on"] = None
            result.append(listing)
        elif listing["match_status"] == "pending":
            partner = waiting_on(listing["swipes"], user)
            if partner:
                listing["waiting_on"] = partner
                result.append(listing)
    return result


def filter_listings(
    listings: list[dict],
    *,
    include_incomplete: bool = False,
    only_matched: bool = False,
) -> list[dict]:
    result = listings

    if not include_incomplete:
        result = [listing for listing in result if not listing.get("needs_backfill")]
    if only_matched:
        result = [listing for listing in result if listing.get("match_status") == "match"]

    return result


def swipe_queue_for_user(listings: list[dict], user: str) -> list[dict]:
    """This user's personal, independent swipe queue: listings they haven't
    swiped on yet (regardless of what the other person has done - swiping is
    blind), excluding incomplete listings (Needs Scan handles those) and
    anything already disqualified post-match. Highest AI match first, since
    that's the most useful default order for a one-at-a-time queue with no
    filter UI of its own.

    Shuffled before that sort - most listings don't have an ai_score (AI
    scoring is deliberately deprioritized right now), so without shuffling
    first, Python's stable sort would leave every unscored listing in DB
    insertion order, which clusters by neighborhood (scans import one
    neighborhood at a time) - the queue would show one neighborhood after
    another instead of a mixed order. Shuffling first randomizes the order
    within each (scored vs unscored) group; the sort then still puts any
    real AI scores first, highest to lowest."""
    undecided = [
        listing
        for listing in listings
        if user not in listing.get("swipes", {}) and not listing.get("needs_backfill")
    ]
    random.shuffle(undecided)
    return sorted(
        undecided, key=lambda listing: (listing["ai_score"] is None, -(listing["ai_score"] or 0))
    )


def _ranked(listings: list[dict], key) -> list[dict]:
    listings = sorted(listings, key=key, reverse=True)
    for rank, listing in enumerate(listings, start=1):
        listing["rank"] = rank
    return listings


def sort_listings(listings: list[dict], sort: str) -> list[dict]:
    """Only ever called with a "leaderboard_*" sort - the Leaderboard's four
    tabs (shared/ai/elliott/madison) are the only remaining caller."""
    if sort == "leaderboard_shared":
        both_rated = [
            listing
            for listing in listings
            if listing["both_rating"] is not None and listing["label"] is None
        ]
        return _ranked(
            both_rated, lambda listing: (listing["both_rating"] or 0, listing["ai_score"] or 0)
        )

    if sort == "leaderboard_ai":
        scored = [listing for listing in listings if listing.get("ai_score") is not None]
        return _ranked(scored, lambda listing: listing["ai_score"])

    user = sort.removeprefix("leaderboard_")
    if user in KNOWN_USERS:
        rated = [listing for listing in listings if listing["ratings"].get(user) is not None]
        return _ranked(rated, lambda listing: listing["ratings"][user])

    raise ValueError(f"unknown sort {sort!r}")
