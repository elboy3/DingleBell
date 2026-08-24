export interface Reaction {
  rating: number | null;
  comment: string | null;
  updated_at: string;
}

export interface Listing {
  id: number;
  url: string;
  address: string | null;
  price: number | null;
  beds: number | null;
  baths: number | null;
  sqft: number | null;
  neighborhood: string | null;
  photo_url: string | null;
  open_house_raw: string | null;
  open_house_date: string | null;
  available_date: string | null;
  ai_score: number | null;
  ai_reasoning: string | null;
  first_seen: string;
  swipes: Record<string, string>;
  match_status: "pending" | "match" | "miss";
  mismatch: boolean;
  waiting_on?: string | null;
  reactions: Record<string, Reaction>;
  ratings: { elliott: number | null; madison: number | null };
  both_rating: number | null;
  label: string | null;
  rank?: number;
  needs_backfill: boolean;
  category_ratings: Record<string, Record<string, number>>;
}
