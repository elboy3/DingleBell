import { Link } from "react-router-dom";
import type { Listing } from "../types";
import { Stars } from "./Stars";

interface Props {
  listing: Listing;
  user: string;
  onRate: (id: number, rating: number) => void;
  onHide: (id: number, hidden: boolean) => void;
}

const NEW_WINDOW_MS = 3 * 24 * 60 * 60 * 1000; // "new" for 3 days after first_seen

function RatingDisplay({
  label,
  viewer,
  targetUser,
  listingId,
  value,
  onRate,
}: {
  label: string;
  viewer: string;
  targetUser: string;
  listingId: number;
  value: number | null;
  onRate: (id: number, rating: number) => void;
}) {
  if (viewer === targetUser) {
    return (
      <div className="rating-row">
        {label} <Stars value={value} editable onChange={(n) => onRate(listingId, n)} />
      </div>
    );
  }
  // The other person's rating is read-only - Airbnb-style compact "★ N"
  // instead of a full 5-star row, since it's just informational here.
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

export function ListingCard({ listing, user, onRate, onHide }: Props) {
  const scoreClass =
    listing.ai_score == null
      ? ""
      : listing.ai_score >= 70
        ? "score-high"
        : listing.ai_score >= 40
          ? "score-mid"
          : "score-low";

  const isNew = listing.first_seen && Date.now() - new Date(listing.first_seen).getTime() < NEW_WINDOW_MS;

  return (
    <div className="listing-card">
      <div className="listing-photo-wrap">
        {listing.photo_url ? (
          <img className="listing-photo" src={listing.photo_url} alt="" />
        ) : (
          <div className="listing-photo-placeholder">No photo yet - run a scan to get one</div>
        )}
        {listing.rank != null && <div className="rank-badge">#{listing.rank}</div>}
        <button
          type="button"
          className={`heart-button ${listing.hidden ? "hidden-state" : ""}`}
          onClick={() => onHide(listing.id, !listing.hidden)}
          aria-label={listing.hidden ? "Unhide - bring back into the feed" : "Not interested - hide this listing"}
          title={listing.hidden ? "Unhide" : "Not interested"}
        >
          <span className={listing.hidden ? "" : "heart-fill"}>{listing.hidden ? "♡" : "♥"}</span>
        </button>
      </div>
      <div className="listing-body">
        <div className="listing-header">
          <Link to={`/listings/${listing.id}`} className="listing-address">
            {listing.address || listing.url}
          </Link>
        </div>
        <div className="header-tags">
          {isNew && <span className="new-badge">New</span>}
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
          <RatingDisplay
            label="Elliott"
            viewer={user}
            targetUser="elliott"
            listingId={listing.id}
            value={listing.ratings.elliott}
            onRate={onRate}
          />
          <RatingDisplay
            label="Madison"
            viewer={user}
            targetUser="madison"
            listingId={listing.id}
            value={listing.ratings.madison}
            onRate={onRate}
          />
          {listing.label && <div className="rating-label">{listing.label}</div>}
        </div>

        <div className="card-actions">
          <Link to={`/listings/${listing.id}`}>Details / comment →</Link>
        </div>
      </div>
    </div>
  );
}
