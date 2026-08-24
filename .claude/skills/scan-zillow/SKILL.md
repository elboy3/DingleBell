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
   `https://www.zillow.com/{neighborhood-slug}/rentals/?searchQueryState=...`
   where `{neighborhood-slug}` is usually the neighborhood name lowercased
   with spaces replaced by hyphens plus `-brooklyn-ny` (e.g. "Fort Greene"
   -> `fort-greene-brooklyn-ny`, "Clinton Hill" -> `clinton-hill-brooklyn-ny`)
   - **but not always**: `williamsburg-brooklyn-ny` silently redirects to a
   different, adjacent neighborhood ("East Williamsburg"); the correct slug
   there is `williamsburg-new-york-ny`. Don't trust the guessed pattern
   blindly - see the sanity-check below. The URL-encoded `searchQueryState`
   JSON is:
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
   `isMapVisible` doesn't actually matter for the extraction technique
   below (unlike the older DOM-scraping approach) - `false` is just kept
   for a cleaner, unscrolled screenshot in step 7.

   After the first navigation, sanity-check the page title (`page_info()`)
   actually matches the intended neighborhood, not a redirect to something
   else or a 0-result page.

4. Read `apt_agent/browser_scan_helpers.py` for `PAGE_PACING_SECONDS`,
   `MAX_PAGES_PER_SESSION`, and `matches_config_bounds()` (shared across
   both scan skills - don't hardcode them here). Read
   `apt_agent/zillow_scan/extract_next_data.js`'s contents.

5. For page loads (see the note below on why "pages" barely applies
   anymore) up to `MAX_PAGES_PER_SESSION`:
   - `goto_url(...)` to the neighborhood's URL (reuse one tab across
     loads - don't open a new tab per load).
   - `wait_for_load()`.
   - Run `extract_next_data.js`'s content via `js(...)` to get that
     load's raw results. **This is the primary extraction technique** -
     it reads Zillow's own `__NEXT_DATA__` script tag (structured JSON
     the page's React app hydrates from), which is both more complete
     and more reliable than DOM-scraping `article.property-card` text
     (confirmed 2026-08-24: a same-query Clinton Hill re-test got 26
     results this way versus only 6 from the older `extract.js` earlier
     the same day - `extract.js`'s `wait_for_load()` was returning before
     the client-side card list finished hydrating, a timing race, not a
     hard cap). If `extract_next_data.js` returns `null` (the
     `__NEXT_DATA__` tag was missing or Zillow restructured it), fall
     back to `extract.js` + `zillow_scan_helpers.parse_page_json()`
     instead of failing the session.
   - Take a screenshot (`browser_screenshot`) of the page too, if
     `taste_profile.md` exists (see step 7 - skip if there's no profile).
   - Accumulate the raw results (and that load's screenshot, if taken).
   - If there are more loads left to make, `time.sleep(PAGE_PACING_SECONDS)`
     before navigating to the next one. **Do not skip this.**
   - If a page's `page_info()` title suggests a block page ("Access to this
     page has been denied" or similar), stop immediately, tell the user, and
     do not retry in the same session (see the note above about not trying
     to dodge it with a fresh identity either). Blocks have recurred more
     than once around the 3rd-5th paced load in a session even with correct
     pacing - pacing reduces the odds, it doesn't guarantee immunity.

   **This technique still only returns roughly one page's worth of
   results per load** (matched `categoryTotals.cat1.totalResultCount`'s
   first page in testing, e.g. 18 of 29 for Fort Greene) - it fixes data
   *quality* and *reliability* per load, not Zillow's own pagination,
   which separately has been confirmed unreliable (silently drops filter
   state past page 1 - see `matches_config_bounds()` and DECISIONS.md).
   **Practical consequence: budget each paced session as roughly one
   load per neighborhood, spread across more neighborhoods**, rather than
   trying to paginate deep into one - a neighborhood bigger than what one
   load returns (Williamsburg, at 221+ total, is by far the biggest of
   the 7) will need many sessions over time, same as before. Re-running
   the same neighborhood in a later session is safe and useful even
   without new pagination - Zillow's own result ordering shifts over
   time (by "days on market," new listings, etc.), so a repeat load
   often surfaces genuinely new results, as happened with Clinton Hill.

6. Once done, run (still inside `browser_exec`, or after copying the raw
   JSON out to a scratch file) `apt_agent.zillow_scan_helpers.
   parse_next_data_page()` on the accumulated list (this both structures
   the fields and drops Zillow's own "relaxed"/building-aggregator cards
   - see that function's docstring), then `apt_agent.
   browser_scan_helpers.dedupe_within_batch()` on the result, then
   `apt_agent.browser_scan_helpers.matches_config_bounds()` per listing
   to catch anything that snuck past Zillow's own filter (this has
   happened for real - see DECISIONS.md). Set `neighborhood` on each kept
   listing to the neighborhood this session is scanning -
   `parse_next_data_result()` deliberately doesn't guess it.

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
   StreetEasy scan uses. `source` is set to `"zillow-browser-scan"` by
   `parse_next_data_result()`/`parse_card()`, distinguishing this from
   both the StreetEasy scan and the automated email import in
   `listings.source`.

10. Report back to the user: which neighborhood(s), how many loads made
    vs. the total Zillow itself reported (title's "N Rentals," and/or
    `categoryTotals.cat1.totalResultCount` if you captured it - note
    these two numbers have been observed to disagree, see DECISIONS.md),
    and the `{new, already_seen, backfilled, would_alert, scored}` import
    stats per neighborhood. If a neighborhood wasn't fully covered, say
    so explicitly and note it's safe to resume later (already-seen
    listings are skipped automatically, and re-running the same
    neighborhood later can still surface new results even without
    Zillow's own pagination working, since results reorder over time).
    Update the coverage table in `STATUS.md` (captured / reported total
    per neighborhood) - that table, not a vague "done" feeling, is the
    project's actual answer to "how do we know we've got everything."
