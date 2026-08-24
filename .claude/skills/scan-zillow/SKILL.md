---
name: scan-zillow
description: Backfill historical Zillow rental listings (from before the automated email pipeline existed) by scanning Zillow's search-results page via the user's real authenticated browser session (browser-use MCP plugin), one target neighborhood at a time, and importing into listings.db. Use when the user asks to "backfill Zillow", "scan Zillow for old listings", or similar. Do NOT use this for day-to-day new-listing ingestion - apt_agent/zillow_email_import.py already covers that automatically and unattended, no browser needed.
---

# Backfill Zillow listings into the shared listings db

**This is a backfill tool, not the primary Zillow ingestion path.**
`apt_agent/zillow_email_import.py` already runs unattended on the GitHub
Actions poll cron and catches every new Zillow listing within minutes, no
browser needed - see `DECISIONS.md` ("Zillow instant-update emails"). This
skill exists only to catch listings that existed *before* that pipeline was
set up, which the email pipeline can never see (Zillow doesn't resend old
alerts). Once the backlog is caught up, this skill won't need to run again
except opportunistically.

This is an interactive, session-driven scan - it only works because it
drives the user's real, already-logged-in browser via the `browser-use` MCP
plugin, same reasoning as `.claude/skills/scan-streeteasy/SKILL.md`. It
cannot run unattended/on a schedule.

**Known constraint, mitigated below - confirmed twice now, not just
theoretical:** StreetEasy tripped its anti-bot wall after 13 rapid
sequential page loads (see that skill's own note). Zillow tripped its own
wall even faster - 5 page loads only ~3 seconds apart, during this skill's
initial build - while a single organic load, and later a single retry
after waiting, did not. The pacing and page cap below exist specifically to
avoid re-triggering that. If you hit a block anyway (see step 6), don't
retry in the same session, and don't try switching to a "fresh" browser
identity to route around it - the whole reason this approach is legitimate
is that it's the user's own authenticated browser loading a page they're
entitled to see, not automated evasion, and deliberately spinning up a new
identity specifically to dodge a block crosses into evasion. Just wait and
try again later.

## Procedure

1. If the `browser-use` MCP plugin's tools aren't loaded yet, `ToolSearch`
   for them (`mcp__plugin_browser-use_browser-use__browser_exec` /
   `browser_screenshot`). If the harness needs remote-debugging permission
   enabled in Chrome, tell the user and wait for their confirmation before
   retrying - don't guess or hammer retries.

2. Read `config.yaml`'s `search:` section for `price_min`/`price_max`/
   `beds_min`/`baths_min`/`neighborhoods` - don't hardcode these, they're
   user-owned. Confirm with the user which neighborhood(s) to scan this
   session if not obvious from context - one neighborhood per session is
   the realistic unit of work (see step 5's page-cap math below).

   Deliberately do **not** filter by move-in date here, even though
   Zillow's own search UI supports it - this project casts a wider net
   than the user's manual search on purpose (see config.yaml's own
   comment on this), the same reason the StreetEasy scan doesn't
   hard-filter either.

3. Build the search URL for one neighborhood:
   `https://www.zillow.com/{neighborhood-slug}-brooklyn-ny/rentals/{page}_p/?searchQueryState=...`
   where `{neighborhood-slug}` is the neighborhood name lowercased with
   spaces replaced by hyphens (e.g. "Fort Greene" -> `fort-greene`,
   "Clinton Hill" -> `clinton-hill`), `{page}_p/` is omitted for page 1
   and `2_p/`, `3_p/`, etc. for later pages, and the URL-encoded
   `searchQueryState` JSON is:
   ```json
   {
     "isMapVisible": false,
     "isListVisible": true,
     "filterState": {
       "fr": {"value": true}, "fsba": {"value": false}, "fsbo": {"value": false},
       "nc": {"value": false}, "cmsn": {"value": false}, "auc": {"value": false},
       "fore": {"value": false},
       "mp": {"min": <price_min>, "max": <price_max>},
       "beds": {"min": <beds_min>}, "baths": {"min": <baths_min>},
       "sort": {"value": "days"}
     }
   }
   ```
   **`isMapVisible: false` matters** - with the map visible, Zillow's
   results list only renders ~5 cards into the DOM at a time no matter
   how it's scrolled (it's virtualized, and scripted scrollTop changes /
   synthetic wheel events don't reliably trigger it to render more, at
   least not in initial testing - a fresh approach could revisit this
   if a future session has a better technique). With the map hidden, the
   full-width list layout renders ~11-18 cards in the initial DOM without
   any scrolling needed at all, which is what makes per-page extraction
   (no scroll-trickery required) actually work.

   After the first navigation, sanity-check the page title (`page_info()`)
   actually matches the intended neighborhood, not a redirect to something
   else or a 0-result page - neighborhood slugs aren't all confirmed, only
   `fort-greene-brooklyn-ny` has been verified to resolve correctly so far.

