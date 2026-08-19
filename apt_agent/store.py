"""SQLite-backed dedup store for listings we've already alerted on.

Handles two layers of dedup:
  1. Exact URL match (the original, cheap check)
  2. Normalized-address match (catches the same unit cross-posted on
     multiple sites - StreetEasy + Zillow + RentHop often all carry the
     same listing with different URLs)
"""
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta


SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    address TEXT,
    normalized_address TEXT,
    price INTEGER,
    beds REAL,
    baths REAL,
    available_date TEXT,
    source TEXT,
    first_seen TEXT NOT NULL,
    alerted INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_normalized_address ON listings(normalized_address);
CREATE INDEX IF NOT EXISTS idx_first_seen ON listings(first_seen);
"""

# Common noise words that show up in listing titles/addresses but don't
# help identify the physical unit - stripped before comparing.
_NOISE_WORDS = re.compile(
    r"\b(apt|apartment|unit|for rent|rental|ny|new york|brooklyn|"
    r"no fee|noFee|\#)\b",
    re.IGNORECASE,
)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")

# Street-suffix abbreviations, unified before noise-stripping so
# "29 Joralemon St" and "29 Joralemon Street" normalize identically.
_STREET_ABBREVIATIONS = {
    r"\bst\b": "street",
    r"\bave\b": "avenue",
    r"\bblvd\b": "boulevard",
    r"\bdr\b": "drive",
    r"\brd\b": "road",
    r"\bpl\b": "place",
    r"\bln\b": "lane",
    r"\bct\b": "court",
}


def normalize_address(raw_address: str | None) -> str | None:
    """
    Best-effort normalization so '29 Joralemon St #GARDEN, Brooklyn, NY'
    and '29 Joralemon Street Garden Apt, Brooklyn' collapse to the same
    key. Expands common street-suffix abbreviations first, then strips
    noise words and punctuation. Still not perfect (unit numbering
    styles, typos, etc. can slip through) but catches the common
    cross-posting case.
    """
    if not raw_address:
        return None
    text = raw_address.lower()
    for pattern, replacement in _STREET_ABBREVIATIONS.items():
        text = re.sub(pattern, replacement, text)
    text = _NOISE_WORDS.sub(" ", text)
    text = _NON_ALNUM.sub("", text)
    return text or None


class ListingStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def already_seen(self, url: str) -> bool:
        with self._conn() as conn:
            row = conn.execute("SELECT 1 FROM listings WHERE url = ?", (url,)).fetchone()
            return row is not None

    def already_alerted_for_address(self, address: str | None) -> bool:
        """True if we've already sent an alert for this normalized address,
        regardless of which site/URL it came in on."""
        norm = normalize_address(address)
        if not norm:
            return False
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM listings WHERE normalized_address = ? AND alerted = 1",
                (norm,),
            ).fetchone()
            return row is not None

    def save(self, listing: dict, alerted: bool):
        """listing dict expects: url, address, price, beds, baths, available_date, source"""
        with self._conn() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO listings
                   (url, address, normalized_address, price, beds, baths,
                    available_date, source, first_seen, alerted)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    listing["url"],
                    listing.get("address"),
                    normalize_address(listing.get("address")),
                    listing.get("price"),
                    listing.get("beds"),
                    listing.get("baths"),
                    listing.get("available_date"),
                    listing.get("source"),
                    datetime.now(timezone.utc).isoformat(),
                    1 if alerted else 0,
                ),
            )

    def stats_since(self, since: datetime) -> dict:
        """Counts for the heartbeat email: total seen vs alerted since a given time."""
        with self._conn() as conn:
            seen = conn.execute(
                "SELECT COUNT(*) FROM listings WHERE first_seen >= ?",
                (since.isoformat(),),
            ).fetchone()[0]
            alerted = conn.execute(
                "SELECT COUNT(*) FROM listings WHERE first_seen >= ? AND alerted = 1",
                (since.isoformat(),),
            ).fetchone()[0]
        return {"seen": seen, "alerted": alerted}

    def stats_last_24h(self) -> dict:
        return self.stats_since(datetime.now(timezone.utc) - timedelta(hours=24))
