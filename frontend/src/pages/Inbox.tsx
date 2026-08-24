import { useEffect, useState } from "react";
import { api } from "../api";
import { useCategoryRate } from "../hooks/useCategoryRate";
import type { Listing } from "../types";
import { ListingCard } from "../components/ListingCard";

export function Inbox({ user }: { user: string }) {
  const [listings, setListings] = useState<Listing[]>([]);

  const load = async () => setListings(await api.inbox());
  useEffect(() => {
    load();
  }, []);

  const onCategoryRate = useCategoryRate(load);

  return (
    <div>
      <p className="empty-note">
        It's a match! Listings you both swiped right on - open one to leave category ratings and
        comments, then check the Leaderboard once you've both weighed in.
      </p>
      {listings.length === 0 ? (
        <p className="empty">No matches yet - keep swiping.</p>
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
