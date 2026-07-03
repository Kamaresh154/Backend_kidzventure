from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import settings

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Validate secrets on startup — raises if JWT_SECRET is missing
    settings.validate_production_secrets()
    from app.core.database import AsyncSessionLocal
    from app.db.bootstrap import init_sqlite_schema, seed_rbac, ensure_employee_permissions, seed_demo_org

    await init_sqlite_schema()
    async with AsyncSessionLocal() as db:
        await seed_rbac(db)
        await db.flush()
        await ensure_employee_permissions(db)
        await seed_demo_org(db)
        await db.commit()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.4.0",
    description=(
        "Kidzventure ERP — Phase 1–4 API: auth, org/franchise, students, parents, "
        "attendance, invoices, ledger, payroll, inventory, CRM, reports"
    ),
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Serve frontend static files ─────────────────────────────────────────
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/")
    async def serve_frontend() -> HTMLResponse:
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(html)

    @app.exception_handler(404)
    async def spa_fallback(request: Request, exc: Exception) -> HTMLResponse:
        if request.url.path.startswith("/api/") or request.url.path.startswith("/assets/") or request.url.path == "/health":
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(html)
else:
    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "Kidzventure ERP API", "docs": "/docs"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "kidzventure-api", "version": "0.4.0"}


app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(Exception)
async def unhandled_exception(_request: Request, exc: Exception) -> JSONResponse:
    if settings.debug:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
