from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
    if settings.use_sqlite:
        from app.db.bootstrap import bootstrap_sqlite

        await bootstrap_sqlite()
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "kidzventure-api", "version": "0.4.0"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Kidzventure ERP API", "docs": "/docs"}


app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(Exception)
async def unhandled_exception(_request: Request, exc: Exception) -> JSONResponse:
    if settings.debug:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
