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


_allow_origins = [
    "https://africa.zxqconsulting.com",
    "https://global2china.zxqconsulting.com",
    "https://frontend-nrlqfber2-johnzhangs-projects-50e83ec4.vercel.app",
    "https://africa-web-1.onrender.com",
    "https://africa-zero-frontend.vercel.app",
    "http://localhost:5173",
    "http://localhost:8000",
]
_allow_credentials = True

app = FastAPI(
    title="AfricaZero API",
    description="非洲零关税全链路决策平台 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/debug/calc-tariff")
def debug_calc_tariff():
    """Debug tariff calculation."""
    import traceback, json
    from app.services import tariff as tariff_service
    from app.models.database import get_db_path, get_db
    try:
        result = tariff_service.calculate_tariff(
            hs_code="0901",
            origin_country="ET",
            destination="CN",
            fob_value=240,
            db_path=get_db_path(),
        )
        bd = result.get("breakdown", {})
        total_val = bd.get("total_cost", 0) if isinstance(bd, dict) else 0
        json_str = json.dumps(result)
        conn = get_db(get_db_path())
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO calculations (user_id, product_name, hs_code, origin, destination, fob_value, result_json, total) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (1, "咖啡豆", "0901", "ET", "CN", 240, json_str, total_val)
        )
        conn.commit()
        conn.close()
        return {"success": True, "total": total_val}
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__, "tb": traceback.format_exc()[-800:]}


@app.get("/debug/calc-import")
def debug_calc_import():
    """Debug import cost calculation."""
    import traceback, json
    from app.services import tariff as tariff_service
    from app.models.database import get_db_path, get_db
    try:
        result = tariff_service.calculate_import_cost(
            product_name="咖啡生豆",
            quantity_kg=30,
            fob_per_kg=8,
            origin="ET",
            db_path=get_db_path(),
        )
        bd = result.get("breakdown")
        if bd and hasattr(bd, "model_dump"):
            bd_dict = bd.model_dump()
        else:
            bd_dict = bd or {}
        total_val = bd_dict.get("total_cost") or 0
        serializable = dict(result)
        serializable["breakdown"] = bd_dict
        json_str = json.dumps(serializable)
        conn = get_db(get_db_path())
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO calculations (user_id, product_name, hs_code, origin, destination, fob_value, result_json, total) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (1, "咖啡生豆", None, "ET", "CN", bd_dict.get("fob_value") or 0, json_str, total_val)
        )
        conn.commit()
        conn.close()
        return {"success": True, "total": total_val, "result_keys": list(result.keys())}
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__, "tb": traceback.format_exc()[-800:]}


@app.get("/debug/calc-outer")
def debug_calc_outer():
    """Debug the OUTER calculator router function."""
    import traceback, json
    from app.models.database import get_db_path, get_db, get_db as _get_db
    try:
        # Step 1: get tariff result
        from app.services import tariff as tariff_service
        result = tariff_service.calculate_tariff(
            hs_code="0901", origin_country="ET", destination="CN",
            fob_value=240, db_path=get_db_path(),
        )
        # Step 2: json.dumps
        json_str = json.dumps(result)
        return {"step1": "tariff ok", "step2": "json ok", "keys": list(result.keys())}
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__, "tb": traceback.format_exc()[-800:]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
