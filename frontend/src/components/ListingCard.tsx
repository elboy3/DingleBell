import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { CATEGORIES } from "../categories";
import type { Listing } from "../types";
import { Stars } from "./Stars";

type DetailLevel = "minimal" | "summary" | "full";
type SwipeDirection = "left" | "right";

interface Props {
  listing: Listing;
  user: string;
  onCategoryRate: (id: number, category: string, score: number) => void;
  /** minimal: the Swipe page - photo/price/facts/AI score only, no ratings
   * or category detail, so a fast yes/no decision isn't cluttered.
   * summary (default): Inbox/Passed/Needs Scan/Leaderboard grids - adds
   * the two people's overall rating, but still no category panel/comments.
   * full: the listing's own detail page - everything, including the
   * category-rating panel (the only place it's editable). */
  detailLevel?: DetailLevel;
  /** On the listing's own detail page, the title should open the original
   * StreetEasy listing instead of linking to the page you're already on,
   * and the "Details / comment" footer link (which would point right
   * back here) is redundant and gets skipped. */
  linkExternally?: boolean;
  /** Swipe page only: big Pass/Interested buttons plus a bidirectional drag
   * gesture. Swiping is personal and permanent - there's no "unhide" once
   * you've decided, unlike the old shared-hide model, so this card renders
   * no hide/unhide affordance anywhere else. */
  swipeDecide?: boolean;
  onSwipe?: (id: number, direction: SwipeDirection) => void;
  /** Leaderboard only: disqualify a matched listing (e.g. it went off the
   * market) - a shared, reversible action, distinct from a personal swipe. */
  onDisqualify?: (id: number) => void;
}

const NEW_WINDOW_MS = 3 * 24 * 60 * 60 * 1000; // "new" for 3 days after first_seen
const SWIPE_THRESHOLD = 90; // px of horizontal drag before a release commits a decision

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

export function ListingCard({
  listing,
  user,
  onCategoryRate,
  detailLevel = "summary",
  linkExternally = false,
  swipeDecide = false,
  onSwipe,
  onDisqualify,
}: Props) {
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
    if (!swipeDecide) return;
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
      onSwipe?.(listing.id, "left");
    } else if (dragX > SWIPE_THRESHOLD) {
      onSwipe?.(listing.id, "right");
    }
    draggingRef.current = false;
    setDragX(0);
  };

  return (
    <div className="listing-card">
      <div
        className={`listing-photo-wrap ${swipeDecide ? "swipeable" : ""}`}
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
        {swipeDecide && dragX < -20 && (
          <div className="pass-stamp" style={{ opacity: Math.min(1, -dragX / SWIPE_THRESHOLD) }}>
            PASS
          </div>
        )}
        {swipeDecide && dragX > 20 && (
          <div
            className="interested-stamp"
            style={{ opacity: Math.min(1, dragX / SWIPE_THRESHOLD) }}
          >
            YES
          </div>
        )}
      </div>
      <div className="listing-body">
        <div className="listing-header">
          {linkExternally ? (
            <a
              href={listing.url}
              target="_blank"
              rel="noopener noreferrer"
              className="listing-address"
            >
              {title} <span className="external-icon">↗</span>
            </a>
          ) : (
            <Link to={`/listings/${listing.id}`} className="listing-address">
              {title}
            </Link>
          )}
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
            {detailLevel !== "minimal" && listing.ai_reasoning && (
              <span className="ai-reasoning">{listing.ai_reasoning}</span>
            )}
          </div>
        )}

        {detailLevel !== "minimal" && (
          <div className="ratings">
            <RatingReadout label="Elliott" value={listing.ratings.elliott} />
            <RatingReadout label="Madison" value={listing.ratings.madison} />
            {listing.label && <div className="rating-label">{listing.label}</div>}
          </div>
        )}

        {detailLevel === "full" && (
          <>
            <button type="button" className="rate-toggle" onClick={() => setShowCategories((v) => !v)}>
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
          </>
        )}

        {swipeDecide && (
          <div className="swipe-buttons">
            <button type="button" className="swipe-pass" onClick={() => onSwipe?.(listing.id, "left")}>
              ✕ Pass
            </button>
            <button
              type="button"
              className="swipe-interested"
              onClick={() => onSwipe?.(listing.id, "right")}
            >
              ✓ Interested
            </button>
          </div>
        )}

        {onDisqualify && (
          <button type="button" className="disqualify-link" onClick={() => onDisqualify(listing.id)}>
            Off market / disqualify
          </button>
        )}

        {!linkExternally && !swipeDecide && (
          <div className="card-actions">
            <Link to={`/listings/${listing.id}`}>Details / comment →</Link>
          </div>
        )}
      </div>
    </div>
  );
}
