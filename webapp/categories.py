"""Rating categories for the "why do you like it" breakdown - shown when a
listing gets a thumbs-up instead of hidden. Kept as a plain list (not
user-editable) since there are only two users and the set is small enough
to hardcode; mirrored by hand in frontend/src/categories.ts."""

CATEGORIES = [
    ("light", "Light"),
    ("kitchen", "Kitchen"),
    ("location", "Location"),
    ("vibe", "Vibe"),
    ("coziness", "Coziness"),
    ("space", "Space"),
]
CATEGORY_KEYS = [key for key, _ in CATEGORIES]
