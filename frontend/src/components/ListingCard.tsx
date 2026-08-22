import { Link } from "react-router-dom";
import type { Listing } from "../types";
import { Stars } from "./Stars";

interface Props {
  listing: Listing;
  user: string;
  onRate: (id: number, rating: number) => void;
  onHide: (id: number, hidden: boolean) => void;
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

  return (
    <div className="listing-card">
      <div className="listing-photo-wrap">
        {listing.photo_url ? (
          <img className="listing-photo" src={listing.photo_url} alt="" />
        ) : (
          <div className="listing-photo-placeholder">No photo yet - run a scan to get one</div>
        )}
        {listing.rank != null && <div className="rank-badge">#{listing.rank}</div>}
        {listing.price != null && <div className="price-badge">${listing.price.toLocaleString()}/mo</div>}
        {listing.ai_score != null && (
          <div className={`score-badge ${scoreClass}`}>{(listing.ai_score / 10).toFixed(1)}/10 match</div>
        )}
      </div>
      <div className="listing-body">
        <div className="listing-header">
          <Link to={`/listings/${listing.id}`} className="listing-address">
            {listing.address || listing.url}
          </Link>
          {listing.neighborhood && <span className="neighborhood">{listing.neighborhood}</span>}
        </div>
        <div className="listing-facts">
          {listing.beds != null && <span>{listing.beds} bed</span>}
          {listing.baths != null && <span>{listing.baths} bath</span>}
          {listing.sqft && <span>{listing.sqft} ft²</span>}
        </div>
        {listing.open_house_raw && <div className="open-house">{listing.open_house_raw}</div>}
        {listing.ai_reasoning && <span className="ai-reasoning">{listing.ai_reasoning}</span>}

        {Object.entries(listing.reactions || {}).map(
          ([u, r]) =>
            r.comment && (
              <div className="comment-preview" key={u}>
                <strong>{u[0].toUpperCase() + u.slice(1)}:</strong> {r.comment}
              </div>
            ),
        )}

        <div className="ratings">
          <div className="rating-row">
            Elliott{" "}
            <Stars
              value={listing.ratings.elliott}
              editable={user === "elliott"}
              onChange={(n) => onRate(listing.id, n)}
            />
          </div>
          <div className="rating-row">
            Madison{" "}
            <Stars
              value={listing.ratings.madison}
              editable={user === "madison"}
              onChange={(n) => onRate(listing.id, n)}
            />
          </div>
          {listing.label && <div className="rating-label">{listing.label}</div>}
        </div>

        <div className="card-actions">
          <Link to={`/listings/${listing.id}`}>Details / comment →</Link>
          <button onClick={() => onHide(listing.id, !listing.hidden)}>
            {listing.hidden ? "Unhide" : "Not interested"}
          </button>
        </div>
      </div>
    </div>
  );
}
