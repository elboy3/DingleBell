"""Lightweight "who's using this" picker - no passwords, just a cookie."""

from fastapi import APIRouter, Body, Request, Response

from ..deps import KNOWN_USERS, get_current_user

router = APIRouter(prefix="/api")

COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year


@router.get("/whoami")
def whoami(request: Request):
    return {"user": get_current_user(request)}


@router.post("/whoami")
def set_whoami(response: Response, user: str = Body(..., embed=True)):
    if user not in KNOWN_USERS:
        return {"ok": False}
    response.set_cookie("user", user, max_age=COOKIE_MAX_AGE, httponly=True, samesite="lax")
    return {"ok": True}
