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
from datetime import UTC, datetime, timedelta

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

CREATE TABLE IF NOT EXISTS listing_category_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    user TEXT NOT NULL,
    category TEXT NOT NULL,
    score INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(listing_id, user, category)
);
CREATE INDEX IF NOT EXISTS idx_listing_category_ratings_listing
    ON listing_category_ratings(listing_id);

CREATE TABLE IF NOT EXISTS listing_swipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    user TEXT NOT NULL,
    direction TEXT NOT NULL,
    swiped_at TEXT NOT NULL,
    UNIQUE(listing_id, user)
);
CREATE INDEX IF NOT EXISTS idx_listing_swipes_listing ON listing_swipes(listing_id);
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
    ("hidden_reason", "TEXT"),  # only ever "off_market" now - see set_hidden's docstring
    # interested/interested_by/interested_at: unused leftovers from an earlier
    # shared-swipe-queue design, superseded by the per-user listing_swipes
    # table below. Left in place rather than dropped (SQLite can't cheaply
    # drop columns) - nothing reads or writes them anymore.
    ("interested", "INTEGER NOT NULL DEFAULT 0"),
    ("interested_by", "TEXT"),
    ("interested_at", "TEXT"),
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
                    datetime.now(UTC).isoformat(),
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
            row = conn.execute(
                "SELECT id FROM listings WHERE url = ?", (listing["url"],)
            ).fetchone()
            return row[0]

    _BACKFILLABLE_COLUMNS = [
        "address",
        "neighborhood",
        "price",
        "beds",
        "baths",
        "sqft",
        "listing_agent",
        "photo_url",
        "open_house_raw",
        "open_house_date",
        "available_date",
    ]

    def backfill_listing(self, url: str, fields: dict) -> bool:
        """Fills in currently-empty columns on an already-saved listing from
        a fresh scan of the same URL - never overwrites a column that
        already has a value. Used to resume scanning listings that were
        first saved without a photo/address (see needs_backfill_listings).
        Returns True if anything was actually filled in."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM listings WHERE url = ?", (url,)).fetchone()
            if row is None:
                return False

            set_clauses = []
            params: list = []
            for col in self._BACKFILLABLE_COLUMNS:
                new_val = fields.get(col)
                if new_val is not None and not row[col]:
                    set_clauses.append(f"{col} = ?")
                    params.append(new_val)

            if not set_clauses:
                return False
            if "address" in fields and not row["address"] and fields.get("address") is not None:
                set_clauses.append("normalized_address = ?")
                params.append(normalize_address(fields["address"]))

            params.append(url)
            conn.execute(f"UPDATE listings SET {', '.join(set_clauses)} WHERE url = ?", params)
            return True

    def set_rating(self, listing_id: int, user: str, rating: int) -> None:
        now = datetime.now(UTC).isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO listing_reactions (listing_id, user, rating, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(listing_id, user) DO UPDATE SET rating = ?, updated_at = ?""",
                (listing_id, user, rating, now, rating, now),
            )

    def set_comment(self, listing_id: int, user: str, comment: str) -> None:
        now = datetime.now(UTC).isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO listing_reactions (listing_id, user, comment, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(listing_id, user) DO UPDATE SET comment = ?, updated_at = ?""",
                (listing_id, user, comment, now, comment, now),
            )

    def set_hidden(
        self, listing_id: int, hidden: bool, by: str, reason: str = "off_market"
    ) -> None:
        """Hidden is shared, not per-user - a deliberate joint decision, made
        only from the Leaderboard to disqualify a matched listing (e.g. it
        went off the market), reversible via the Passed view's undo. This is
        NOT how a pre-match "no" is recorded - that's a personal, permanent
        swipe (see record_swipe) with no undo, independent per person."""
        with self._conn() as conn:
            conn.execute(
                """UPDATE listings
                   SET hidden = ?, hidden_by = ?, hidden_at = ?, hidden_reason = ?
                   WHERE id = ?""",
                (
                    1 if hidden else 0,
                    by if hidden else None,
                    datetime.now(UTC).isoformat() if hidden else None,
                    reason if hidden else None,
                    listing_id,
                ),
            )

    def record_swipe(self, listing_id: int, user: str, direction: str) -> None:
        """Personal, one-time, permanent - a listing swiped in either
        direction never reappears in that user's own swipe queue again.
        Whether it becomes a match depends only on what the *other* person
        does, independently (see feed_logic.match_status)."""
        now = datetime.now(UTC).isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO listing_swipes (listing_id, user, direction, swiped_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(listing_id, user) DO UPDATE SET direction = ?, swiped_at = ?""",
                (listing_id, user, direction, now, direction, now),
            )

    def all_swipes_for_listing(self, listing_id: int) -> dict[str, str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT user, direction FROM listing_swipes WHERE listing_id = ?",
                (listing_id,),
            ).fetchall()
        return dict(rows)

    def set_category_rating(self, listing_id: int, user: str, category: str, score: int) -> None:
        now = datetime.now(UTC).isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO listing_category_ratings
                       (listing_id, user, category, score, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(listing_id, user, category)
                       DO UPDATE SET score = ?, updated_at = ?""",
                (listing_id, user, category, score, now, score, now),
            )

    def get_category_ratings_for_listing(self, listing_id: int) -> dict[str, dict[str, int]]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT user, category, score
                   FROM listing_category_ratings WHERE listing_id = ?""",
                (listing_id,),
            ).fetchall()
        result: dict[str, dict[str, int]] = {}
        for user, category, score in rows:
            result.setdefault(user, {})[category] = score
        return result

    def needs_backfill_listings(self) -> list[dict]:
        """Listings missing a photo or address - candidates for the next
        browser scan to re-visit and backfill, rather than re-scraping
        everything from scratch each time."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT * FROM listings
                   WHERE photo_url IS NULL OR photo_url = ''
                      OR address IS NULL OR address = ''
                   ORDER BY first_seen DESC"""
            ).fetchall()
        return [dict(row) for row in rows]

    def get_reactions_for_listing(self, listing_id: int) -> dict[str, dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT user, rating, comment, updated_at
                   FROM listing_reactions WHERE listing_id = ?""",
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

    def set_ai_score(
        self, listing_id: int, score: int, reasoning: str | None, profile_version: str
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """UPDATE listings SET ai_score = ?, ai_reasoning = ?,
                   ai_scored_at = ?, ai_profile_version = ? WHERE id = ?""",
                (
                    score,
                    reasoning,
                    datetime.now(UTC).isoformat(),
                    profile_version,
                    listing_id,
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
        return self.stats_since(datetime.now(UTC) - timedelta(hours=24))
