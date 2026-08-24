# Wiki operation log

Append-only. One entry per wiki-authoring operation (not per code commit -
`DECISIONS.md` remains the place for why-level project decision history).
Format: `## [DATE] operation | description`

## [2026-08-24] initial-build | Repo inventory
Explore agent produced a full, verified repo inventory ahead of the wiki
build: confirmed no test suite exists anywhere in the repo, and no
`wiki/`/`docs/` directory existed yet.

## [2026-08-24] initial-build | Architecture design + review
Drafted the wiki's three-layer architecture (raw sources / wiki / schema),
the 20-entity + 7-concept page manifest, domain ownership split, page
template, and verification plan. A Plan agent critiqued the draft against
the real repo and found: a real orphaned file (`mapEmbed.ts`) missing from
the manifest, a cross-cutting config file (`config.yaml`) misattributed to
the wrong domain, a narrative-consistency risk in running all agents fully
in parallel, and the risk that this wiki duplicates `CLAUDE.md`'s existing
"File map"/"Architecture summary" sections. All four were fixed before the
build started (see README.md's "Relationship to existing docs" section for
the last one).

## [2026-08-24] wave-1 | Shared data layer
Wrote `entities/store.md`, `entities/shared-config.md`.

## [2026-08-24] wave-1 | Email pipeline (Phase 1)
Wrote `entities/email-pipeline.md`, `entities/notifications.md`,
`entities/check-setup.md`, `entities/zillow-email-import.md`.

## [2026-08-24] wave-1 | Browser-scan pipelines
Wrote `entities/browser-scan-streeteasy.md`, `entities/browser-scan-zillow.md`,
`entities/browser-import.md`, `entities/github-workflows.md`.

## [2026-08-24] wave-1 | Webapp backend
Wrote `entities/webapp-app-and-deps.md`, `entities/feed-logic-and-ranking.md`,
`entities/scoring.md`, `entities/api-routes.md`.

## [2026-08-24] wave-1 | Frontend
Wrote `entities/frontend-app-shell.md`, `entities/frontend-listing-card.md`,
`entities/frontend-swipe-page.md`, `entities/frontend-matches-and-passed.md`,
`entities/frontend-listing-detail-and-leaderboard.md`, `entities/frontend-misc.md`.

## [2026-08-24] wave-2 | Concept synthesis
Wrote all 7 `concepts/*.md` pages from `DECISIONS.md`/`STATUS.md`/`CLAUDE.md`
plus the freshly-written wave-1 entity pages.

## [2026-08-24] final-assembly | Index, log, schema doc, and consistency fixes
Built `index.md` and this `log.md` from the wave manifests; wrote
`README.md` (the schema doc). Fixed two wave-1 pages whose H1 title was
literally the filename (`store.md`, `shared-config.md`) instead of a real
title. Converted all `[[wiki-link]]`-style links (used inconsistently by the
concepts-synthesis agent and two entity pages) to the standard relative
markdown links the template specified, resolving each against the real set
of entity/concept filenames rather than assuming they were correct. Also
found and fixed 10 entity pages (webapp-backend and frontend domains) whose
"Depends on/used by" and "Related concepts" sections were bare paths with
no `[label](...)` markdown link syntax at all - inert plain text, not
actual links, and invisible to a link-checker that only scans real link
syntax. Ran coverage/link/secrets checks after all fixes: 51/51 source
files covered, 0 real broken links, 0 orphan pages, 0 secret-field leaks.
