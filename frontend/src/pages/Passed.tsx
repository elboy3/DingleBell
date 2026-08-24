import { useEffect, useState } from "react";
import { api } from "../api";
import type { Listing } from "../types";
import { ListingCard } from "../components/ListingCard";

const NAMES: Record<string, string> = { elliott: "Elliott", madison: "Madison" };

function swipeTag(direction: string | undefined) {
  if (direction === "right") return { text: "liked", cls: "liked" };
  if (direction === "left") return { text: "passed", cls: "passed" };
  return { text: "hasn't swiped yet", cls: "pending" };
}

function SwipeTags({ swipes }: { swipes: Record<string, string> }) {
  return (
    <div className="swipe-tags">
      {Object.entries(NAMES).map(([key, name]) => {
        const tag = swipeTag(swipes[key]);
        return (
          <span className={`swipe-tag ${tag.cls}`} key={key}>
            {name}: {tag.text}
          </span>
        );
      })}
    </div>
  );
}

export function Passed({ user }: { user: string }) {
  const [passed, setPassed] = useState<Listing[]>([]);
  const [offMarket, setOffMarket] = useState<Listing[]>([]);

  const load = async () => {
    setPassed(await api.passed());
    setOffMarket(await api.offMarket());
  };
  useEffect(() => {
    load();
  }, []);

  const onCategoryRate = async (id: number, category: string, score: number) => {
    await api.setCategoryRating(id, category, score);
    load();
  };
  const undoOffMarket = async (id: number) => {
    await api.setHidden(id, false);
    load();
  };

  return (
    <div>
      <h3>Passed while swiping</h3>
      <p className="empty-note">
        Full transparency, no undo - once you swipe, it's gone from your own queue for good.
      </p>
      {passed.length === 0 ? (
        <p className="empty">Nothing passed on yet.</p>
      ) : (
        <div className="feed-grid">
          {passed.map((l) => (
            <div key={l.id}>
              <SwipeTags swipes={l.swipes} />
              <ListingCard listing={l} user={user} onCategoryRate={onCategoryRate} />
            </div>
          ))}
        </div>
      )}

      <h3>Disqualified matches (off market)</h3>
      <p className="empty-note">
        Matches removed from the Leaderboard because they're no longer available - reversible.
      </p>
      {offMarket.length === 0 ? (
        <p className="empty">Nothing disqualified right now.</p>
      ) : (
        <div className="feed-grid">
          {offMarket.map((l) => (
            <div key={l.id}>
              <button type="button" className="undo-link" onClick={() => undoOffMarket(l.id)}>
                Undo - bring back to Leaderboard
              </button>
              <ListingCard listing={l} user={user} onCategoryRate={onCategoryRate} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
