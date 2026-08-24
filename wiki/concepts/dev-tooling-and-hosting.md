---
type: concept
status: active
verified: 2026-08-24
tags: [dev-tooling, testing, verification, hosting, anti-bot]
---

# Dev tooling, verification, and hosting

## Summary

This repo has no automated test suite anywhere - "does it work" is answered by static checks (`ruff`/`ty`/`tsc`) plus actually running the app and exercising it, ideally via a headless Playwright browser rather than by reading the code and assuming it works. Hosting is planned (Fly.io + Turso/libSQL) but not yet done. Separately, both browser-scan ingestion paths share a general anti-bot pacing discipline (`PAGE_PACING_SECONDS`, `MAX_PAGES_PER_SESSION`) that any future browser-driven scraping in this project should reuse rather than re-derive.

## Details

**Backend tooling.** `ruff` (format + a simple `E`/`F`/`I`/`UP`/`B` lint ruleset) and `ty` (Astral's mypy-equivalent type checker, no special config needed) are configured in `pyproject.toml`. `poethepoet` (`poe`) is the task runner, chosen over a plain Makefile specifically because it's Python-native and its config lives alongside the ruff/ty config already in `pyproject.toml`. Tasks: `poe fmt`/`fmt-check`, `poe lint`/`lint-fix`, `poe typecheck`, `poe check` (the full verify-only sequence - fmt-check + lint + typecheck, CI/pre-commit style), `poe api` (FastAPI on port 8000), `poe web` (Vite dev server on port 5175), `poe dev` (both), `poe rescore` (`webapp/rescore.py`). `uv` is adopted only lightly for local env/installs - `requirements.txt`/`requirements-dev.txt` stay the source of truth, and GitHub Actions plus the planned Dockerfile stay on plain `pip`. `uv`'s stricter resolver did catch a real bug: invented, never-verified version pins in `requirements.txt` (e.g. `anthropic==0.40.0` when `1.0.0` was actually installed and tested against).

**Frontend tooling.** Plain `npm`/`npx` in `frontend/` - `npx tsc --noEmit` for type-checking, no separate lint step configured. `frontend/` also has its own `playwright` dev dependency, used specifically to test the app's own UI with a plain headless Chromium browser, completely independent of the user's real, `browser-use`-driven session - this matters because `browser-use` needs a literal click on a Chrome permission popup that blocks unattended testing, while the app's own UI only talks to the local FastAPI API and needs no StreetEasy authentication at all.

**"How do I verify a change works" - there is no test suite.** Verification here means: `poe check` for any Python change, `npx tsc --noEmit` (in `frontend/`) for any TypeScript change, and then actually running the feature - manually or via a headless Playwright script driven against the real running app (`localhost:5175`/`localhost:8000`) - before calling anything done. This project's own history backs this up directly: real-world testing repeatedly surfaced genuine bugs that reading the code alone would have missed (an OAuth scope gap, an unbounded Gmail query pulling years of backlog, page-fetch 403s, invented `requirements.txt` version pins, an empty `min_score=""` crashing a route, a cross-hostname `SameSite` cookie bug that silently broke login, a Python round-half-to-even bug understating category ratings). "Should work from reading the code" is explicitly not the bar on this project.

**Anti-bot pacing as a general principle.** Both StreetEasy and Zillow browser scans ([browser-scan-streeteasy](../entities/browser-scan-streeteasy.md), [browser-scan-zillow](../entities/browser-scan-zillow.md)) share `PAGE_PACING_SECONDS = 20` and `MAX_PAGES_PER_SESSION = 5`, defined once in `apt_agent/browser_scan_helpers.py` and reused (not re-tuned) by the Zillow scan, because both sites' anti-bot walls were confirmed to behave the same way: a tight rapid loop of navigations trips a block, a single organic or properly-paced load usually doesn't. Pacing reduces but does not guarantee immunity - blocks have recurred on both sites even with correct pacing, sometimes as early as the 2nd load in a session. The non-negotiable rule on any block: stop immediately, do not retry in the same session, and never open a new tab or fresh browser identity to route around it - doing so would cross from legitimate authenticated access into evasion, which is the entire reason this technique is allowed at all. Resuming across sessions is always safe regardless of where a scan stopped, since `ListingStore.already_seen()` skips anything already imported.

**Hosting - planned, not done.** The plan is Fly.io (app) + Turso/libSQL (db), not yet set up (`turso auth login` + `fly launch`/`fly deploy` are still `[MANUAL]` items in `STATUS.md`). Turso's Python client is designed as a near-drop-in for `sqlite3`, so `store.py`'s connection logic is expected to change in one place, in remote (non-embedded-replica) mode - no sync complexity needed at this traffic level.

## Related entities

- [webapp-app-and-deps](../entities/webapp-app-and-deps.md)
- [browser-scan-streeteasy](../entities/browser-scan-streeteasy.md)
- [browser-scan-zillow](../entities/browser-scan-zillow.md)
- [check-setup](../entities/check-setup.md)
- [shared-config](../entities/shared-config.md)

## Sources

CLAUDE.md ("Dev tooling", "Planned hosting", "Pacing matters even with a real authenticated session", "Working style notes for future sessions"); DECISIONS.md ("Added ruff/ty/poethepoet, light uv adoption", "Browser-authenticated scan replaces anonymous scraping for full census"); STATUS.md (hosting checklist items under "Needs you").
