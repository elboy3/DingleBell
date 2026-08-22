"""
Backfills AI taste-match scores for listings that don't have one yet, or
whose score was computed against a since-revised taste profile. A manual
command is enough at this scale - not worth automating.

    python -m webapp.rescore
"""
import os

from apt_agent.store import ListingStore

from .config import load_webapp_config
from .scoring import score_listing


def main():
    cfg = load_webapp_config()
    scoring_cfg = cfg.get("scoring") or {}
    profile_path = scoring_cfg.get("profile_path")
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not profile_path or not os.path.exists(profile_path):
        print(f"[error] no taste profile at {profile_path!r} - nothing to rescore against")
        return
    if not api_key:
        print("[error] ANTHROPIC_API_KEY not set")
        return

    with open(profile_path) as f:
        taste_profile = f.read()

    profile_version = scoring_cfg["profile_version"]
    store = ListingStore(cfg["storage"]["db_path"])

    stale = [
        listing for listing in store.all_listings(include_hidden=True)
        if listing["ai_score"] is None or listing["ai_profile_version"] != profile_version
    ]
    print(f"{len(stale)} listing(s) need (re)scoring against profile version {profile_version!r}")

    scored = 0
    for listing in stale:
        score, reasoning = score_listing(listing, taste_profile, api_key)
        label = listing["address"] or listing["url"]
        if score is not None:
            store.set_ai_score(listing["id"], score, reasoning, profile_version)
            scored += 1
            print(f"  [{score}/100] {label}")
        else:
            print(f"  [skip - no score] {label}")

    print(f"Done. {scored}/{len(stale)} scored.")


if __name__ == "__main__":
    main()
