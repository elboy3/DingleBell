"""SQLite-backed store for every listing we've seen (email pipeline or
browser scan), plus per-user reactions (rating/comment) and shared
hide/AI-score state used by the webapp.

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

CREATE TABLE IF NOT EXISTS listing_reactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    user TEXT NOT NULL,
    rating INTEGER,
    comment TEXT,
    updated_at TEXT NOT NULL,
    UNIQUE(listing_id, user)
);
CREATE INDEX IF NOT EXISTS idx_listing_reactions_listing ON listing_reactions(listing_id);
"""

# Columns added after the initial schema above - kept as a migration list
# (rather than folding into SCHEMA) since existing listings.db files
# already committed to the repo need ALTER TABLE, not CREATE TABLE.
_MIGRATIONS = [
    ("neighborhood", "TEXT"),
    ("sqft", "INTEGER"),
    ("listing_agent", "TEXT"),
    ("photo_url", "TEXT"),
    ("open_house_raw", "TEXT"),
    ("open_house_date", "TEXT"),
    ("ai_score", "INTEGER"),
    ("ai_reasoning", "TEXT"),
    ("ai_scored_at", "TEXT"),
    ("ai_profile_version", "TEXT"),
    ("hidden", "INTEGER NOT NULL DEFAULT 0"),
    ("hidden_by", "TEXT"),
    ("hidden_at", "TEXT"),
]

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
            existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(listings)")}
            for col, col_type in _MIGRATIONS:
                if col not in existing_cols:
                    conn.execute(f"ALTER TABLE listings ADD COLUMN {col} {col_type}")

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

    def save(self, listing: dict, alerted: bool) -> int:
        """listing dict expects: url, address, price, beds, baths, available_date,
        source, and optionally neighborhood, sqft, listing_agent, photo_url,
        open_house_raw, open_house_date - all of the optional fields are only
        ever populated via a browser-sourced scan (see browser_import.py),
        not the email pipeline. Returns the row id (existing row's id if this
        url was already present, since INSERT OR IGNORE is a no-op then)."""
        with self._conn() as conn:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO listings
                   (url, address, normalized_address, price, beds, baths,
                    available_date, source, first_seen, alerted,
                    neighborhood, sqft, listing_agent, photo_url,
                    open_house_raw, open_house_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                    listing.get("neighborhood"),
                    listing.get("sqft"),
                    listing.get("listing_agent"),
                    listing.get("photo_url"),
                    listing.get("open_house_raw"),
                    listing.get("open_house_date"),
                ),
            )
            if cursor.lastrowid and cursor.rowcount:
                return cursor.lastrowid
            row = conn.execute("SELECT id FROM listings WHERE url = ?", (listing["url"],)).fetchone()
            return row[0]

    def set_rating(self, listing_id: int, user: str, rating: int) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO listing_reactions (listing_id, user, rating, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(listing_id, user) DO UPDATE SET rating = ?, updated_at = ?""",
                (listing_id, user, rating, datetime.now(timezone.utc).isoformat(),
                 rating, datetime.now(timezone.utc).isoformat()),
            )

    def set_comment(self, listing_id: int, user: str, comment: str) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO listing_reactions (listing_id, user, comment, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(listing_id, user) DO UPDATE SET comment = ?, updated_at = ?""",
                (listing_id, user, comment, datetime.now(timezone.utc).isoformat(),
                 comment, datetime.now(timezone.utc).isoformat()),
            )

    def set_hidden(self, listing_id: int, hidden: bool, by: str) -> None:
        """Hidden is shared, not per-user - a deliberate joint decision that
        removes a listing from both feeds, reversible via the /hidden view."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE listings SET hidden = ?, hidden_by = ?, hidden_at = ? WHERE id = ?",
                (1 if hidden else 0, by if hidden else None,
                 datetime.now(timezone.utc).isoformat() if hidden else None, listing_id),
            )

    def get_reactions_for_listing(self, listing_id: int) -> dict[str, dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT user, rating, comment, updated_at FROM listing_reactions WHERE listing_id = ?",
                (listing_id,),
            ).fetchall()
        return {
            user: {"rating": rating, "comment": comment, "updated_at": updated_at}
            for user, rating, comment, updated_at in rows
        }

    def all_listings(self, include_hidden: bool = False) -> list[dict]:
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM listings"
            if not include_hidden:
                query += " WHERE hidden = 0"
            query += " ORDER BY first_seen DESC"
            rows = conn.execute(query).fetchall()
        return [dict(row) for row in rows]

    def set_ai_score(self, listing_id: int, score: int, reasoning: str, profile_version: str) -> None:
        with self._conn() as conn:
            conn.execute(
                """UPDATE listings SET ai_score = ?, ai_reasoning = ?,
                   ai_scored_at = ?, ai_profile_version = ? WHERE id = ?""",
                (score, reasoning, datetime.now(timezone.utc).isoformat(), profile_version, listing_id),
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
