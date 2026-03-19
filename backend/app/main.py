"""
AfricaZero — FastAPI Backend
Main entry point. Routes are mounted in app/routers/.
"""
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.routers import calculator, hs_codes, countries, subscribe

load_dotenv()

# ─── Database initialization ─────────────────────────────────────────────────
DB_PATH = Path("data") / "africa_zero.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Bootstrap: ensure DB schema and seed data exist on startup."""
    from app.models.database import init_db
    init_db(str(DB_PATH))
    yield


app = FastAPI(
    title="AfricaZero API",
    description="非洲零关税全链路决策平台 API",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ───────────────────────────────────────────────────────────────────
import os

origins_raw = os.getenv("CORS_ORIGINS", "").strip()
if origins_raw in ("*", "all", "true"):
    allow_origins = ["*"]
    allow_credentials = False
elif origins_raw:
    allow_origins = [o.strip() for o in origins_raw.split(",") if o.strip()]
    allow_credentials = True
else:
    allow_origins = [
        "https://africa-web-1.onrender.com",
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── OPTIONS bypass middleware ────────────────────────────────────────────────
# Render + Cloudflare platform layer intercepts OPTIONS preflight before it
# reaches this middleware. The Cloudflare Worker (_worker.js) handles this
# for browser requests. For direct backend calls, we still return proper headers.
@app.middleware("http")
async def cors_options_bypass(request: Request, call_next):
    if request.method == "OPTIONS":
        origin = request.headers.get("origin", "")
        response = Response(status_code=204)
        response.headers["Access-Control-Allow-Origin"] = origin or "https://africa-web-1.onrender.com"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept, Origin"
        response.headers["Access-Control-Max-Age"] = "86400"
        response.headers["Vary"] = "Origin"
        return response
    return await call_next(request)


# ─── Routes ──────────────────────────────────────────────────────────────────
app.include_router(calculator.router, prefix="/api/v1", tags=["关税与成本计算"])
app.include_router(hs_codes.router, prefix="/api/v1", tags=["HS编码查询"])
app.include_router(countries.router, prefix="/api/v1", tags=["国家信息"])
app.include_router(subscribe.router, prefix="/api/v1", tags=["订阅管理"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "africa-zero"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
