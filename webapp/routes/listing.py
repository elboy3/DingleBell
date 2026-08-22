"""Per-listing detail + the actions that mutate state: rating, comment,
and the shared hide toggle."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from ..deps import get_current_user, get_store, templates
from ..ranking import compute_rating_summary

router = APIRouter()


@router.get("/listings/{listing_id}")
def listing_detail(request: Request, listing_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/whoami")

    store = get_store()
    listings_by_id = {row["id"]: row for row in store.all_listings(include_hidden=True)}
    listing = listings_by_id.get(listing_id)
    if listing is None:
        return RedirectResponse("/")

    reactions = store.get_reactions_for_listing(listing_id)
    listing["reactions"] = reactions
    listing.update(compute_rating_summary(reactions))

    return templates.TemplateResponse(
        request, "listing_detail.html", {"listing": listing, "user": user}
    )


@router.post("/listings/{listing_id}/rating")
def set_rating(request: Request, listing_id: int, rating: int = Form(...)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/whoami", status_code=303)
    get_store().set_rating(listing_id, user, rating)
    return RedirectResponse(request.headers.get("referer", "/"), status_code=303)


@router.post("/listings/{listing_id}/comment")
def set_comment(request: Request, listing_id: int, comment: str = Form(...)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/whoami", status_code=303)
    get_store().set_comment(listing_id, user, comment)
    return RedirectResponse(f"/listings/{listing_id}", status_code=303)


@router.post("/listings/{listing_id}/hidden")
def set_hidden(request: Request, listing_id: int, hidden: str = Form(...)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/whoami", status_code=303)
    get_store().set_hidden(listing_id, hidden == "true", user)
    return RedirectResponse(request.headers.get("referer", "/"), status_code=303)
