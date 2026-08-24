import type { Listing } from "./types";

// Must match the frontend's own hostname (both "localhost") for the
// identity cookie to work - SameSite=Lax blocks cookies on background
// fetch() calls across different hostnames, even when both are loopback
// (127.0.0.1 vs localhost counts as cross-site for cookie purposes).
const API_BASE = "http://localhost:8000/api";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${await res.text()}`);
  }
  return res.json();
}

export const api = {
  whoami: () => request<{ user: string | null }>("/whoami"),
  setWhoami: (user: string) =>
    request<{ ok: boolean }>("/whoami", { method: "POST", body: JSON.stringify({ user }) }),
  listings: (params: Record<string, string>) =>
    request<Listing[]>(`/listings?${new URLSearchParams(params)}`),
  listing: (id: number) => request<Listing>(`/listings/${id}`),
  setComment: (id: number, comment: string) =>
    request<{ ok: boolean }>(`/listings/${id}/comment`, {
      method: "POST",
      body: JSON.stringify({ comment }),
    }),
  setHidden: (id: number, hidden: boolean, reason?: string) =>
    request<{ ok: boolean }>(`/listings/${id}/hidden`, {
      method: "POST",
      body: JSON.stringify({ hidden, ...(reason ? { reason } : {}) }),
    }),
  swipe: (id: number, direction: "left" | "right") =>
    request<{ ok: boolean }>(`/listings/${id}/swipe`, {
      method: "POST",
      body: JSON.stringify({ direction }),
    }),
  setCategoryRating: (id: number, category: string, score: number) =>
    request<{ ok: boolean }>(`/listings/${id}/category-rating`, {
      method: "POST",
      body: JSON.stringify({ category, score }),
    }),
  needsScan: () => request<Listing[]>("/needs-scan"),
  swipeQueue: () => request<Listing[]>("/swipe-queue"),
  matches: () => request<Listing[]>("/matches"),
  passed: () => request<Listing[]>("/passed"),
  offMarket: () => request<Listing[]>("/off-market"),
};
