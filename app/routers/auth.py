from __future__ import annotations

import logging

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User, UserRole
from app.templating import templates

logger = logging.getLogger(__name__)
router = APIRouter()

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/login", name="login")
async def login_page(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id:
        if db.get(User, user_id):
            return RedirectResponse(url="/dashboard", status_code=303)
        request.session.clear()
    error = request.query_params.get("error")
    return templates.TemplateResponse(
        request, "login.html",
        {
            "settings": settings,
            "error": error,
        },
    )


@router.get("/auth/google", name="auth_google")
async def auth_google(request: Request):
    redirect_uri = settings.google_redirect_uri
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback", name="auth_google_callback")
async def auth_google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as exc:
        logger.warning("OAuth error: %s", exc)
        return RedirectResponse(url="/login?error=oauth", status_code=303)

    userinfo = token.get("userinfo")
    if not userinfo:
        try:
            userinfo = await oauth.google.userinfo(token=token)
        except Exception:  # noqa: BLE001
            userinfo = None
    if not userinfo:
        return RedirectResponse(url="/login?error=userinfo", status_code=303)

    sub = userinfo.get("sub")
    email = (userinfo.get("email") or "").lower().strip()
    name = userinfo.get("name") or email.split("@")[0]
    picture = userinfo.get("picture")

    if not email:
        return RedirectResponse(url="/login?error=email", status_code=303)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        role = (
            UserRole.admin
            if email in settings.admin_emails_list
            else UserRole.author
        )
        user = User(
            name=name,
            email=email,
            role=role,
            google_sub=sub,
            picture=picture,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        changed = False
        if user.google_sub != sub and sub:
            user.google_sub = sub
            changed = True
        if name and user.name != name:
            user.name = name
            changed = True
        if picture and user.picture != picture:
            user.picture = picture
            changed = True
        if email in settings.admin_emails_list and user.role != UserRole.admin:
            user.role = UserRole.admin
            changed = True
        if changed:
            db.commit()

    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/logout", name="logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
