import { useEffect, useState } from "react";
import { api } from "../api";
import type { Listing } from "../types";
import { ListingCard } from "../components/ListingCard";

export function NeedsScan({ user }: { user: string }) {
  const [listings, setListings] = useState<Listing[]>([]);

  const load = async () => setListings(await api.needsScan());
  useEffect(() => {
    load();
  }, []);

  const onCategoryRate = async (id: number, category: string, score: number) => {
    await api.setCategoryRating(id, category, score);
    load();
  };

  return (
    <div>
      <p className="empty-note">
        Listings missing a photo or address - run a browser scan to backfill these. They're kept
        out of the swipe queue until they're ready.
      </p>
      {listings.length === 0 ? (
        <p className="empty">Nothing waiting on a scan - everything has a photo and address.</p>
      ) : (
        <div className="feed-grid">
          {listings.map((l) => (
            <ListingCard key={l.id} listing={l} user={user} onCategoryRate={onCategoryRate} />
          ))}
        </div>
      )}
    </div>
  );
}
