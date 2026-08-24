---
type: entity
source_files: [apt_agent/browser_import.py]
status: active
verified: 2026-08-24
tags: [ingestion, browser-scan, persistence, ai-scoring]
---

# Browser-scan import

## Purpose

The shared persistence step both browser-scan skills (StreetEasy and Zillow) run at the end of a scan session: takes the JSON list of raw listing dicts produced by a scan, dedups them against everything already in `listings.db`, applies today's hard filters (for reporting only), and saves AI taste-match scores. Invoked as `python -m apt_agent.browser_import <path-to-json-file>`. Deliberately never sends alert emails - importing a bulk census of what's currently on the market is a different event from "something new just appeared," and alerting on all of it at once would just be inbox spam.

## Key exports

- `import_listings(listings, cfg, store, score_fn=None) -> dict` - the core dedup/save/score loop. For each raw listing: if its URL is already in the store, calls `store.backfill_listing()` to fill in anything missing (e.g. photo/address) rather than skipping outright; otherwise saves it as new (`alerted=False`), checks it against hard filters + address-dedup for the `would_alert` stat (never actually alerts), and resolves an AI score - preferring a pre-computed `ai_score`/`ai_reasoning` already on the raw dict (set by the scanning session's own vision judgment), falling back to `score_fn` only if neither is present. Returns `{new, already_seen, backfilled, would_alert, scored}` counts.
- `_build_score_fn(cfg)` - returns an Anthropic-API-key-based fallback scorer (via `webapp/scoring.py`) only if `taste_profile.md` exists AND `ANTHROPIC_API_KEY` is set; otherwise returns `None`, and ingestion proceeds identically without it.
- `main()` - CLI entry point: loads config, opens the `ListingStore`, builds the optional fallback `score_fn`, runs `import_listings()`, prints the stats dict.

## Depends on / used by

- [browser-scan-streeteasy.md](browser-scan-streeteasy.md)
- [browser-scan-zillow.md](browser-scan-zillow.md)
- [store.md](store.md)
- [shared-config.md](shared-config.md)
- [scoring.md](scoring.md)

## Notes & gotchas

- **AI scoring has two independent, non-exclusive paths**, and this module is where they converge: (1) a pre-computed `ai_score`/`ai_reasoning` on the raw listing dict - set when a Claude Code session doing an interactive browser scan already has vision and judges a listing's photo against `taste_profile.md` directly, no API call needed (the primary path for both scan skills); (2) the `score_fn` fallback, wired up only when a taste profile file and an `ANTHROPIC_API_KEY` both exist. Either, neither, or (per-listing) exactly one may apply for a given import - a listing with a pre-computed score never invokes `score_fn` even if one is configured.
- `score_fn`'s failure modes (no photo, fetch failure, API error, bad response) are expected to already be caught inside `score_fn` itself and returned as `(None, None)` - `import_listings()` does not catch scoring exceptions, on the reasoning that a scoring bug should never be able to break ingestion.
- Rescanning a listing already in the store is treated as an opportunity to backfill missing fields (`store.backfill_listing()`), not a no-op - this is how the webapp's "Needs Scan" queue (listings missing photo/address) actually gets resolved when a session revisits those URLs.
- `source` on the imported listing dict defaults to `"streeteasy-browser-scan"` if the raw dict doesn't set one, but both scan skills always set it explicitly (`"streeteasy-browser-scan"` vs. `"zillow-browser-scan"`) to distinguish origin in `listings.source`, separate again from the automated `zillow_email_import.py` path.
- This is the third of three consumers of `ListingStore` alongside the email pipeline's `main.py` and `webapp/` - all writing to the one shared `listings.db`, which is why dedup here (`already_seen`) is what makes re-running a scan session safe.

## Related concepts

- [two-ingestion-paths.md](../concepts/two-ingestion-paths.md)
- [ai-taste-scoring.md](../concepts/ai-taste-scoring.md)
- [zillow-ingestion-evolution.md](../concepts/zillow-ingestion-evolution.md)
