import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import type { Listing } from "../types";
import { ListingCard } from "../components/ListingCard";

export function ListingDetail({ user }: { user: string }) {
  const { id } = useParams();
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

  const onRate = async (listingId: number, rating: number) => {
    setListing((prev) =>
      prev && prev.id === listingId ? { ...prev, ratings: { ...prev.ratings, [user]: rating } } : prev,
    );
    await api.setRating(listingId, rating);
    load();
  };
  const onHide = async (listingId: number, hidden: boolean) => {
    await api.setHidden(listingId, hidden);
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
      <Link to="/" className="back-link">
        &larr; Back to feed
      </Link>

      <div className="listing-detail-card">
        <ListingCard listing={listing} user={user} onRate={onRate} onHide={onHide} />
      </div>

      {mapQuery && (
        <div className="map-embed">
          <iframe
            width="100%"
            height="260"
            style={{ border: 0 }}
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
            src={`https://maps.google.com/maps?q=${mapQuery}&output=embed`}
            title="Map"
          />
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

      <a href={listing.url} target="_blank" rel="noopener noreferrer" className="original-link">
        View original listing &rarr;
      </a>
    </div>
  );
}
