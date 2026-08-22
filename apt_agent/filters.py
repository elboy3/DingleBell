"""Hard filters: price, beds/baths, move-in window."""

from dateutil import parser as dateparser


def passes_filters(listing: dict, cfg: dict) -> tuple[bool, str]:
    """Returns (passes, reason_if_not)."""
    search_cfg = cfg["search"]

    price = listing.get("price")
    if price is not None:
        if price < search_cfg["price_min"] or price > search_cfg["price_max"]:
            return (
                False,
                f"price {price} outside [{search_cfg['price_min']}, {search_cfg['price_max']}]",
            )

    beds = listing.get("beds")
    if beds is not None and beds < search_cfg["beds_min"]:
        return False, f"beds {beds} below min {search_cfg['beds_min']}"

    baths = listing.get("baths")
    if baths is not None and baths < search_cfg["baths_min"]:
        return False, f"baths {baths} below min {search_cfg['baths_min']}"

    avail_ok, avail_reason = _check_availability(listing.get("available_date"), search_cfg)
    if not avail_ok:
        return False, avail_reason

    return True, ""


def _check_availability(avail_str: str | None, search_cfg: dict) -> tuple[bool, str]:
    if not avail_str:
        # Unknown availability - don't filter it out, let a human eyeball it.
        return True, ""

    lowered = avail_str.lower()
    if "now" in lowered or "immediately" in lowered:
        return True, ""

    earliest = dateparser.parse(search_cfg["earliest_move_in"]).date()
    latest = dateparser.parse(search_cfg["latest_move_in"]).date()

    try:
        parsed_date = dateparser.parse(avail_str, fuzzy=True).date()
    except (ValueError, OverflowError):
        # Couldn't parse a date out of it - don't filter, flag for review instead.
        return True, ""

    if parsed_date < earliest or parsed_date > latest:
        return False, f"available {parsed_date} outside window [{earliest}, {latest}]"

    return True, ""
