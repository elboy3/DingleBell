"""Shared rating-combination logic, used across the swipe/matches/leaderboard
routes and the listing detail page so they never disagree about what "our
rating" means.

Deliberately MIN, not average, of the two people's ratings when both have
rated: the goal is a place they both like, so one person's low rating
should pull the combined signal down, not get smoothed over."""

KNOWN_USERS = ["elliott", "madison"]


def compute_rating_summary(reactions: dict) -> dict:
    ratings = {u: reactions.get(u, {}).get("rating") for u in KNOWN_USERS}
    rated = {u: r for u, r in ratings.items() if r is not None}

    if len(rated) == len(KNOWN_USERS):
        both_rating = min(rated.values())
        label = None
    elif len(rated) == 1:
        ((only_user, only_rating),) = rated.items()
        both_rating = only_rating
        label = f"only {only_user.capitalize()} has rated"
    else:
        both_rating = None
        label = None

    return {"ratings": ratings, "both_rating": both_rating, "label": label}
