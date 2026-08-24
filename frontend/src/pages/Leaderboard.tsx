import { useEffect, useState } from "react";
import { api } from "../api";
import type { Listing } from "../types";
import { ListingCard } from "../components/ListingCard";

const TABS: { key: string; label: string; empty: string }[] = [
  {
    key: "leaderboard_shared",
    label: "Shared",
    empty: "Nobody's rated a match yet - go rate some in the Inbox.",
  },
  { key: "leaderboard_elliott", label: "Elliott", empty: "Elliott hasn't rated anything yet." },
  { key: "leaderboard_madison", label: "Madison", empty: "Madison hasn't rated anything yet." },
  {
    key: "leaderboard_ai",
    label: "AI match",
    empty: "No AI scores yet - scores come from a browser scan.",
  },
];

export function Leaderboard({ user }: { user: string }) {
  const [tab, setTab] = useState(TABS[0].key);
  const [listings, setListings] = useState<Listing[]>([]);

  const load = async (sort: string) =>
    setListings(await api.listings({ sort, only_matched: "true" }));
  useEffect(() => {
    load(tab);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const onCategoryRate = async (id: number, category: string, score: number) => {
    await api.setCategoryRating(id, category, score);
    load(tab);
  };
  const onDisqualify = async (id: number) => {
    await api.setHidden(id, true, "off_market");
    load(tab);
  };

  const active = TABS.find((t) => t.key === tab) ?? TABS[0];

  return (
    <div>
      <div className="tab-row">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            className={`tab-button ${t.key === tab ? "active" : ""}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <p className="empty-note">
        {tab === "leaderboard_shared"
          ? "Ranked by how much you both like it - only listings you've both rated show up here."
          : tab === "leaderboard_ai"
            ? "Ranked by AI taste-match score."
            : `Ranked by ${active.label}'s own rating.`}
      </p>
      {listings.length === 0 ? (
        <p className="empty">{active.empty}</p>
      ) : (
        <div className="feed-grid">
          {listings.map((l) => (
            <ListingCard
              key={l.id}
              listing={l}
              user={user}
              onCategoryRate={onCategoryRate}
              onDisqualify={onDisqualify}
            />
          ))}
        </div>
      )}
    </div>
  );
}
