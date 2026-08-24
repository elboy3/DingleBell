---
type: concept
status: active
verified: 2026-08-24
tags: [swipe-model, blind-judgment, matching, product-design]
---

# Blind swipe model

## Summary

The core product mechanic of the shared web app: Elliott and Madison each swipe left/right on listings independently, in their own private queue, blind to what the other has decided. A listing becomes a match - and moves into a shared Matches page for category ratings and comments - only when both swipe right. A left swipe is personal, permanent, and has no undo, but stays visible in a full-transparency Passed view. The one deliberate, non-negotiable invariant underlying all of this: a user must never be shown their partner's opinion on a listing the user hasn't decided on yet.

## Details

This replaced an earlier shared-feed design where both people rated/commented/hid listings together - see [the-two-pivots](the-two-pivots.md) for why. The mechanism lives in three layers:

- **Data**: `listing_swipes` (`listing_id, user, direction, swiped_at`, unique per listing+user) records each person's independent decision via `store.record_swipe()`, which is explicitly one-time and permanent - a re-swipe overwrites direction/time at the DB layer, but the app layer never exposes an undo. See [store](../entities/store.md).
- **Logic**: [feed-logic-and-ranking](../entities/feed-logic-and-ranking.md)'s `match_status()` derives `"pending"`/`"match"`/`"miss"` from the two recorded swipes at request time (never stored). The safety-critical primitive is `waiting_on(swipes, user)`, which returns the partner's name only when the *requesting* user is the one with a pending right-swipe and the partner hasn't decided yet - by construction it can never leak the partner's own pending opinion to the viewer. `matches_for_user()` builds on this: it only ever surfaces "waiting on partner" for the viewer's own pending like, and the mirror case (partner already liked it, viewer hasn't swiped) is simply never included in that viewer's response - it isn't a suppressed field, it's absent entirely.
- **UI**: [frontend-swipe-page](../entities/frontend-swipe-page.md) shows the partner's *comment* on a listing (if any) but never their swipe decision, preserving blindness while still allowing async notes. [frontend-matches-and-passed](../entities/frontend-matches-and-passed.md)'s Matches page renders a "waiting on a decision" section using `waiting_on`, and its Passed page is the deliberate transparency counterpart - every left swipe either person has made is visible there (split into disagreements vs. mutual passes), so nothing silently disappears even though nothing can be undone.

Filtering out and ranking down are treated as two different, deliberately separate mechanisms. A swipe-left is how a listing leaves consideration *before* a match, personal and irreversible. The shared `hidden`/`hidden_reason` flag (`set_hidden()` in [store](../entities/store.md)) is a completely different, *shared*, *reversible* action used for exactly one purpose post-match: the Leaderboard's "off market" disqualify when a matched listing is no longer really available, undoable from the Passed view. Once matched, ranking (min-of-both-ratings, deliberately MIN not average so one person's dislike isn't smoothed over, or AI score) is a live, non-destructive sort - never a hide.

The "waiting on a decision" feature was added within the same session as a targeted extension of this model, built specifically to respect the blindness invariant via per-viewer scoping in `waiting_on()`/`matches_for_user()`, rather than a shared "someone liked this" flag that would have leaked information across users.

## Related entities

- [feed-logic-and-ranking](../entities/feed-logic-and-ranking.md)
- [frontend-swipe-page](../entities/frontend-swipe-page.md)
- [frontend-matches-and-passed](../entities/frontend-matches-and-passed.md)
- [frontend-listing-card](../entities/frontend-listing-card.md)
- [store](../entities/store.md)
- [api-routes](../entities/api-routes.md)

## Sources

DECISIONS.md ("Dating-app swipe model: independent per-person swiping, matches gate review"); CLAUDE.md ("The second pivot", "Filtering out and ranking down are two different..."); wiki/entities/feed-logic-and-ranking.md, wiki/entities/store.md, wiki/entities/frontend-swipe-page.md, wiki/entities/frontend-matches-and-passed.md.
