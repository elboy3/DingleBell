import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useCategoryRate } from "../hooks/useCategoryRate";
import type { Listing } from "../types";
import { ListingCard } from "../components/ListingCard";

export function Swipe({ user }: { user: string }) {
  const [queue, setQueue] = useState<Listing[] | null>(null);
  const [decided, setDecided] = useState(0);

  const load = async () => {
    setQueue(await api.swipeQueue());
    setDecided(0);
  };

  useEffect(() => {
    load();
  }, []);

  const decide = (id: number) => {
    setQueue((prev) => (prev ? prev.filter((l) => l.id !== id) : prev));
    setDecided((n) => n + 1);
  };

  const onSwipe = async (id: number, direction: "left" | "right") => {
    decide(id);
    await api.swipe(id, direction);
  };
  const onCategoryRate = useCategoryRate(() => {});

  if (queue === null) return <p className="empty">Loading...</p>;

  const current = queue[0];
  const remaining = queue.length;

  return (
    <div className="swipe-page">
      {current ? (
        <>
          <p className="swipe-progress">
            {remaining} left to decide{decided > 0 ? ` · ${decided} done this session` : ""}
          </p>
          <ListingCard
            key={current.id}
            listing={current}
            user={user}
            onSwipe={onSwipe}
            onCategoryRate={onCategoryRate}
            detailLevel="minimal"
            swipeDecide
          />
        </>
      ) : (
        <div className="swipe-empty">
          <p className="empty">
            {decided > 0
              ? "That's everything for now - nice work."
              : "Nothing new to decide on right now."}
          </p>
          <div className="swipe-empty-links">
            <Link to="/inbox">Check the Inbox for matches →</Link>
            <Link to="/needs-scan">See what's waiting on a scan →</Link>
          </div>
        </div>
      )}
    </div>
  );
}
