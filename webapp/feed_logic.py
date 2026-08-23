"""Shared listing enrichment/filter/sort logic for the JSON API - defined
once here rather than duplicated across route handlers."""

from datetime import datetime

from dateutil import parser as dateparser

from apt_agent.store import ListingStore

from .ranking import compute_rating_summary

FAVORITE_THRESHOLD = 4  # both_rating >= this counts as "a favorite" for open-houses


def enrich(listings: list[dict], store: ListingStore) -> list[dict]:
    for listing in listings:
        reactions = store.get_reactions_for_listing(listing["id"])
        listing["reactions"] = reactions
        listing.update(compute_rating_summary(reactions))
        listing["category_ratings"] = store.get_category_ratings_for_listing(listing["id"])
        listing["needs_backfill"] = not listing.get("photo_url") or not listing.get("address")
    return listings


def _available_on_or_before(raw_available_date: str | None, cutoff) -> bool:
    """Unknown/unparseable dates pass the filter rather than get excluded -
    same "don't filter on unknowns" pattern as apt_agent/filters.py."""
    if not raw_available_date:
        return True
    try:
        parsed = dateparser.parse(raw_available_date, fuzzy=True).date()
    except (ValueError, OverflowError, TypeError):
        return True
    return parsed <= cutoff


def filter_listings(
    listings: list[dict],
    *,
    neighborhood: str | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    available_before: str | None = None,
    needs_review: str | None = None,
    viewer: str | None = None,
    include_incomplete: bool = False,
) -> list[dict]:
    result = listings

    if not include_incomplete:
        result = [listing for listing in result if not listing.get("needs_backfill")]

    if neighborhood:
        result = [listing for listing in result if listing.get("neighborhood") == neighborhood]
    if price_min is not None:
        result = [
            listing
            for listing in result
            if listing.get("price") is None or listing["price"] >= price_min
        ]
    if price_max is not None:
        result = [
            listing
            for listing in result
            if listing.get("price") is None or listing["price"] <= price_max
        ]

    if available_before:
        try:
            cutoff = datetime.fromisoformat(available_before).date()
        except ValueError:
            cutoff = None
        if cutoff:
            result = [
                listing
                for listing in result
                if _available_on_or_before(listing.get("available_date"), cutoff)
            ]

    if needs_review == "me" and viewer:
        result = [listing for listing in result if listing["ratings"].get(viewer) is None]
    elif needs_review == "both":
        result = [
            listing
            for listing in result
            if listing["ratings"].get("elliott") is None
            and listing["ratings"].get("madison") is None
        ]

    return result


def _ranked(listings: list[dict], key) -> list[dict]:
    listings = sorted(listings, key=key, reverse=True)
    for rank, listing in enumerate(listings, start=1):
        listing["rank"] = rank
    return listings


def sort_listings(listings: list[dict], sort: str) -> list[dict]:
    if sort in ("leaderboard", "leaderboard_shared"):
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

    if sort in ("leaderboard_elliott", "leaderboard_madison"):
        user = sort.removeprefix("leaderboard_")
        rated = [listing for listing in listings if listing["ratings"].get(user) is not None]
        return _ranked(rated, lambda listing: listing["ratings"][user])

    key = "ai_score" if sort == "ai" else "both_rating"
    return sorted(listings, key=lambda listing: (listing[key] is None, -(listing[key] or 0)))
