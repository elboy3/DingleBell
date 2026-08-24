---
type: entity
source_files: [webapp/app.py, webapp/deps.py, webapp/config.py]
status: active
verified: 2026-08-24
tags: [fastapi, backend, bootstrap, cors, identity]
---

# App bootstrap and shared dependencies

## Purpose

The FastAPI application bootstrap layer for the webapp backend: builds the `FastAPI` instance, configures CORS for the React dev server, and mounts the two route modules. `deps.py` provides the shared, lazily-constructed `ListingStore` singleton and cookie-based current-user resolution used by every route handler. `config.py` is a one-line wrapper so the webapp reads the exact same `config.yaml` loader as the rest of the project.

## Key exports

- `app` (`webapp/app.py`) - the `FastAPI` instance; CORS restricted to `http://localhost:5175` and `http://127.0.0.1:5175`, `allow_credentials=True`; mounts `api_identity.router` and `api_listings.router`
- `get_store()` (`deps.py`) - returns the single module-level `ListingStore` instance, constructing it on first call from `config.yaml`'s `storage.db_path`
- `get_current_user(request)` (`deps.py`) - reads the unsigned `user` cookie, returns it only if it's in `KNOWN_USERS`, else `None`
- `load_webapp_config(path="config.yaml")` (`config.py`) - thin wrapper around `apt_agent.main.load_config()`

## Depends on / used by

- [store](../entities/store.md)
- [api-routes](../entities/api-routes.md)
- [shared-config](../entities/shared-config.md)
- [frontend-app-shell](../entities/frontend-app-shell.md)

## Notes & gotchas

- CORS origins are hardcoded to `localhost:5175`/`127.0.0.1:5175` - the frontend and backend must be accessed via the **same hostname** (`localhost`, never mix with `127.0.0.1`), or the identity cookie set by `POST /api/whoami` silently won't be sent on later `fetch()` calls. This is `SameSite=Lax`'s cross-*site* rule treating different loopback hostnames as different sites - a real bug hit during development, not a hypothetical.
- `KNOWN_USERS` is imported into `deps.py` from `ranking.py`, not redefined here - it used to be independently duplicated in both files with the same value, a "landmine" where adding a third user to only one copy would silently break the other. Consolidated to `ranking.py` as the single source of truth.
- No passwords or signed sessions anywhere in this layer - deliberate, for exactly 2 known users where a tampered cookie's worst case is a misattributed rating, not a security exposure.
- `_store` is a plain module-level global, not a FastAPI dependency-injected singleton with lifecycle management - simplest thing that works for a single-process dev server.

## Related concepts

- [identity-and-data-model](../concepts/identity-and-data-model.md)
- [dev-tooling-and-hosting](../concepts/dev-tooling-and-hosting.md)
