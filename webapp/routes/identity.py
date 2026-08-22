"""Lightweight "who's using this" picker - no passwords, just a cookie."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from ..deps import KNOWN_USERS, templates

router = APIRouter()

COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year


@router.get("/whoami")
def whoami_form(request: Request):
    return templates.TemplateResponse(request, "whoami.html", {"users": KNOWN_USERS})


@router.post("/whoami")
def whoami_set(user: str = Form(...)):
    if user not in KNOWN_USERS:
        return RedirectResponse("/whoami", status_code=303)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("user", user, max_age=COOKIE_MAX_AGE, httponly=True)
    return response
