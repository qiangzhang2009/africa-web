"""
AfricaZero — FastAPI Backend
Main entry point. Routes are mounted in app/routers/.
"""
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.routers import calculator, hs_codes, countries, subscribe
from app.routers.auth import router as auth_router
from app.routers.subscription import router as subscription_router
from app.routers.api_keys import router as api_keys_router
from app.routers.admin import router as admin_router
from app.routers.freight import router as freight_router
from app.routers.certificate import router as certificate_router
from app.routers.suppliers import router as suppliers_router

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Bootstrap: ensure DB schema and seed data exist on startup."""
    from app.models.database import get_db_path, init_db, seed_admin_user
    db_path = get_db_path()
    init_db(db_path)
    seed_admin_user(db_path)
    yield


# ─── CORS configuration (must be before any routes) ─────────────────────────
# 明确允许的跨域来源（不能用 * 因为 credentials=True 时浏览器拒绝 *）
# OnRender 后端通过 Vercel rewrite 被 AfricaZero 前端调用
_allow_origins = [
    "https://africa.zxqconsulting.com",
    "https://global2china.zxqconsulting.com",
    "https://frontend-nrlqfber2-johnzhangs-projects-50e83ec4.vercel.app",
    "https://africa-web-1.onrender.com",
    "https://africa-zero-frontend.vercel.app",
    "http://localhost:5173",  # dev
    "http://localhost:8000",  # dev
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


# ─── Global OPTIONS handler (bypasses lifespan/cold-start delays) ────────────
# OnRender 免费版冷启动时 lifespan 中的 init_db() 会阻塞 OPTIONS 预检请求
# 解决：添加同步 OPTIONS 处理器，优先于所有异步路由匹配
@app.api_route("/{path:path}", methods=["OPTIONS"])
async def options_handler(request: Request, path: str):
    """Handle all OPTIONS preflight requests before reaching any route handler."""
    origin = request.headers.get("origin", "*")
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
            "Access-Control-Max-Age": "600",
        },
    )


# ─── Routes ──────────────────────────────────────────────────────────────────
app.include_router(calculator.router, prefix="/api/v1", tags=["关税与成本计算"])
app.include_router(hs_codes.router, prefix="/api/v1", tags=["HS编码查询"])
app.include_router(countries.router, prefix="/api/v1", tags=["国家信息"])
app.include_router(subscribe.router, prefix="/api/v1", tags=["订阅查询"])
app.include_router(auth_router, prefix="/api/v1", tags=["用户认证"])
app.include_router(subscription_router, prefix="/api/v1", tags=["订阅管理"])
app.include_router(api_keys_router, prefix="/api/v1", tags=["API密钥管理"])
app.include_router(admin_router, prefix="/api/v1", tags=["管理后台"])
app.include_router(freight_router, prefix="/api/v1", tags=["物流成本估算"])
app.include_router(certificate_router, prefix="/api/v1", tags=["原产地证书办理"])
app.include_router(suppliers_router, prefix="/api/v1", tags=["供应商发现"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "africa-zero"}


@app.get("/debug/login")
def debug_login():
    """Debug endpoint: try login and return any exception details."""
    import traceback
    from app.models.database import get_db, _is_postgres
    from app.models.database import hash_password, verify_password
    from jose import jwt
    from datetime import datetime, timedelta, timezone

    try:
        from app.models.database import get_db_path
        DB_PATH = get_db(get_db_path())
        cursor = DB_PATH.cursor()
        email = "admin@africa-zero.com"
        password = "AfricaZero2026Admin!"

        # Test the SQL directly
        if _is_postgres():
            cursor.execute("SELECT * FROM users WHERE email = %s AND is_active = 1", (email,))
        else:
            cursor.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", (email,))
        row = cursor.fetchone()
        DB_PATH.close()

        if not row:
            return {"step": "user_lookup", "result": "not_found"}

        # Test password
        pwd_ok = verify_password(password, row["password_hash"])

        return {
            "is_postgres": _is_postgres(),
            "db_driver": "postgresql" if _is_postgres() else "sqlite",
            "user_found": True,
            "user_id": row["id"],
            "email": row["email"],
            "password_ok": pwd_ok,
            "tier": row["tier"],
            "is_admin": bool(row["is_admin"]),
            "expires_at": row["expires_at"],
            "created_at": row["created_at"],
            "password_hash": row["password_hash"][:20] + "...",
        }
    except Exception as e:
        import sys
        return {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
