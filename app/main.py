from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.routers import auth as auth_router
from app.routers import dashboard as dashboard_router
from app.routers import invite as invite_router
from app.routers import pdf as pdf_router
from app.routers import pi as pi_router
from app.templating import templates

logging.basicConfig(
    level=logging.INFO if not settings.app_debug else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rpi")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        docs_url="/docs" if settings.app_debug else None,
        redoc_url=None,
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie=settings.session_cookie_name,
        same_site="lax",
        https_only=False,
        max_age=60 * 60 * 24 * 7,
    )

    static_dir = Path(__file__).resolve().parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.middleware("http")
    async def add_user_to_request(request: Request, call_next):
        request.state.user = None
        response = await call_next(request)
        return response

    app.include_router(auth_router.router)
    app.include_router(dashboard_router.router)
    app.include_router(pi_router.router)
    app.include_router(invite_router.router)
    app.include_router(pdf_router.router)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 307 and exc.headers and exc.headers.get("Location"):
            return RedirectResponse(url=exc.headers["Location"], status_code=303)
        if exc.status_code in (401, 403):
            if not request.session.get("user_id"):
                return RedirectResponse(url="/login", status_code=303)
        ctx = {
            "status_code": exc.status_code,
            "detail": exc.detail or "Erro",
        }
        try:
            return templates.TemplateResponse(
                request, "error.html", ctx, status_code=exc.status_code
            )
        except Exception:  # noqa: BLE001
            return HTMLResponse(
                f"<h1>{exc.status_code}</h1><p>{exc.detail}</p>",
                status_code=exc.status_code,
            )

    return app


app = create_app()
