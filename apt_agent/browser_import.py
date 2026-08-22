"""
Imports listings extracted during an interactive browser session (see
DECISIONS.md - authenticated-browser census, not the email pipeline)
into the same listings.db the automated pipeline uses, so a manual
"map what's currently on the market" scan shares dedup with real
alerts, and re-running a scan (even with broadened filters) never
re-processes a listing we've already recorded.

    python -m apt_agent.browser_import <path-to-json-file>

Expects a JSON list of dicts with: url, address, neighborhood, price,
beds, baths, sqft, listing_agent, photo (the shape the browser-side
extraction script produces).

Deliberately never sends alert emails - a bulk census of what's
already on the market is not the same event as "something new just
appeared," and alerting on all of it at once would just be inbox
spam. `would_alert` in the returned stats tells you how many of the
newly-imported listings pass today's hard filters, without emailing
about any of them.
"""
import json
import sys

from .main import load_config
from .filters import passes_filters
from .store import ListingStore


def import_listings(listings: list[dict], cfg: dict, store: ListingStore) -> dict:
    new_count = 0
    already_seen_count = 0
    would_alert_count = 0

    for raw in listings:
        if store.already_seen(raw["url"]):
            already_seen_count += 1
            continue

        listing = {
            "url": raw["url"],
            "address": raw.get("address"),
            "neighborhood": raw.get("neighborhood"),
            "price": raw.get("price"),
            "beds": raw.get("beds"),
            "baths": raw.get("baths"),
            "sqft": raw.get("sqft"),
            "listing_agent": raw.get("listing_agent"),
            "photo_url": raw.get("photo"),
            "available_date": raw.get("available_date"),
            "source": raw.get("source", "streeteasy-browser-scan"),
        }

        ok, _reason = passes_filters(listing, cfg)
        if ok and store.already_alerted_for_address(listing.get("address")):
            ok = False

        store.save(listing, alerted=False)
        new_count += 1
        if ok:
            would_alert_count += 1

    return {
        "new": new_count,
        "already_seen": already_seen_count,
        "would_alert": would_alert_count,
    }


def main():
    path = sys.argv[1]
    with open(path) as f:
        listings = json.load(f)

    cfg = load_config()
    store = ListingStore(cfg["storage"]["db_path"])
    stats = import_listings(listings, cfg, store)
    print(f"Imported: {stats}")


if __name__ == "__main__":
    main()
