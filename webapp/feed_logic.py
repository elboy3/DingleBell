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
) -> list[dict]:
    result = listings

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


def sort_listings(listings: list[dict], sort: str) -> list[dict]:
    if sort == "leaderboard":
        both_rated = [
            listing
            for listing in listings
            if listing["both_rating"] is not None and listing["label"] is None
        ]
        both_rated.sort(
            key=lambda listing: (-(listing["both_rating"] or 0), -(listing["ai_score"] or 0))
        )
        for rank, listing in enumerate(both_rated, start=1):
            listing["rank"] = rank
        return both_rated

    key = "ai_score" if sort == "ai" else "both_rating"
    return sorted(listings, key=lambda listing: (listing[key] is None, -(listing[key] or 0)))
