"""
Debug routers — mounted at /api/v1 prefix (also accessible at root for local dev).

Vercel rewrites /api/v1/debug/* → OnRender, so these must be at /api/v1 prefix.
Legacy root-level /debug/* routes are kept for local dev compatibility.
"""
import httpx
from fastapi import APIRouter

router = APIRouter()


def _db_status():
    """Shared logic for /debug/db-status (both prefixed and root versions)."""
    from app.models.database import get_db, get_db_path

    db_path = get_db_path()
    try:
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
                "market_analysis": count_table("market_analysis"),
                "policy_rules": count_table("policy_rules"),
                "supplier_reviews": count_table("supplier_reviews"),
                "suppliers": count_table("suppliers"),
                "users": count_table("users"),
            },
        }
        conn.close()
        return status
    except Exception as e:
        return {
            "db_path": db_path,
            "is_postgres": str(db_path).startswith("postgres"),
            "error": str(e),
            "tables": {},
        }


# ─── /api/v1/debug/db-status ────────────────────────────────────────────────
# This is the canonical endpoint for the frontend DatabasePage.
# Vercel rewrites /api/v1/debug/db-status → OnRender, so this prefix is required.
@router.get("/debug/db-status")
def api_v1_debug_db_status():
    return _db_status()


# ─── /api/v1/geo/ip ─────────────────────────────────────────────────────────
# Proxy for ipapi.co to avoid browser CORS issues.
# The zxqTrack SDK fetches https://ipapi.co/json/ for geolocation.
# ipapi.co doesn't send Access-Control-Allow-Origin, so the browser blocks it.
# This endpoint calls ipapi.co server-side (no CORS) and returns the result.
@router.get("/geo/ip")
async def geo_ip():
    """
    Returns the server's public IP + geolocation from ipapi.co.
    Compatible with the /json/ endpoint response shape.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("https://ipapi.co/json/")
            resp.raise_for_status()
            return resp.json()
    except httpx.TimeoutException:
        return {"error": "timeout", "message": "ipapi.co request timed out"}
    except httpx.HTTPStatusError as e:
        return {"error": "http_error", "message": str(e)}
    except Exception as e:
        return {"error": "unknown", "message": str(e)}
