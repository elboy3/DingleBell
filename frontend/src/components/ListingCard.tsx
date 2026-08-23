import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { CATEGORIES } from "../categories";
import type { Listing } from "../types";
import { Stars } from "./Stars";

interface Props {
  listing: Listing;
  user: string;
  onHide: (id: number, hidden: boolean) => void;
  onCategoryRate: (id: number, category: string, score: number) => void;
}

const NEW_WINDOW_MS = 3 * 24 * 60 * 60 * 1000; // "new" for 3 days after first_seen
const SWIPE_THRESHOLD = 90; // px of horizontal drag before a release counts as "pass"

function RatingReadout({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rating-row rating-compact">
      {label}{" "}
      {value != null ? (
        <>
          <span className="star-icon">★</span> {value}
        </>
      ) : (
        <span className="rating-label">not yet rated</span>
      )}
    </div>
  );
}

export function ListingCard({ listing, user, onHide, onCategoryRate }: Props) {
  const [showCategories, setShowCategories] = useState(false);
  const [dragX, setDragX] = useState(0);
  const draggingRef = useRef(false);
  const startXRef = useRef(0);

  const scoreClass =
    listing.ai_score == null
      ? ""
      : listing.ai_score >= 70
        ? "score-high"
        : listing.ai_score >= 40
          ? "score-mid"
          : "score-low";

  const isNew =
    listing.first_seen && Date.now() - new Date(listing.first_seen).getTime() < NEW_WINDOW_MS;
  const title = listing.address || `Listing #${listing.id}`;
  const myCategories = listing.category_ratings?.[user] || {};

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    draggingRef.current = true;
    startXRef.current = e.clientX;
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!draggingRef.current) return;
    setDragX(e.clientX - startXRef.current);
  };
  const commitDrag = () => {
    if (!draggingRef.current) return;
    if (dragX < -SWIPE_THRESHOLD) {
      onHide(listing.id, true);
    }
    draggingRef.current = false;
    setDragX(0);
  };

  return (
    <div className="listing-card">
      <div
        className="listing-photo-wrap"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={commitDrag}
        onPointerCancel={commitDrag}
        style={
          dragX
            ? { transform: `translateX(${dragX}px) rotate(${dragX / 22}deg)`, transition: "none" }
            : undefined
        }
      >
        {listing.photo_url ? (
          <img className="listing-photo" src={listing.photo_url} alt="" draggable={false} />
        ) : (
          <div className="listing-photo-placeholder">No photo yet - run a scan to get one</div>
        )}
        {listing.rank != null && <div className="rank-badge">#{listing.rank}</div>}
        {dragX < -20 && (
          <div
            className="pass-stamp"
            style={{ opacity: Math.min(1, -dragX / SWIPE_THRESHOLD) }}
          >
            PASS
          </div>
        )}
        <button
          type="button"
          className={`cricket-button ${listing.hidden ? "hidden-state" : ""}`}
          onPointerDown={(e) => e.stopPropagation()}
          onClick={() => onHide(listing.id, !listing.hidden)}
          aria-label={listing.hidden ? "Unhide - bring back into the feed" : "Not interested - hide this listing"}
          title={listing.hidden ? "Unhide" : "Not interested (or swipe the photo left)"}
        >
          🦗
        </button>
      </div>
      <div className="listing-body">
        <div className="listing-header">
          <Link to={`/listings/${listing.id}`} className="listing-address">
            {title}
          </Link>
        </div>
        <div className="header-tags">
          {isNew && <span className="new-badge">New</span>}
          {listing.needs_backfill && <span className="backfill-badge">Needs scan</span>}
          {listing.neighborhood && <span className="neighborhood">{listing.neighborhood}</span>}
        </div>
        {listing.price != null && (
          <div className="price-line">
            ${listing.price.toLocaleString()} <span>/mo</span>
          </div>
        )}
        <div className="listing-facts">
          {listing.beds != null && <span>{listing.beds} bed</span>}
          {listing.baths != null && <span>{listing.baths} bath</span>}
          {listing.sqft && <span>{listing.sqft} ft²</span>}
        </div>
        {listing.open_house_raw && <div className="open-house">{listing.open_house_raw}</div>}
        {listing.ai_score != null && (
          <div className="ai-score-line">
            <span className={`score-pill ${scoreClass}`}>{(listing.ai_score / 10).toFixed(1)}/10 match</span>
            {listing.ai_reasoning && <span className="ai-reasoning">{listing.ai_reasoning}</span>}
          </div>
        )}

        {Object.entries(listing.reactions || {}).map(
          ([u, r]) =>
            r.comment && (
              <div className="comment-preview" key={u}>
                <strong>{u[0].toUpperCase() + u.slice(1)}:</strong> {r.comment}
              </div>
            ),
        )}

        <div className="ratings">
          <RatingReadout label="Elliott" value={listing.ratings.elliott} />
          <RatingReadout label="Madison" value={listing.ratings.madison} />
          {listing.label && <div className="rating-label">{listing.label}</div>}
        </div>

        <button
          type="button"
          className="rate-toggle"
          onClick={() => setShowCategories((v) => !v)}
        >
          {showCategories ? "Hide category ratings ▲" : "Like it? Rate by category ▾"}
        </button>
        {showCategories && (
          <div className="category-panel">
            {CATEGORIES.map((c) => (
              <div className="category-row" key={c.key}>
                <span>{c.label}</span>
                <Stars
                  value={myCategories[c.key] ?? null}
                  editable
                  onChange={(n) => onCategoryRate(listing.id, c.key, n)}
                />
              </div>
            ))}
          </div>
        )}

        <div className="card-actions">
          <Link to={`/listings/${listing.id}`}>Details / comment →</Link>
        </div>
      </div>
    </div>
  );
}
