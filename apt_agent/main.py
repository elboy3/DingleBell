"""
Entry point. Run this on a schedule (cron / systemd timer / launchd,
or the GitHub Actions workflow in .github/workflows/poll.yml).

    python -m apt_agent.main            # normal run
    python -m apt_agent.main --dry-run  # inject one fake listing to test
                                         # the full pipeline end-to-end,
                                         # without waiting for a real alert

Flow per run:
  1. Pull new alert emails from Gmail -> extract listing URLs
  2. Skip URLs already in the dedup DB
  3. Fetch + parse each new listing page (best-effort)
  4. Apply hard filters (price / beds / baths / move-in window)
  5. Skip if we've already alerted on this address from a different site
  6. Save to DB, send email alert on every listing that passes
"""
import argparse
import os
import sys
import yaml

from .gmail_ingest import fetch_new_alert_urls
from .listing_parser import fetch_listing_page, parse_listing_html
from .filters import passes_filters
from .store import ListingStore
from .notify import send_alert

DRY_RUN_LISTING = {
    "url": "https://example.com/dry-run-test-listing",
    "address": "123 Test Street, Brooklyn, NY (DRY RUN)",
    "price": 4000,
    "beds": 2.0,
    "baths": 1.0,
    "available_date": "available now",
    "source": "dry-run",
}


def load_config(path: str = "config.yaml") -> dict:
    """
    Load config.yaml, then apply env var overrides for anything that
    shouldn't sit in plaintext in a public repo (recipient emails, the
    sending address). Falls back to config.yaml values if the env vars
    aren't set - so this works unchanged for local runs.

      NOTIFY_RECIPIENTS   comma-separated list, e.g. "a@x.com,b@x.com"
      NOTIFY_FROM_ADDRESS single address
    """
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)

    env_recipients = os.environ.get("NOTIFY_RECIPIENTS")
    if env_recipients:
        cfg["notify"]["recipients"] = [r.strip() for r in env_recipients.split(",") if r.strip()]

    env_from = os.environ.get("NOTIFY_FROM_ADDRESS")
    if env_from:
        cfg["notify"]["from_address"] = env_from

    return cfg


def process_listing(listing: dict, cfg: dict, store: ListingStore) -> bool:
    """Runs filters + address dedup + save + alert for one listing dict.
    Returns True if an alert was sent."""
    ok, reason = passes_filters(listing, cfg)

    if ok and store.already_alerted_for_address(listing.get("address")):
        ok = False
        reason = "already alerted on this address from another source"

    store.save(listing, alerted=ok)

    if ok:
        send_alert(listing, cfg["notify"])
        print(f"[alert sent] {listing['url']}")
        return True
    else:
        print(f"[filtered out] {listing['url']} - {reason}")
        return False


def run_once(cfg: dict) -> int:
    store = ListingStore(cfg["storage"]["db_path"])

    urls = fetch_new_alert_urls(cfg["gmail"]["label_or_query"])
    alert_count = 0

    for url in urls:
        if store.already_seen(url):
            continue

        html = fetch_listing_page(url)
        if html is None:
            print(f"[skip] could not fetch {url}", file=sys.stderr)
            continue

        listing = parse_listing_html(html, url)
        if process_listing(listing, cfg, store):
            alert_count += 1

    return alert_count


def run_dry_run(cfg: dict) -> int:
    """Pushes one obviously-fake listing through filters + alert email,
    bypassing Gmail entirely. Use this to confirm OAuth, filters, and
    email delivery all work before waiting on a real alert."""
    store = ListingStore(cfg["storage"]["db_path"])
    # dry run always alerts regardless of filters, so you actually see
    # the test email land in your inbox
    send_alert(DRY_RUN_LISTING, cfg["notify"])
    print(f"[dry run] test alert sent to {cfg['notify']['recipients']}")
    return 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="send one fake test alert and exit")
    args = parser.parse_args()

    cfg = load_config()

    if args.dry_run:
        sent = run_dry_run(cfg)
    else:
        sent = run_once(cfg)

    print(f"Done. {sent} alert(s) sent.")


if __name__ == "__main__":
    main()
