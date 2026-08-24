---
type: entity
source_files: [webapp/scoring.py, webapp/rescore.py, taste_profile.md]
status: active
verified: 2026-08-24
tags: [ai-scoring, claude-vision, taste-profile, fallback-path]
---

# AI scoring fallback and taste profile

## Purpose

The secondary/fallback AI taste-match scoring path: given a listing's photo URL and the written `taste_profile.md`, calls the Anthropic API directly (Claude vision) to produce a 0-100 match score and one-sentence reasoning, plus `rescore.py`, the manual command that backfills this for listings missing a score or scored against a stale profile version. This is explicitly *not* the primary scoring mechanism - see Notes below.

## Key exports

- `score_listing(listing, taste_profile, api_key)` (`scoring.py`) - fetches `listing["photo_url"]`, base64-encodes it, sends it plus the taste profile text to Claude (`model = "claude-opus-5"`, `effort: "low"`), parses a JSON `{score, reasoning}` response; returns `(int, str)` on success, `(None, None)` on any failure
- `_extract_json(text)` - tolerant parsing: tries a direct `json.loads`, falls back to a regex-extracted `{...}` substring
- `main()` (`rescore.py`, run as `python -m webapp.rescore` / `poe rescore`) - finds every listing where `ai_score is None` or `ai_profile_version` doesn't match the configured `profile_version`, scores each via `score_listing`, writes results back with `store.set_ai_score`
- `taste_profile.md` (repo root) - the reference document scored against; **preliminary draft**, 3 liked StreetEasy examples only, no disliked examples yet

## Depends on / used by

- [store](../entities/store.md)
- [shared-config](../entities/shared-config.md)
- [browser-import](../entities/browser-import.md)

## Notes & gotchas

- **This is the secondary/fallback scoring path, not the primary one.** The primary path is an interactive Claude Code browser-scan session judging a page screenshot directly against `taste_profile.md`, with no API call at all - see `browser-import.md` / `ai-taste-scoring`. `webapp/scoring.py` exists only for listings that arrive without a pre-computed score, e.g. the Zillow email-import path, which deliberately leaves `ai_score` `NULL` since there's no live session watching an unattended cron run.
- **Never actually run against the real Anthropic API as of this writing.** It was built and tested with no `ANTHROPIC_API_KEY` available - only the graceful-degradation paths are proven (missing photo, non-200 photo fetch, non-image content-type, `requests.RequestException`, `anthropic.APIError`/`APIConnectionError`, a `"refusal"` `stop_reason`, unparseable or out-of-range JSON). The actual live vision call has not been verified end-to-end.
- Every failure mode returns `(None, None)` and never raises, matching `apt_agent/filters.py`'s "unknown field, don't block on it" pattern - scoring must never block or fail ingestion.
- `rescore.py` is a deliberately manual, one-off command, not scheduled - "not worth automating" at this project's scale.
- `profile_version` (from `config.yaml`'s `scoring:` section) is compared per-listing against `ai_profile_version`, so revising `taste_profile.md` and bumping the version number automatically marks every previously-scored listing stale for re-scoring.
- `taste_profile.md` is intentionally rough: only 3 liked listings (256 Cumberland St #4, 75 South 3rd St #1, 163 Warren St #1), no disliked contrast set. What it can actually support: good light/windows, "real character" via either modern renovation or authentic prewar detail, private outdoor space as a strong plus but not required, and finish level as explicitly *not* the deciding factor. It explicitly cannot yet support "score X down" reasoning - absence of a positive signal (e.g. no outdoor space) must not be read as a negative one.

## Related concepts

- [ai-taste-scoring](../concepts/ai-taste-scoring.md)
- [zillow-ingestion-evolution](../concepts/zillow-ingestion-evolution.md)
