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
   - Accumulate the raw cards.
   - If there are more pages left to fetch, `time.sleep(PAGE_PACING_SECONDS)`
     before navigating to the next one. **Do not skip this** - this is the
     specific fix for the PerimeterX trip described above.
   - If a page's `page_info()` title suggests a block page ("Access to this
     page has been denied" or similar), stop immediately, tell the user, and
     do not retry in the same session.

6. Once done paging, run (still inside `browser_exec`, since that's where the
   accumulated raw cards live) `apt_agent.browser_scan_helpers.parse_page_json`
   on the accumulated list, then `dedupe_within_batch` on the result. Write
   the final JSON list to a file in the scratchpad directory.

7. Run `python -m apt_agent.browser_import <scratch-file-path>` via Bash (use
   the repo's `.venv/bin/python` if present). This dedups against everything
   already in `listings.db`, applies today's hard filters (for the
   `would_alert` stat only - it never sends email), and AI-scores newly
   imported listings if a `taste_profile.md` + `ANTHROPIC_API_KEY` are both
   configured.

8. Report back to the user: how many pages were scanned vs. how many exist
   in total (from the results page's header count), and the `{new,
   already_seen, would_alert}` stats the import script printed. If the page
   cap was hit before reaching the last page, say so explicitly and note that
   running the scan again will pick up where it left off (already-seen
   listings are skipped automatically, so nothing needs to be tracked
   between runs).