4. Read `apt_agent/browser_scan_helpers.py` for `PAGE_PACING_SECONDS` and
   `MAX_PAGES_PER_SESSION` (shared across both scan skills - don't hardcode
   them here). Read `apt_agent/zillow_scan/extract.js`'s contents.

5. For page 1 through `MAX_PAGES_PER_SESSION` (or until a page returns zero
   cards, whichever comes first):
   - `goto_url(...)` to that page's URL (reuse one tab across pages - don't
     open a new tab per page).
   - `wait_for_load()`.
   - Run `extract.js`'s content via `js(...)` to get that page's raw cards
     (no scrolling needed - see step 3's note).
   - Take a screenshot (`browser_screenshot`) of the page too, if
     `taste_profile.md` exists (see step 7 - skip if there's no profile).
   - Accumulate the raw cards (and that page's screenshot, if taken).
   - If there are more pages left to fetch, `time.sleep(PAGE_PACING_SECONDS)`
     before navigating to the next one. **Do not skip this.**
   - If a page's `page_info()` title suggests a block page ("Access to this
     page has been denied" or similar), stop immediately, tell the user, and
     do not retry in the same session (see the note above about not trying
     to dodge it with a fresh identity either).

   A neighborhood with under ~50-60 listings (check the page title's
   "N Rentals" count on the first load) fits in one session at ~11-18
   cards/page. A bigger one will need multiple sessions - that's fine,
   `already_seen()`-based dedup makes resuming safe, same as StreetEasy.

6. Once done paging, run (still inside `browser_exec`) `apt_agent.
   zillow_scan_helpers.parse_page_json` on the accumulated list, then
   `apt_agent.browser_scan_helpers.dedupe_within_batch` on the result.

7. **AI scoring - no API key needed, you do this yourself.** Same
   procedure as `.claude/skills/scan-streeteasy/SKILL.md` step 7: if
   `taste_profile.md` doesn't exist, skip scoring entirely. If it exists,
   for each listing not already in `listings.db` (`ListingStore.
   already_seen(url)`), judge its photo (matched by address/price text)
   against the taste profile using your own vision, and set `ai_score`/
   `ai_reasoning` directly on that listing dict.

8. Write the final JSON list to a file in the scratchpad directory.

9. Run `python -m apt_agent.browser_import <scratch-file-path>` via Bash
   (use the repo's `.venv/bin/python` if present) - the same importer the
   StreetEasy scan uses, `source` is already set to `"zillow-browser-scan"`
   by `zillow_scan_helpers.parse_card` so it's distinguishable from both
   the StreetEasy scan and the automated email import in `listings.source`.

10. Report back to the user: which neighborhood, how many pages scanned vs.
    the total the page header reported, and the `{new, already_seen,
    backfilled, would_alert, scored}` import stats. If the neighborhood
    wasn't fully covered, say so explicitly and note it's safe to resume
    later (already-seen listings are skipped automatically). Track which
    of the 7 `config.yaml` neighborhoods still need a first pass -
    `DECISIONS.md`/`STATUS.md` is a reasonable place to log progress across
    sessions until the backlog is fully caught up.
