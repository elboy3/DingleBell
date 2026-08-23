import { useEffect, useState } from "react";
import { api } from "../api";
import type { Listing } from "../types";
import { ListingCard } from "../components/ListingCard";

export function Hidden({ user }: { user: string }) {
  const [listings, setListings] = useState<Listing[]>([]);

  const load = async () => setListings(await api.hidden());
  useEffect(() => {
    load();
  }, []);

  const onHide = async (id: number, hidden: boolean) => {
    await api.setHidden(id, hidden);
    load();
  };
  const onCategoryRate = async (id: number, category: string, score: number) => {
    await api.setCategoryRating(id, category, score);
    load();
  };

  return (
    <div>
      <p className="empty-note">
        Listings either of you marked "not interested" - unhide to bring one back into the feed.
      </p>
      {listings.length === 0 ? (
        <p className="empty">Nothing hidden right now.</p>
      ) : (
        <div className="feed-grid">
          {listings.map((l) => (
            <ListingCard
              key={l.id}
              listing={l}
              user={user}
              onHide={onHide}
              onCategoryRate={onCategoryRate}
            />
          ))}
        </div>
      )}
    </div>
  );
}
