import { useEffect, useState } from "react";
import { api } from "../api";
import { useCategoryRate } from "../hooks/useCategoryRate";
import type { Listing } from "../types";
import { ListingCard } from "../components/ListingCard";

const NAMES: Record<string, string> = { elliott: "Elliott", madison: "Madison" };

export function Matches({ user }: { user: string }) {
  const [listings, setListings] = useState<Listing[]>([]);

  const load = async () => setListings(await api.matches());
  useEffect(() => {
    load();
  }, []);

  const onCategoryRate = useCategoryRate(load);

  const matched = listings.filter((l) => l.match_status === "match");
  const waiting = listings.filter((l) => l.match_status === "pending");

  return (
    <div>
      <p className="empty-note">
        It's a match! Listings you both swiped right on - open one to leave category ratings and
        comments, then check the Leaderboard once you've both weighed in.
      </p>
      {matched.length === 0 ? (
        <p className="empty">No matches yet - keep swiping.</p>
      ) : (
        <div className="feed-grid">
          {matched.map((l) => (
            <ListingCard key={l.id} listing={l} user={user} onCategoryRate={onCategoryRate} />
          ))}
        </div>
      )}

      <h3>Waiting on a decision</h3>
      <p className="empty-note">
        Ones you swiped right on that your partner hasn't decided on yet - they'll move up to
        Matched if it becomes mutual.
      </p>
      {waiting.length === 0 ? (
        <p className="empty">Nothing waiting right now.</p>
      ) : (
        <div className="feed-grid">
          {waiting.map((l) => (
            <div key={l.id}>
              <div className="swipe-tags">
                <span className="swipe-tag pending">
                  Waiting on {NAMES[l.waiting_on ?? ""] ?? l.waiting_on}
                </span>
              </div>
              <ListingCard
                listing={l}
                user={user}
                onCategoryRate={onCategoryRate}
                detailLevel="minimal"
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
