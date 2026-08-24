---
type: concept
status: active
verified: 2026-08-24
tags: [ai-scoring, claude-vision, taste-profile]
---

# AI taste-match scoring

## Summary

Every listing can carry an `ai_score`/`ai_reasoning` judging how well it matches the couple's taste, computed one of two ways: primarily by the interactive Claude Code session itself, during a browser scan, looking directly at a page screenshot - no API call needed; secondarily, only when no pre-computed score exists, by an Anthropic-API-key-based fallback in `webapp/scoring.py`. The reference document both paths score against, `taste_profile.md`, is a preliminary draft (3 liked examples, no disliked ones yet).

## Details

**Primary path - the scanning session's own vision.** Both browser-scan skills ([browser-scan-streeteasy](../entities/browser-scan-streeteasy.md), [browser-scan-zillow](../entities/browser-scan-zillow.md)) score each new listing directly during the scan: the Claude Code session already has vision and is already looking at the results page, so it judges each listing's photo (via a page screenshot) against `taste_profile.md` and sets `ai_score`/`ai_reasoning` in the JSON handed to [browser-import](../entities/browser-import.md). This was a deliberate simplification - the original design called the Anthropic API from inside `browser_import.py`, but the user pointed out that a separate API-key-based call was redundant when the scanning session could just judge the photo itself. This removed an entire external credential from the critical path.

**Secondary/fallback path - `webapp/scoring.py` + `rescore.py`.** [scoring](../entities/scoring.md) exists only for listings that arrive without a pre-computed score - specifically [zillow-email-import](../entities/zillow-email-import.md)'s unattended cron path, which leaves `ai_score` `NULL` because there's no live session watching an automated run to judge a photo. `score_listing()` fetches the listing's photo, base64-encodes it, and calls Claude vision directly; every failure mode (missing photo, fetch failure, API error, bad response) returns `(None, None)` and never blocks ingestion, matching `filters.py`'s broader "unknown field, don't block on it" pattern. `webapp/rescore.py` (`poe rescore`) is the manual, one-off backfill command - it re-scores anything with `ai_score is None` or a stale `ai_profile_version` (bumped in `config.yaml`'s `scoring:` section whenever `taste_profile.md` meaningfully changes). Critically, this fallback path has **never actually been exercised against the real Anthropic API** - it was built and tested with no `ANTHROPIC_API_KEY` available, so only its graceful-degradation branches are proven, not the live vision call itself.

[browser-import](../entities/browser-import.md)'s `import_listings()` is where the two paths converge: it prefers a pre-computed `ai_score`/`ai_reasoning` already on the raw listing dict, and only invokes the optional `score_fn` fallback (wired up only if both `taste_profile.md` and `ANTHROPIC_API_KEY` exist) when neither is present. A listing with a pre-computed score never calls the fallback even if one is configured.

**`taste_profile.md` itself is rough signal, not confident judgment.** It has only 3 liked StreetEasy examples (256 Cumberland St #4, 75 South 3rd St #1, 163 Warren St #1) and zero disliked examples. What it can support: good light/windows, "real character" via modern renovation or authentic prewar detail, private outdoor space as a plus but not required, and finish level explicitly not being the deciding factor. It cannot yet support "score X down" reasoning - the absence of a positive signal must not be read as a negative one. Sharpening it needs disliked examples from the user.

## Related entities

- [scoring](../entities/scoring.md)
- [browser-scan-streeteasy](../entities/browser-scan-streeteasy.md)
- [browser-scan-zillow](../entities/browser-scan-zillow.md)
- [browser-import](../entities/browser-import.md)
- [zillow-email-import](../entities/zillow-email-import.md)
- [shared-config](../entities/shared-config.md)

## Sources

DECISIONS.md ("AI scoring: the interactive session scores directly, no API key required"); CLAUDE.md ("AI taste-match scoring" architecture bullet, "Known limitations"); wiki/entities/scoring.md, wiki/entities/browser-import.md, wiki/entities/browser-scan-streeteasy.md.
