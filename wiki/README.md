# wiki/ - the schema doc

This directory is an LLM-maintained documentation wiki for the `dingle` repo,
adapting the three-layer pattern from
[Karpathy's gist on LLM-maintained personal wikis](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
to a codebase instead of a personal knowledge base. This file is the
"schema" layer: it tells any future session (human or LLM) how the wiki is
structured and how to keep it accurate as the code changes.

## Structure

- `wiki/entities/*.md` - one page per source file, or per tight sibling
  group of small/coupled files. Describes what a piece of code *is*.
- `wiki/concepts/*.md` - one page per cross-cutting theme (a design
  decision, a pivot, a technique that evolved over time). Describes *why*
  things are the way they are, and links to the entity pages that
  implement it.
- `wiki/index.md` - catalog of every page, one line each, grouped by area.
  Update this whenever a page is added, removed, or renamed.
- `wiki/log.md` - append-only record of wiki-authoring operations (not
  code changes themselves - see "Relationship to existing docs" below).

## Page templates

**Entity page**, required frontmatter:
```yaml
---
type: entity
source_files: [apt_agent/store.py]   # exact relative repo paths
status: active | deprioritized | superseded
verified: 2026-08-24                  # date this page was last checked against its source
tags: [kebab-case, tags]
---
```
Sections: **Purpose** (one paragraph) / **Key exports** (bullet list) /
**Depends on / used by** (bullet list of links *only* to other wiki pages -
no prose here, so a link-checker can be exhaustive rather than sampling) /
**Notes & gotchas** (real invariants/caveats pulled from the actual code -
never invented) / **Related concepts** (links).

`store.md` is the one deliberate exception: because `apt_agent/store.py` is
the largest, most central, most cross-referenced file in the repo, it uses
four mandated subheadings instead of a generic "Key exports" - Schema/
migrations, Write API, Query/read API, Dedup logic. Extend this exception to
any future file that plays a similarly central role, rather than forcing it
into the generic template.

**Concept page**, required frontmatter: same `type`/`status`/`verified`/
`tags` shape (`type: concept`). Sections: **Summary** (one paragraph) /
**Details** (the substance) / **Related entities** (links only) /
**Sources** (which doc/section this was derived from).

**Links** are always standard relative markdown links
(`[label](../entities/name.md)` or `[label](name.md)` from within the same
directory) - never `[[Obsidian-style]]` double-bracket links. This wiki is
meant to render correctly on GitHub and in any plain markdown viewer, not
just Obsidian.

## Maintenance workflow (read this before changing code)

When a future session makes a meaningful change to a file that has an
entity page:
1. Update that entity page's content and bump its `verified:` date.
2. If the change affects a concept page's story (e.g. a new ingestion
   technique, a new design decision), update that concept page too - don't
   let entity and concept pages describe the same fact two different ways.
3. If a page was added, removed, or renamed, update `index.md`.
4. Append one entry to `log.md` describing what changed and why, in the
   format `## [DATE] operation | description`.

This mirrors the gist's "ingest" workflow, adapted from "a new source
arrived" to "the code changed."

**Periodic lint pass** (do this occasionally, not after every change): look
for pages whose `verified:` date predates their `source_files`' last git
change (a mechanical check: `git log -1 --format=%ad -- <path>` per file),
pages with no inbound links from `index.md` or any other page (orphans), and
places where an entity page and a concept page describe the same underlying
fact in subtly different words (a contradiction) - fix by making the concept
page link to and summarize the entity page rather than restate it.

## Relationship to existing docs

This repo already had `CLAUDE.md` (onboarding + a "File map"/"Architecture
summary"), `DECISIONS.md` (append-only why-level decision log), `STATUS.md`
(live checklist), `ROADMAP.md`, and `README.md` before this wiki existed.
Those are this wiki's **raw sources**, not superseded by it:

- `DECISIONS.md` stays the place for **why** something was decided and the
  narrative history around it - this wiki's concept pages summarize and
  link to it, they don't replace it.
- `STATUS.md` stays the live, owner-tagged checklist of concrete next
  actions - not the wiki's job.
- `wiki/log.md` logs **wiki-authoring operations only** (when a page was
  written or updated) - it is explicitly not a substitute for
  `DECISIONS.md`'s decision history or `STATUS.md`'s own status log.
- `CLAUDE.md`'s "File map" section has been replaced with a pointer to
  `wiki/index.md` (see that file) specifically to avoid two
  independently-maintained catalogs of "what does this file do" drifting
  apart - update `wiki/`, not a file map inside `CLAUDE.md`, when files
  change.

## What this wiki deliberately does not do

Karpathy's gist describes several features aimed at much larger corpora
(100+ sources, multiple contributors ingesting concurrently, multiple
audiences). None of those apply at this repo's size (~35 source files, one
git history), so none are implemented here:

- **No full-text search (BM25) index** - `index.md` alone is enough to
  navigate ~27 pages. Revisit if the wiki grows past ~100 pages.
- **No placeholder-locking for concurrent page-name claims** - this wiki was
  built with strict non-overlapping file ownership per contributing agent
  instead, which is simpler and sufficient at this scale.
- **No audience-separated wikis** - there is one wiki, for whoever is
  working on this repo (human or LLM), not multiple visibility tiers.
- **No "pins" system for human corrections surviving regeneration** - pages
  aren't regenerated wholesale; they're edited in place per the maintenance
  workflow above.

## Verification performed on the initial build

Coverage (every repo source file maps to an entity page's `source_files`),
bidirectional link-checking (every link target exists; every page is
reachable from `index.md`), a secrets grep (`credentials.json`/`token.json`/
`listings.db` contents never appear in any page), and a cross-page
contradiction pass between concept pages and the entity pages they
reference. See `log.md` for what was found and fixed.
