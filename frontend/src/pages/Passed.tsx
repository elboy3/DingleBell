import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useCategoryRate } from "../hooks/useCategoryRate";
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

/** Compact row for the bulk "passed" list - this section only grows over
 * time (passing happens far more than liking), so full photo cards don't
 * scale: a real audit trail of a few hundred listings needs to be
 * scannable, not scrolled through one giant card at a time. */
function PassedRow({ listing }: { listing: Listing }) {
  const title = listing.address || `Listing #${listing.id}`;
  const facts = [
    listing.price != null ? `$${listing.price.toLocaleString()}/mo` : null,
    listing.beds != null ? `${listing.beds} bed` : null,
    listing.baths != null ? `${listing.baths} bath` : null,
    listing.neighborhood,
  ].filter(Boolean);

  return (
    <Link to={`/listings/${listing.id}`} className="passed-row">
      {listing.photo_url ? (
        <img className="passed-row-thumb" src={listing.photo_url} alt="" />
      ) : (
        <div className="passed-row-thumb passed-row-thumb-empty" />
      )}
      <div className="passed-row-info">
        <span className="passed-row-address">{title}</span>
        <span className="passed-row-facts">{facts.join(" · ")}</span>
      </div>
      <SwipeTags swipes={listing.swipes} />
    </Link>
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

  const onCategoryRate = useCategoryRate(load);
  const undoOffMarket = async (id: number) => {
    await api.setHidden(id, false);
    load();
  };

  const disagreements = passed.filter((l) => l.mismatch);
  const bothPassed = passed.filter((l) => !l.mismatch);

  return (
    <div>
      <h3>Disagreements</h3>
      <p className="empty-note">One of you liked it, the other passed.</p>
      {disagreements.length === 0 ? (
        <p className="empty">No disagreements yet.</p>
      ) : (
        <div className="feed-grid">
          {disagreements.map((l) => (
            <div key={l.id}>
              <SwipeTags swipes={l.swipes} />
              <ListingCard listing={l} user={user} onCategoryRate={onCategoryRate} />
            </div>
          ))}
        </div>
      )}

      <h3>Passed while swiping</h3>
      <p className="empty-note">
        Full transparency, no undo - once you swipe, it's gone from your own queue for good.
      </p>
      {bothPassed.length === 0 ? (
        <p className="empty">Nothing passed on yet.</p>
      ) : (
        <div className="passed-row-list">
          {bothPassed.map((l) => (
            <PassedRow key={l.id} listing={l} />
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
