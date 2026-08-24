---
type: concept
status: active
verified: 2026-08-24
tags: [pivot, history, architecture, swipe-model]
---

# The two pivots

## Summary

This project changed direction twice. Pivot 1 (2026-08-22) replaced the Gmail-alert email pipeline with an authenticated-browser-scan as the primary ingestion technique, because StreetEasy never actually sent real-time per-listing alerts and the emails lacked photos/detail - and, more fundamentally, because the user's real problem turned out to be shared/asynchronous review, not speed. Pivot 2 (same session, later) reworked the resulting shared feed into independent, blind, dating-app-style swiping after the user clarified that both people "never see the same listing twice" and decide separately. Both pivots are documented as deliberate, user-driven scope changes, not silent redesigns - each is the precedent for how future scope changes on this project should happen.

## Details

**Pivot 1 - email alerts to browser-scan, speed to shared/async review.** Phase 1 (`apt_agent/`, see [email-pipeline](../entities/email-pipeline.md)) was built first on the assumption that being first to see a new listing was the main thing worth optimizing. Real-world testing on 2026-08-20/22 falsified that assumption on two independent counts: StreetEasy only sends a few thin "recommendations" digests a day, not real per-listing alerts, and those emails are missing photos and most detail anyway. Separately, the `browser-use` MCP plugin turned out to let the user's own already-authenticated browser session load StreetEasy's full search-results page directly, bypassing the PerimeterX anti-bot wall that blocks anonymous scraping - not by evading it, but because it's a real user's own browser loading a page they're entitled to see (see [browser-scan-streeteasy](../entities/browser-scan-streeteasy.md)). But the decisive fact was what the user actually said the problem was: *"not re-evaluating the same apartments over and over, not holding rankings in our heads, and letting both of us react to listings async... without always having to text back and forth in real time."* That's a shared-state/collaboration problem, not a latency problem. The email pipeline was kept running (deprioritized, not removed) in case Zillow's alert cadence turned out worth revisiting - which it later did, becoming [zillow-email-import](../entities/zillow-email-import.md), an independent, still-active, fully-automated path unrelated to Phase 1 despite also using Gmail. Speed as a goal was explicitly retired: `CLAUDE.md`'s goal ordering states real-time alerting is "no longer a priority" and warns against adding urgency-driven complexity back in without being asked.

**Pivot 2 - shared feed to independent blind swiping.** The first webapp build (still within the same pivot) had both people rate/comment/hide from one shared feed, with a shared "interested" flag. Direct user feedback reframed the whole model: *"it's actually going to be like a dating app... we each do this separately... for each of us we never see the same listing twice."* This produced the current mechanic (fully detailed in [blind-swipe-model](blind-swipe-model.md)): each person gets a private swipe queue ([frontend-swipe-page](../entities/frontend-swipe-page.md)) and swipes left/right independently and blind to the other; a listing becomes a match only when both swipe right, moving it to a shared Matches page for category ratings. The shared "interested" flag and the grid-browse Feed page were removed; the `interested`/`interested_by`/`interested_at` columns were left in the schema (dead, unused) rather than dropped, since SQLite can't cheaply drop columns. The Leaderboard survived downstream of matches (confirmed explicitly with the user rather than assumed). The Open Houses feature was removed outright in a later cleanup pass rather than patched for the new model, since it was never updated for swipe/match and nobody asked to keep it as a dedicated page - a listing's own open-house info still shows inline on its card.

## Related entities

- [email-pipeline](../entities/email-pipeline.md)
- [browser-scan-streeteasy](../entities/browser-scan-streeteasy.md)
- [browser-scan-zillow](../entities/browser-scan-zillow.md)
- [zillow-email-import](../entities/zillow-email-import.md)
- [frontend-swipe-page](../entities/frontend-swipe-page.md)
- [store](../entities/store.md)

## Sources

DECISIONS.md ("Pivot from email alerts to a shared web app, deprioritizing speed", "Browser-authenticated scan replaces anonymous scraping for full census", "Dating-app swipe model: independent per-person swiping, matches gate review"); CLAUDE.md ("The pivot", "The second pivot", "Goal ordering"); STATUS.md ("Phase 2 / 2.5 - SUPERSEDED..." and "Shared web app pivot" log entries).
