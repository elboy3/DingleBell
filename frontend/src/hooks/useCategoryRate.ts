import { api } from "../api";

/** Every list/detail page wires this up identically: save the category
 * score, then reload whatever local state that page shows. Kept as a
 * shared hook rather than copy-pasted per page. */
export function useCategoryRate(reload: () => void) {
  return async (id: number, category: string, score: number) => {
    await api.setCategoryRating(id, category, score);
    reload();
  };
}
