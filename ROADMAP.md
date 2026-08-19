# ROADMAP.md

## Phase 1 - Ingestion, filtering, alerting  [IN PROGRESS - confirming it works]

- [x] Gmail ingestion of alert emails (StreetEasy/Zillow/RentHop/NakedApartments)
- [x] Listing URL extraction + best-effort page parsing
- [x] Hard filters: price, beds/baths, move-in window (Sep 1 - Oct 3)
- [x] SQLite dedup by URL
- [x] SQLite dedup by normalized address (cross-source)
- [x] Email alerts via Gmail API
- [x] GitHub Actions deployment, public repo, variable-frequency schedule
- [x] listings.db persistence via commit-back-to-repo
- [x] Failure alert email (`if: failure()` in workflow)
- [x] Daily heartbeat email with basic stats
- [x] Dry-run/test mode
- [ ] **User confirms end-to-end it's working reliably in production** <- current blocker before Phase 2
- [ ] (deferred) Delisting detection
- [ ] (deferred) Weekly "close calls" digest for near-miss filtered listings

## Phase 2 - Taste/style scoring  [NOT STARTED - do not begin without user confirmation]

- [ ] Collect reference photos (liked + disliked apartments) from user
- [ ] Claude-vision-derived written taste profile
- [ ] Score each new listing's photos against the taste profile
- [ ] Include score + one-line "why this one" reasoning in alert emails
- [ ] Feedback loop: thumbs up/down on real alerts refines the profile over time

## Phase 2.5 - Interactive texting agent  [DESIGNED, NOT STARTED]

User wants to interact via text instead of (or alongside) email, with
queries like "anything in Boerum Hill that looks like the Fort Greene
one?" - this is a real scope increase, not a bolt-on: it requires an
always-on/on-demand server (can't run on GitHub Actions cron) and
absorbs Phase 2's taste-profile work as its data foundation. Designed
as a deliberately simple v1 - see DECISIONS.md for why each
simplification was chosen.

- [ ] Twilio SMS number + webhook endpoint (serverless: Lambda/Fly.io/
      Render, not a always-on VPS - traffic is a few texts/day)
- [ ] Per-listing Claude-vision description generated at ingestion time,
      for every listing *seen* (not just ones that pass hard filters) -
      this is the data similarity queries run against
- [ ] Shared single conversation thread (one phone number, both people
      text it, one running history) + last-N-listings-referenced context
- [ ] Similarity query handling: no vector DB/embeddings - at this
      volume, hand Claude the target + candidate descriptions directly
      and ask it to compare/rank in one call
- [ ] Preference notes log: freeform texted preferences ("hate galley
      kitchens") appended to a table, feeds the same taste-profile
      prompt as Phase 2's reference photos
- [ ] Single-call intent handling: one Claude call per incoming text,
      given conversation history + recent listings as context, decides
      whether to answer/log-preference/both and drafts the reply -
      no separate classifier step
- [ ] Depends on: Phase 2's taste-profile foundation should exist first
      (per sequencing decision - see DECISIONS.md)

## Phase 3 - Nice-to-haves  [NOT STARTED]

- [ ] Auto-drafted inquiry message ("still available? can we see it Thurs?")
- [ ] Days-on-market tracking as a negotiation-leverage signal
- [ ] Delisting detection (moved here from deferred Phase 1 list)
- [ ] Weekly close-calls digest (moved here from deferred Phase 1 list)
- [ ] Commute-time enrichment via Maps API
- [ ] Rent-stabilization lookup against NYC public data
