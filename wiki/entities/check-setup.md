---
type: entity
source_files: [apt_agent/check_setup.py]
status: deprioritized
verified: 2026-08-24
tags: [email-pipeline, phase-1, deprioritized, diagnostics]
---

# check_setup (Phase 1 deploy-readiness diagnostic)

A standalone diagnostic script that checks the *actual* on-disk/in-config state of a local setup against Phase 1's deploy checklist (`STATUS.md`), rather than relying on memory of what's been done. Prints a pass/fail report covering Python dependencies, OAuth credential files, `config.yaml` customization, and git remote/`listings.db` presence. Belongs entirely to the deprioritized email pipeline - its own banner literally prints "Phase 1 setup check" - and has no equivalent for the webapp or Zillow-email paths.

## Key exports

- `check_setup.main()` - `python -m apt_agent.check_setup` (CLI) - runs every check below in sequence, printing a formatted report.
- `check_setup.check(label, passed, detail="")` - the shared pass/fail line-printer every other check function calls.
- `check_setup.check_packages()` - verifies each module in `REQUIRED_PACKAGES` importable (`googleapiclient`, `google.oauth2.credentials`, `google_auth_oauthlib.flow`, `bs4`, `yaml`, `dateutil`).
- `check_setup.check_credentials_file()` / `check_token_file()` - checks `credentials.json`/`token.json` exist in the working directory.
- `check_setup.check_config()` - loads `config.yaml`, verifies it exists, checks `notify.recipients`/`notify.from_address` aren't still one of `PLACEHOLDER_VALUES`, and reports whether `search.price_min`/`price_max` are set. Returns `(config_exists, config_looks_customized)`.
- `check_setup.check_listings_db()` - checks `listings.db` exists (normal for it to be absent pre-first-run).
- `check_setup.check_git_remote()` - checks `.git` exists and `git remote get-url origin` resolves.

## Depends on / used by

- [shared-config](../entities/shared-config.md)
- [email-pipeline](../entities/email-pipeline.md)

## Notes & gotchas

- Purely diagnostic/read-only - never mutates `config.yaml`, `listings.db`, or any credential file; safe to run at any time.
- Explicitly cannot check GitHub Secrets, Actions workflow run history, or each listing site's saved-search alert subscriptions (printed as a note at the end of `main()`) - those require manual verification via the GitHub Actions tab and each site's own settings.
- `PLACEHOLDER_VALUES` is a hardcoded set of example addresses (`you@example.com`, `cricket@example.com`, `apartment-agent@example.com`) used to detect an un-customized `config.yaml` - a real recipient/from-address that happens to match one of these strings would produce a false "still placeholder" warning, though this is unlikely in practice.
- Since Phase 1 is deprioritized (not removed), this script still works and still reflects real local state - it just isn't part of the active development loop anymore.

## Related concepts

- [the-two-pivots](../concepts/the-two-pivots.md)
- [dev-tooling-and-hosting](../concepts/dev-tooling-and-hosting.md)
