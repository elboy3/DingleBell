"""
Sends one daily summary email so you always know the agent is alive -
even on days with zero matches, silence would otherwise be ambiguous
between "nothing new" and "something broke quietly."

Run once/day via a separate scheduled workflow (see
.github/workflows/heartbeat.yml) or manually:

    python -m apt_agent.heartbeat
"""
from .main import load_config
from .store import ListingStore
from .notify import send_alert


def build_heartbeat_listing(stats: dict) -> dict:
    """Reuses the same send_alert()/email-building path as a real
    listing alert, just with heartbeat-shaped content instead."""
    return {
        "url": "(heartbeat - no listing, this is a status check-in)",
        "address": f"Last 24h: {stats['seen']} listing(s) seen, {stats['alerted']} alert(s) sent",
        "price": None,
        "beds": None,
        "baths": None,
        "available_date": None,
        "source": "heartbeat",
    }


def main():
    cfg = load_config()
    store = ListingStore(cfg["storage"]["db_path"])
    stats = store.stats_last_24h()

    listing = build_heartbeat_listing(stats)
    send_alert(listing, cfg["notify"])
    print(f"Heartbeat sent: {stats}")


if __name__ == "__main__":
    main()
