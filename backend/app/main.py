"""
AfricaZero — FastAPI Backend
Main entry point. Routes are mounted in app/routers/.
"""
import json
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.routers import calculator, hs_codes, countries, subscribe
from app.routers.auth import router as auth_router
from app.routers.subscription import router as subscription_router
from app.routers.api_keys import router as api_keys_router
from app.routers.admin import router as admin_router
from app.routers.freight import router as freight_router
from app.routers.certificate import router as certificate_router
from app.routers.suppliers import router as suppliers_router
from app.routers.market_analysis import router as market_analysis_router

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
app.include_router(market_analysis_router, prefix="/api/v1", tags=["市场选品分析"])


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
            "market_analysis": count_table("market_analysis"),
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


@app.get("/debug/export-suppliers")
def debug_export_suppliers():
    """Export all suppliers as JSON for backup or sync."""
    from app.models.database import get_db, get_db_path
    db_path = get_db_path()
    conn = get_db(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM suppliers ORDER BY id")
        rows = [dict(r) for r in cursor.fetchall()]
        return {"count": len(rows), "suppliers": rows}
    finally:
        conn.close()


@app.get("/debug/export-all-data")
def debug_export_all_data():
    """Export all reference data as JSON."""
    from app.models.database import get_db, get_db_path
    db_path = get_db_path()
    conn = get_db(db_path)
    cursor = conn.cursor()
    try:
        def get_table(name):
            try:
                cursor.execute(f"SELECT * FROM {name}")
                cols = [d[0] for d in cursor.description]
                rows = []
                for row in cursor.fetchall():
                    rows.append(dict(zip(cols, row)))
                return rows
            except Exception as e:
                return {"error": str(e)}

        return {
            "africa_countries": get_table("africa_countries"),
            "hs_codes": get_table("hs_codes"),
            "freight_routes": get_table("freight_routes"),
            "cert_guides": get_table("cert_guides"),
            "suppliers": get_table("suppliers"),
            "market_analysis": get_table("market_analysis"),
        }
    finally:
        conn.close()


class DebugUpsertData(BaseModel):
    africa_countries: list[dict] = []
    hs_codes: list[dict] = []
    cert_guides: list[dict] = []
    suppliers: list[dict] = []
    policy_rules: list[dict] = []
    supplier_reviews: list[dict] = []
    freight_routes: list[dict] = []
    market_analysis: list[dict] = []


@app.post("/debug/upsert-data")
def debug_upsert_data(body: DebugUpsertData):
    """Bulk upsert reference data. Deletes all existing rows and inserts new ones."""
    from app.models.database import get_db, get_db_path
    db_path = get_db_path()
    conn = get_db(db_path)
    cursor = conn.cursor()
    is_pg = str(db_path).startswith("postgres")

    def _adapt(sql: str) -> str:
        if is_pg:
            return sql.replace("?", "%s")
        return sql

    def _serialize(val):
        if val is None:
            return None
        if isinstance(val, (dict, list)):
            return json.dumps(val, ensure_ascii=False)
        return str(val) if not isinstance(val, (int, float)) else val

    def upsert_table(table: str, rows: list[dict]) -> int:
        if not rows:
            return 0
        # Remove 'id' from columns (let DB auto-generate)
        cols = [c for c in rows[0].keys() if c != "id"]
        placeholders = ", ".join(["?"] * len(cols))
        insert_sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
        sql = _adapt(insert_sql)
        try:
            cursor.execute(f"DELETE FROM {table}")
            for row in rows:
                vals = [_serialize(row.get(c)) for c in cols]
                cursor.execute(sql, vals)
            return len(rows)
        except Exception as e:
            raise Exception(f"{table}: {e}")

    results = {}
    try:
        results["africa_countries"] = upsert_table("africa_countries", body.africa_countries)
        results["hs_codes"] = upsert_table("hs_codes", body.hs_codes)
        results["cert_guides"] = upsert_table("cert_guides", body.cert_guides)
        results["suppliers"] = upsert_table("suppliers", body.suppliers)
        results["policy_rules"] = upsert_table("policy_rules", body.policy_rules)
        results["supplier_reviews"] = upsert_table("supplier_reviews", body.supplier_reviews)
        results["freight_routes"] = upsert_table("freight_routes", body.freight_routes)
        results["market_analysis"] = upsert_table("market_analysis", body.market_analysis)
        conn.commit()
        return {"status": "ok", "inserted": results}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
