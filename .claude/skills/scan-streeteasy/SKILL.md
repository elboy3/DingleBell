---
name: scan-streeteasy
description: Scan the StreetEasy saved-search results page via the user's real authenticated browser session (browser-use MCP plugin), extract listing data, and import it into listings.db for the shared apartment-review web app. Use when the user asks to "scan StreetEasy", "check for new listings", "update the feed", or similar - this is the primary ingestion path now that speed/real-time alerts are no longer the goal.
---

# Scan StreetEasy into the shared listings db

This is an interactive, session-driven scan - it only works because it drives
the user's real, already-logged-in browser via the `browser-use` MCP plugin,
which bypasses the PerimeterX wall that blocks anonymous scraping (see
`DECISIONS.md`). It cannot run unattended/on a schedule. Running it "whenever
someone asks" is the accepted tradeoff of this pivot - see
`.claude/plans/well-i-realized-that-goofy-platypus.md` for the full context.

**Known constraint, mitigated below:** a tight loop of 13 rapid sequential
page loads tripped PerimeterX on page 2 during this feature's initial build,
even with a real authenticated session - a single organic load did not. The
pacing and page cap below exist specifically to avoid re-triggering that.

**If you ever need a specific listing's full photo set** (not just the
search-results card thumbnail this skill's step 7 screenshots) - e.g. to
open an individual listing page - don't try clicking through its photo
lightbox; it wasn't reliably clickable via CDP in testing (see DECISIONS.md
"Photo galleries: extract image URLs directly"). Extract image URLs from the
DOM instead and view them via download + `Read`.

## Procedure

1. If the `browser-use` MCP plugin's tools aren't loaded yet, `ToolSearch`
   for them (`mcp__plugin_browser-use_browser-use__browser_exec` /
   `browser_screenshot`). If the harness needs remote-debugging permission
   enabled in Chrome, tell the user and wait for their confirmation before
   retrying - don't guess or hammer retries.

2. Confirm with the user which saved-search URL to scan if it's not obvious
   from context (check open tabs via `list_tabs()` first - the user has had
   a StreetEasy saved-search results tab open before).

3. Read `apt_agent/browser_scan_helpers.py` for `PAGE_PACING_SECONDS` and
   `MAX_PAGES_PER_SESSION` (don't hardcode these values here - read them, so
   a future tuning change to that file is automatically picked up).

4. Read `apt_agent/browser_scan/extract.js`'s contents.

5. For page 1 through `MAX_PAGES_PER_SESSION` (or until a page returns zero
   cards, whichever comes first):
   - `goto_url(f"{base_url}&page={n}")` (reuse one tab across pages - don't
     open a new tab per page).
   - `wait_for_load()`.
   - Run `extract.js`'s content via `js(...)` to get that page's raw cards.
   - Take a screenshot (`browser_screenshot`) of the page too, if `taste_profile.md`
     exists (see step 7 - skip the screenshot if there's no profile to score against).
   - Accumulate the raw cards (and that page's screenshot, if taken).
   - If there are more pages left to fetch, `time.sleep(PAGE_PACING_SECONDS)`
     before navigating to the next one. **Do not skip this** - this is the
     specific fix for the PerimeterX trip described above.
   - If a page's `page_info()` title suggests a block page ("Access to this
     page has been denied" or similar), stop immediately, tell the user, and
     do not retry in the same session.

6. Once done paging, run (still inside `browser_exec`, since that's where the
   accumulated raw cards live) `apt_agent.browser_scan_helpers.parse_page_json`
   on the accumulated list, then `dedupe_within_batch` on the result.

7. **AI scoring - no API key needed, you do this yourself.** If
   `taste_profile.md` doesn't exist yet, skip this step entirely (score
   nothing - don't guess at a profile). If it does exist, read it, then for
   each listing that isn't already in `listings.db` (check via
   `ListingStore.already_seen(url)` - don't bother scoring ones that are
   already there, the import will ignore any score given for them anyway):
   look at that listing's photo in the page screenshot from step 5 (matched
   by address/price text next to it), judge it against the taste profile
   using your own vision - no Anthropic API call, you're already looking at
   it - and set that listing dict's `ai_score` (0-100) and `ai_reasoning`
   (one sentence, citing the specific visual cue) fields directly. This is
   the primary scoring path now; `webapp/scoring.py`'s API-key-based scorer
   is a secondary fallback for listings you don't score this way, not
   something you need to configure to do this.

8. Write the final JSON list (each listing's normal fields, plus `ai_score`/
   `ai_reasoning` where you scored it in step 7) to a file in the scratchpad
   directory.

9. Run `python -m apt_agent.browser_import <scratch-file-path>` via Bash (use
   the repo's `.venv/bin/python` if present). This dedups against everything
   already in `listings.db`, applies today's hard filters (for the
   `would_alert` stat only - it never sends email), and saves whatever
   `ai_score`/`ai_reasoning` you set in step 7 (or falls back to the
   API-key scorer per-listing if you didn't score it and one's configured).

10. Report back to the user: how many pages were scanned vs. how many exist
    in total (from the results page's header count), and the `{new,
    already_seen, would_alert, scored}` stats the import script printed. If
    the page cap was hit before reaching the last page, say so explicitly
    and note that running the scan again will pick up where it left off
    (already-seen listings are skipped automatically, so nothing needs to be
    tracked between runs).
