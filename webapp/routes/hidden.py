"""Review + undo shared hides. Hiding is deliberate and joint, but never
permanent - this page is the escape hatch."""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from ..deps import get_current_user, get_store, templates
from ..ranking import compute_rating_summary

router = APIRouter()


@router.get("/hidden")
def hidden_listings(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/whoami")

    store = get_store()
    listings = [listing for listing in store.all_listings(include_hidden=True) if listing["hidden"]]
    for listing in listings:
        reactions = store.get_reactions_for_listing(listing["id"])
        listing["reactions"] = reactions
        listing.update(compute_rating_summary(reactions))

    return templates.TemplateResponse(request, "hidden.html", {"listings": listings, "user": user})
