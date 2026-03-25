"""
AfricaZero — FastAPI Backend
Main entry point. Routes are mounted in app/routers/.
"""
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


_allow_origins = [
    "https://africa.zxqconsulting.com",
    "https://global2china.zxqconsulting.com",
    "https://frontend-nrlqfber2-johnzhangs-projects-50e83ec4.vercel.app",
    "https://africa-web-1.onrender.com",
    "https://africa-web-wuxs.onrender.com",
    "https://africa-zero-frontend.vercel.app",
    "http://localhost:5173",
    "http://localhost:8000",
]

app = FastAPI(
    title="AfricaZero API",
    description="非洲零关税全链路决策平台 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/debug/db-status")
def debug_db_status():
    """Debug endpoint to check database seed status."""
    from app.models.database import get_db, get_db_path
    db_path = get_db_path()
    conn = get_db(db_path)
    cursor = conn.cursor()

    def count_table(name):
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {name}")
            return cursor.fetchone()[0]
        except Exception as e:
            return f"error: {str(e)}"

    status = {
        "db_path": db_path,
        "is_postgres": str(db_path).startswith("postgres"),
        "tables": {
            "africa_countries": count_table("africa_countries"),
            "hs_codes": count_table("hs_codes"),
            "freight_routes": count_table("freight_routes"),
            "cert_guides": count_table("cert_guides"),
            "suppliers": count_table("suppliers"),
            "users": count_table("users"),
        }
    }
    conn.close()
    return status


@app.post("/debug/reinit-db")
def debug_reinit_db():
    """Force reinitialize database schema and seed data."""
    from app.models.database import get_db_path, init_db, seed_admin_user
    try:
        db_path = get_db_path()
        init_db(db_path)
        seed_admin_user(db_path)
        return {"status": "ok", "message": "Database reinitialized successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
