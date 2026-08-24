import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { CATEGORIES } from "../categories";
import type { Listing } from "../types";
import { ListingCard } from "../components/ListingCard";

export function ListingDetail({ user }: { user: string }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [listing, setListing] = useState<Listing | null>(null);
  const [commentDraft, setCommentDraft] = useState("");

  const load = async () => {
    const data = await api.listing(Number(id));
    setListing(data);
    setCommentDraft(data.reactions[user]?.comment || "");
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    load();
  }, [id]);

  const onCategoryRate = async (listingId: number, category: string, score: number) => {
    await api.setCategoryRating(listingId, category, score);
    load();
  };
  const saveComment = async () => {
    await api.setComment(Number(id), commentDraft);
    load();
  };

  if (!listing) return <p className="empty">Loading...</p>;

  const mapQuery = listing.address
    ? encodeURIComponent(`${listing.address}, ${listing.neighborhood || ""} Brooklyn, NY`)
    : null;

  return (
    <div>
      <button type="button" onClick={() => navigate(-1)} className="back-link">
        &larr; Back
      </button>

      <div className="detail-layout">
        <div className="listing-detail-card">
          <ListingCard
            listing={listing}
            user={user}
            onCategoryRate={onCategoryRate}
            detailLevel="full"
            linkExternally
          />
        </div>

        <div className="detail-side">
          <a href={listing.url} target="_blank" rel="noopener noreferrer" className="streeteasy-cta">
            View on StreetEasy ↗
          </a>
          {mapQuery && (
            <div className="map-embed">
              <iframe
                width="100%"
                height="320"
                style={{ border: 0 }}
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
                src={`https://maps.google.com/maps?q=${mapQuery}&output=embed`}
                title="Map"
              />
            </div>
          )}
        </div>
      </div>

      {(listing.category_ratings.elliott || listing.category_ratings.madison) && (
        <div className="category-breakdown">
          <h3>Category ratings</h3>
          <table>
            <thead>
              <tr>
                <th></th>
                <th>Elliott</th>
                <th>Madison</th>
              </tr>
            </thead>
            <tbody>
              {CATEGORIES.map((c) => (
                <tr key={c.key}>
                  <td>{c.label}</td>
                  <td>{listing.category_ratings.elliott?.[c.key] ?? "-"}</td>
                  <td>{listing.category_ratings.madison?.[c.key] ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h3>Comments</h3>
      {Object.entries(listing.reactions).map(
        ([u, r]) =>
          r.comment && (
            <div className="comment" key={u}>
              <strong>{u[0].toUpperCase() + u.slice(1)}:</strong> {r.comment}
            </div>
          ),
      )}

      <div className="comment-form">
        <textarea
          value={commentDraft}
          onChange={(e) => setCommentDraft(e.target.value)}
          placeholder="Leave a note..."
        />
        <button onClick={saveComment}>Save comment</button>
      </div>
    </div>
  );
}
