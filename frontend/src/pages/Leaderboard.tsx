import { useEffect, useState } from "react";
import { api } from "../api";
import type { Listing } from "../types";
import { ListingCard } from "../components/ListingCard";

export function Leaderboard({ user }: { user: string }) {
  const [listings, setListings] = useState<Listing[]>([]);

  const load = async () => setListings(await api.listings({ sort: "leaderboard" }));
  useEffect(() => {
    load();
  }, []);

  const onRate = async (id: number, rating: number) => {
    await api.setRating(id, rating);
    load();
  };
  const onHide = async (id: number, hidden: boolean) => {
    await api.setHidden(id, hidden);
    load();
  };

  return (
    <div>
      <p className="empty-note">
        Ranked by how much you both like it - only listings you've both rated show up here.
      </p>
      {listings.length === 0 ? (
        <p className="empty">Nobody's rated the same listing yet - go rate some in the Feed.</p>
      ) : (
        listings.map((l) => <ListingCard key={l.id} listing={l} user={user} onRate={onRate} onHide={onHide} />)
      )}
    </div>
  );
}
