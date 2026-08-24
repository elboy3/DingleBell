import { useEffect, useState } from "react";
import { api } from "../api";
import type { Listing } from "../types";
import { ListingCard } from "../components/ListingCard";

export function OpenHouses({ user }: { user: string }) {
  const [listings, setListings] = useState<Listing[]>([]);
  const [favoritesOnly, setFavoritesOnly] = useState(false);

  const load = async (fav: boolean) => setListings(await api.openHouses(fav));
  useEffect(() => {
    load(favoritesOnly);
  }, [favoritesOnly]);

  const onCategoryRate = async (id: number, category: string, score: number) => {
    await api.setCategoryRating(id, category, score);
    load(favoritesOnly);
  };

  return (
    <div>
      <div className="controls">
        <label>
          <input
            type="checkbox"
            checked={favoritesOnly}
            onChange={(e) => setFavoritesOnly(e.target.checked)}
          />
          Favorites only (both rated 4+)
        </label>
      </div>
      {listings.length === 0 ? (
        <p className="empty">No upcoming open houses{favoritesOnly ? " for your favorites" : ""}.</p>
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
