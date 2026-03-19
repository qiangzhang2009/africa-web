"""
AfricaZero — FastAPI Backend
Main entry point. Routes are mounted in app/routers/.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.routers import calculator, hs_codes, countries, subscribe

load_dotenv()

# ─── Database initialization ─────────────────────────────────────────────────
def _get_db_path() -> Path:
    raw = os.getenv("DATABASE_URL", "data/africa_zero.db")
    path = Path(raw)
    # If path is relative, resolve from where uvicorn is started (cwd)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

DB_PATH = _get_db_path()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Bootstrap: ensure DB schema and seed data exist on startup."""
    from app.models.database import init_db
    init_db(str(DB_PATH))
    yield


# ─── CORS configuration (must be before any routes) ─────────────────────────
_origins_raw = os.getenv("CORS_ORIGINS", "").strip()
if _origins_raw in ("*", "all", "true"):
    _allow_origins = ["*"]
    _allow_credentials = False
elif _origins_raw:
    _allow_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]
    _allow_credentials = True
else:
    # Default fallback — allow common development URLs
    _allow_origins = [
        "https://africa-web-1.onrender.com",
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    _allow_credentials = True

app = FastAPI(
    title="AfricaZero API",
    description="非洲零关税全链路决策平台 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORSMiddleware MUST come FIRST (before routes) so it handles OPTIONS preflight
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routes ──────────────────────────────────────────────────────────────────
app.include_router(calculator.router, prefix="/api/v1", tags=["关税与成本计算"])
app.include_router(hs_codes.router, prefix="/api/v1", tags=["HS编码查询"])
app.include_router(countries.router, prefix="/api/v1", tags=["国家信息"])
app.include_router(subscribe.router, prefix="/api/v1", tags=["订阅管理"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "africa-zero"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
