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

AI taste-match scoring has two independent paths, either or neither of
which may be in play for a given import:

1. **Pre-computed, per-listing.** If a raw listing dict already has
   `ai_score`/`ai_reasoning` set (e.g. because a Claude Code session
   doing an interactive browser scan looked at the photo itself and
   judged it against the taste profile, no API call needed - that's
   the primary path now), those values are saved as-is.
2. **score_fn fallback.** For listings with no pre-computed score,
   `main()` optionally wires up an Anthropic-API-key-based scorer (see
   webapp/scoring.py) if `taste_profile.md` + `ANTHROPIC_API_KEY` are
   both present. This is a secondary/optional path, not required -
   ingestion works identically with neither path configured.
"""

import json
import os
import sys

from .filters import passes_filters
from .main import load_config
from .store import ListingStore


def import_listings(listings: list[dict], cfg: dict, store: ListingStore, score_fn=None) -> dict:
    """score_fn, if given: Callable[[dict], tuple[int | None, str | None]] -
    a fallback scorer called only for listings that don't already carry
    a pre-computed ai_score/ai_reasoning (see module docstring). Any
    failure inside score_fn should already be caught there and returned
    as (None, None) - import_listings doesn't handle scoring exceptions
    itself, since a scoring bug should never be able to break ingestion."""
    new_count = 0
    already_seen_count = 0
    would_alert_count = 0
    scored_count = 0

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
            "open_house_raw": raw.get("open_house_raw"),
            "open_house_date": raw.get("open_house_date"),
            "available_date": raw.get("available_date"),
            "source": raw.get("source", "streeteasy-browser-scan"),
        }

        ok, _reason = passes_filters(listing, cfg)
        if ok and store.already_alerted_for_address(listing.get("address")):
            ok = False

        listing_id = store.save(listing, alerted=False)
        new_count += 1
        if ok:
            would_alert_count += 1

        score, reasoning = raw.get("ai_score"), raw.get("ai_reasoning")
        if score is None and score_fn is not None:
            score, reasoning = score_fn(listing)
        if score is not None:
            store.set_ai_score(listing_id, score, reasoning, cfg["scoring"]["profile_version"])
            scored_count += 1

    return {
        "new": new_count,
        "already_seen": already_seen_count,
        "would_alert": would_alert_count,
        "scored": scored_count,
    }


def _build_score_fn(cfg: dict):
    """Returns a score_fn if a taste profile + API key are both
    available, else None - the graceful-degradation switch described
    in the module docstring."""
    scoring_cfg = cfg.get("scoring") or {}
    profile_path = scoring_cfg.get("profile_path")
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not profile_path or not os.path.exists(profile_path) or not api_key:
        return None

    with open(profile_path) as f:
        taste_profile = f.read()

    from webapp.scoring import score_listing

    def score_fn(listing: dict):
        return score_listing(listing, taste_profile, api_key)

    return score_fn


def main():
    path = sys.argv[1]
    with open(path) as f:
        listings = json.load(f)

    cfg = load_config()
    store = ListingStore(cfg["storage"]["db_path"])
    score_fn = _build_score_fn(cfg)
    if score_fn is None:
        print(
            "[info] no ANTHROPIC_API_KEY fallback scorer configured - "
            "relying on pre-computed ai_score fields only, if present"
        )

    stats = import_listings(listings, cfg, store, score_fn=score_fn)
    print(f"Imported: {stats}")


if __name__ == "__main__":
    main()
