"""Shared listing enrichment/filter/sort logic for the JSON API - defined
once here rather than duplicated across route handlers."""

from apt_agent.store import ListingStore

from .ranking import KNOWN_USERS, compute_rating_summary


def match_status(swipes: dict[str, str]) -> str:
    """ "pending" until both known users have swiped; then "match" if both
    swiped right, else "miss" (either one or both swiped left)."""
    if len(swipes) < len(KNOWN_USERS):
        return "pending"
    return "match" if all(direction == "right" for direction in swipes.values()) else "miss"


def enrich(listings: list[dict], store: ListingStore) -> list[dict]:
    for listing in listings:
        reactions = store.get_reactions_for_listing(listing["id"])
        listing["reactions"] = reactions
        listing.update(compute_rating_summary(reactions))
        listing["category_ratings"] = store.get_category_ratings_for_listing(listing["id"])
        listing["needs_backfill"] = not listing.get("photo_url") or not listing.get("address")
        listing["swipes"] = store.all_swipes_for_listing(listing["id"])
        listing["match_status"] = match_status(listing["swipes"])
    return listings


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
    filter UI of its own."""
    undecided = [
        listing
        for listing in listings
        if user not in listing.get("swipes", {}) and not listing.get("needs_backfill")
    ]
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
