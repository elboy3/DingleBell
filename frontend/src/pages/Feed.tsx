import { useEffect, useState } from "react";
import { api } from "../api";
import type { Listing } from "../types";
import { ListingCard } from "../components/ListingCard";

export function Feed({ user }: { user: string }) {
  const [listings, setListings] = useState<Listing[]>([]);
  const [neighborhoods, setNeighborhoods] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const [sort, setSort] = useState("ai");
  const [needsReview, setNeedsReview] = useState("");
  const [neighborhood, setNeighborhood] = useState("");
  const [minScore, setMinScore] = useState("");
  const [priceMin, setPriceMin] = useState("");
  const [priceMax, setPriceMax] = useState("");
  const [availableBefore, setAvailableBefore] = useState("");
  const [showMoreFilters, setShowMoreFilters] = useState(false);

  const load = async () => {
    setLoading(true);
    const params: Record<string, string> = { sort };
    if (needsReview) params.needs_review = needsReview;
    if (neighborhood) params.neighborhood = neighborhood;
    if (minScore) params.min_score = minScore;
    if (priceMin) params.price_min = priceMin;
    if (priceMax) params.price_max = priceMax;
    if (availableBefore) params.available_before = availableBefore;
    const data = await api.listings(params);
    setListings(data);
    setLoading(false);
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    load();
  }, [sort, needsReview, neighborhood]);

  useEffect(() => {
    api.neighborhoods().then(setNeighborhoods);
  }, []);

  const onRate = async (id: number, rating: number) => {
    // Optimistic: fill the stars in immediately, then reconcile with the
    // server (which also recomputes sort position/leaderboard rank) -
    // instant feedback on the click itself is what actually matters for
    // "feels slick," the sort re-shuffling a beat later is fine.
    setListings((prev) =>
      prev.map((l) => (l.id === id ? { ...l, ratings: { ...l.ratings, [user]: rating } } : l)),
    );
    await api.setRating(id, rating);
    load();
  };
  const onHide = async (id: number, hidden: boolean) => {
    setListings((prev) => (hidden ? prev.filter((l) => l.id !== id) : prev));
    await api.setHidden(id, hidden);
    load();
  };

  return (
    <div>
      <div className="controls">
        <label>
          Sort:
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="ai">AI match</option>
            <option value="ours">Our ratings</option>
          </select>
        </label>
        <label>
          Needs review:
          <select value={needsReview} onChange={(e) => setNeedsReview(e.target.value)}>
            <option value="">Everyone</option>
            <option value="me">Only I haven't rated</option>
            <option value="both">Neither of us has rated</option>
          </select>
        </label>
        <button
          type="button"
          className="filters-toggle"
          onClick={() => setShowMoreFilters((v) => !v)}
        >
          {showMoreFilters ? "Fewer filters" : "More filters"}
        </button>
      </div>

      {showMoreFilters && (
        <div className="controls more-filters">
          <label>
            Neighborhood:
            <select value={neighborhood} onChange={(e) => setNeighborhood(e.target.value)}>
              <option value="">All</option>
              {neighborhoods.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <label>
            Min score:
            <input
              type="number"
              value={minScore}
              onChange={(e) => setMinScore(e.target.value)}
              placeholder="none"
            />
          </label>
          <label>
            Price min:
            <input type="number" value={priceMin} onChange={(e) => setPriceMin(e.target.value)} />
          </label>
          <label>
            Price max:
            <input type="number" value={priceMax} onChange={(e) => setPriceMax(e.target.value)} />
          </label>
          <label>
            Available by:
            <input type="date" value={availableBefore} onChange={(e) => setAvailableBefore(e.target.value)} />
          </label>
          <button onClick={load}>Apply</button>
        </div>
      )}

      {loading ? (
        <p className="empty">Loading...</p>
      ) : listings.length === 0 ? (
        <p className="empty">No listings match these filters.</p>
      ) : (
        <div className="feed-grid">
          {listings.map((l) => (
            <ListingCard key={l.id} listing={l} user={user} onRate={onRate} onHide={onHide} />
          ))}
        </div>
      )}
    </div>
  );
}
