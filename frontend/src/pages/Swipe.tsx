import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useCategoryRate } from "../hooks/useCategoryRate";
import { mapEmbedUrl } from "../mapEmbed";
import type { Listing } from "../types";
import { ListingCard } from "../components/ListingCard";

const OTHER_USER: Record<string, string> = { elliott: "madison", madison: "elliott" };

export function Swipe({ user }: { user: string }) {
  const [queue, setQueue] = useState<Listing[] | null>(null);
  const [decided, setDecided] = useState(0);
  const [commentDraft, setCommentDraft] = useState("");
  const [commentSaved, setCommentSaved] = useState(false);
  const [, setSearchParams] = useSearchParams();

  const load = async () => {
    setQueue(await api.swipeQueue());
    setDecided(0);
  };

  useEffect(() => {
    load();
  }, []);

  const current = queue?.[0] ?? null;

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    setCommentDraft(current?.reactions[user]?.comment || "");
    setCommentSaved(false);
    // Reflects which listing is on screen in the URL - just for reference
    // (sharing/debugging), doesn't drive which listing loads.
    setSearchParams(current ? { id: String(current.id) } : {}, { replace: true });
  }, [current?.id]);

  const decide = (id: number) => {
    setQueue((prev) => (prev ? prev.filter((l) => l.id !== id) : prev));
    setDecided((n) => n + 1);
  };

  const onSwipe = async (id: number, direction: "left" | "right") => {
    const draftToSave = commentDraft;
    decide(id);
    await Promise.all([
      api.swipe(id, direction),
      draftToSave ? api.setComment(id, draftToSave) : Promise.resolve(),
    ]);
  };
  const onCategoryRate = useCategoryRate(() => {});
  const saveComment = async () => {
    if (!current) return;
    await api.setComment(current.id, commentDraft);
    setCommentSaved(true);
  };

  if (queue === null) return <p className="empty">Loading...</p>;

  const remaining = queue.length;
  const otherComment = current?.reactions[OTHER_USER[user]]?.comment;
  const mapUrl = current?.address ? mapEmbedUrl(current.address, current.neighborhood) : null;

  return (
    <div className="swipe-page">
      {current ? (
        <>
          <p className="swipe-progress">
            {remaining} left to decide{decided > 0 ? ` · ${decided} done this session` : ""}
          </p>
          <div className="detail-layout">
            <div className="listing-detail-card">
              <ListingCard
                key={current.id}
                listing={current}
                user={user}
                onSwipe={onSwipe}
                onCategoryRate={onCategoryRate}
                detailLevel="minimal"
                swipeDecide
                linkExternally
              />
            </div>

            <div className="detail-side">
              {mapUrl && (
                <div className="map-embed">
                  <iframe
                    width="100%"
                    height="240"
                    style={{ border: 0 }}
                    loading="lazy"
                    referrerPolicy="no-referrer-when-downgrade"
                    src={mapUrl}
                    title="Map"
                  />
                </div>
              )}
              {otherComment && (
                <div className="comment">
                  <strong>{OTHER_USER[user][0].toUpperCase() + OTHER_USER[user].slice(1)}:</strong>{" "}
                  {otherComment}
                </div>
              )}
              <div className="comment-form">
                <textarea
                  value={commentDraft}
                  onChange={(e) => {
                    setCommentDraft(e.target.value);
                    setCommentSaved(false);
                  }}
                  placeholder="Leave a note while you decide..."
                />
                <div className="comment-form-actions">
                  <button onClick={saveComment}>Save comment</button>
                  {commentSaved && <span className="save-confirmation">Saved ✓</span>}
                </div>
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="swipe-empty">
          <p className="empty">
            {decided > 0
              ? "That's everything for now - nice work."
              : "Nothing new to decide on right now."}
          </p>
          <div className="swipe-empty-links">
            <Link to="/matches">Check your matches →</Link>
            <Link to="/needs-scan">See what's waiting on a scan →</Link>
          </div>
        </div>
      )}
    </div>
  );
}
