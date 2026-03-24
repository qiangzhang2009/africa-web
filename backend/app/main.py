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
    import traceback
    from app.models.database import get_db_path, _is_postgres
    try:
        from app.models.database import get_db
        db_path = get_db_path()
        is_pg = _is_postgres()
        conn = get_db(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        user_count = cursor.fetchone()["cnt"]
        conn.close()
        return {
            "status": "ok",
            "service": "africa-zero",
            "is_postgres": is_pg,
            "db_path": db_path[:30] + "..." if len(db_path) > 30 else db_path,
            "user_count": user_count,
        }
    except Exception as e:
        return {
            "status": "error",
            "service": "africa-zero",
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()[-500:],
        }


@app.get("/debug/login")
def debug_login():
    """Debug endpoint: try login and return any exception details."""
    import traceback, sys
    from app.models.database import get_db, _is_postgres, get_db_path
    from app.models.database import hash_password, verify_password
    from jose import jwt
    from datetime import datetime, timedelta, timezone

    try:
        db_path = get_db_path()
        DB_PATH = get_db(db_path)
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
        if not pwd_ok:
            return {"step": "password_verify", "result": "wrong_password"}

        # Simulate the tier expiry check
        now_str = datetime.now().strftime("%Y-%m-%d")
        tier = row["tier"]
        expires_at = row["expires_at"]

        # Simulate tier downgrade
        tier_step = "no_change"
        if expires_at and expires_at < now_str:
            tier = "free"
            tier_step = "downgraded"

        # Simulate get_user_daily_usage
        db2 = get_db(db_path)
        cur2 = db2.cursor()
        today_expr = "CURRENT_DATE" if _is_postgres() else "DATE('now')"
        try:
            cur2.execute(f"SELECT COUNT(*) as cnt FROM calculations WHERE user_id = %s AND DATE(created_at) = {today_expr}", (row["id"],)) \
                if _is_postgres() else \
                cur2.execute(f"SELECT COUNT(*) as cnt FROM calculations WHERE user_id = ? AND DATE(created_at) = {today_expr}", (row["id"],))
            cnt = cur2.fetchone()["cnt"]
        except Exception:
            cnt = 0
        db2.close()

        # Simulate create_access_token
        SECRET_KEY = "africa-zero-secret-key-change-in-production-2026"
        ALGORITHM = "HS256"
        token = jwt.encode(
            {"sub": str(row["id"]), "email": row["email"], "tier": tier, "is_admin": bool(row["is_admin"]),
             "exp": datetime.now(timezone.utc) + timedelta(days=30)},
            SECRET_KEY, algorithm=ALGORITHM
        )

        # Simulate UserResponse
        user_data = {
            "id": row["id"], "email": row["email"], "tier": tier,
            "is_admin": bool(row["is_admin"]), "subscribed_at": row["subscribed_at"],
            "expires_at": expires_at, "created_at": row["created_at"],
        }

        # Simulate AuthResponse
        FREE_DAILY_LIMIT = 3
        remaining_today = max(0, FREE_DAILY_LIMIT - cnt) if tier == "free" else 999999

        return {
            "is_postgres": _is_postgres(),
            "db_driver": "postgresql" if _is_postgres() else "sqlite",
            "user_found": True,
            "user_id": row["id"],
            "email": row["email"],
            "password_ok": pwd_ok,
            "tier": tier,
            "tier_step": tier_step,
            "is_admin": bool(row["is_admin"]),
            "expires_at": expires_at,
            "created_at": row["created_at"],
            "used_today": cnt,
            "remaining_today": remaining_today,
            "token_prefix": token[:20],
            "password_hash_prefix": row["password_hash"][:20],
        }
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
