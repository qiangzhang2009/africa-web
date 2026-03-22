"""
Supplier discovery and management API.
"""
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional
from app.models.database import get_db, get_db_path
from app.routers.auth import get_current_user, get_optional_user

router = APIRouter()
DB_PATH = get_db_path()


# ─── Schemas ────────────────────────────────────────────────────────────────────

class Supplier(BaseModel):
    id: int
    name_zh: str
    name_en: Optional[str]
    country: str
    region: Optional[str]
    main_products: list[str]
    main_hs_codes: list[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    website: Optional[str]
    min_order_kg: Optional[float]
    payment_terms: Optional[str]
    export_years: int
    annual_export_tons: Optional[float]
    verified_chamber: bool
    verified_实地拜访: bool
    verified_sgs: bool
    rating_avg: float
    review_count: int
    status: str
    intro: Optional[str]
    certifications: list[str]


class SupplierListItem(BaseModel):
    id: int
    name_zh: str
    country: str
    region: Optional[str]
    main_products: list[str]
    main_hs_codes: list[str]
    export_years: int
    verified_chamber: bool
    rating_avg: float
    review_count: int
    status: str
    min_order_kg: Optional[float]


class SupplierSearchInput(BaseModel):
    country: Optional[str] = Field(None, description="原产国 ISO code")
    keyword: Optional[str] = Field(None, description="搜索关键词（产品/公司名）")
    hs_code: Optional[str] = Field(None, description="HS编码（支持前缀匹配）")
    verified_only: bool = Field(False, description="仅显示已认证供应商")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=50)


class SupplierSearchResult(BaseModel):
    suppliers: list[SupplierListItem]
    total: int
    page: int
    page_size: int


class SupplierReview(BaseModel):
    id: int
    supplier_id: int
    user_email: Optional[str]
    quality_score: float
    delivery_score: float
    communication_score: float
    comment: Optional[str]
    is_verified_deal: bool
    created_at: Optional[str]


class SupplierReviewCreate(BaseModel):
    supplier_id: int
    quality_score: float = Field(..., ge=1, le=5)
    delivery_score: float = Field(..., ge=1, le=5)
    communication_score: float = Field(..., ge=1, le=5)
    comment: str = ""
    is_verified_deal: bool = False


# ─── Helpers ────────────────────────────────────────────────────────────────────

def _parse_list_field(raw: str, default=None):
    if not raw:
        return default or []
    try:
        return json.loads(raw)
    except Exception:
        return [s.strip() for s in raw.split("|") if s.strip()]


def _supplier_row_to_model(r: dict) -> dict:
    return {
        "id": r["id"],
        "name_zh": r["name_zh"],
        "name_en": r["name_en"],
        "country": r["country"],
        "region": r["region"],
        "main_products": _parse_list_field(r["main_products"]),
        "main_hs_codes": _parse_list_field(r["main_hs_codes"]),
        "contact_email": r["contact_email"],
        "contact_phone": r["contact_phone"],
        "website": r["website"],
        "min_order_kg": r["min_order_kg"],
        "payment_terms": r["payment_terms"],
        "export_years": r["export_years"],
        "annual_export_tons": r["annual_export_tons"],
        "verified_chamber": bool(r["verified_chamber"]),
        "verified_实地拜访": bool(r["verified_实地拜访"]),
        "verified_sgs": bool(r["verified_sgs"]),
        "rating_avg": r["rating_avg"],
        "review_count": r["review_count"],
        "status": r["status"],
        "intro": r["intro"],
        "certifications": _parse_list_field(r["certifications"]),
    }


def _supplier_to_list_item(r: dict) -> dict:
    return {
        "id": r["id"],
        "name_zh": r["name_zh"],
        "country": r["country"],
        "region": r["region"],
        "main_products": _parse_list_field(r["main_products"]),
        "main_hs_codes": _parse_list_field(r["main_hs_codes"]),
        "export_years": r["export_years"],
        "verified_chamber": bool(r["verified_chamber"]),
        "rating_avg": r["rating_avg"],
        "review_count": r["review_count"],
        "status": r["status"],
        "min_order_kg": r["min_order_kg"],
    }


# ─── Routes ────────────────────────────────────────────────────────────────────

@router.get("/suppliers")
async def search_suppliers(
    country: Optional[str] = Query(None, description="原产国 ISO code"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    hs_code: Optional[str] = Query(None, description="HS编码前缀"),
    verified_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    """
    Search and filter suppliers.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    sql = "SELECT * FROM suppliers WHERE status != 'blocked'"
    count_sql = "SELECT COUNT(*) as cnt FROM suppliers WHERE status != 'blocked'"
    params = []
    count_params = []

    if country:
        sql += " AND country = ?"
        count_sql += " AND country = ?"
        params.append(country.upper())
        count_params.append(country.upper())

    if keyword:
        sql += " AND (name_zh LIKE ? OR name_en LIKE ? OR main_products LIKE ?)"
        count_sql += " AND (name_zh LIKE ? OR name_en LIKE ? OR main_products LIKE ?)"
        like_kw = f"%{keyword}%"
        params.extend([like_kw, like_kw, like_kw])
        count_params.extend([like_kw, like_kw, like_kw])

    if hs_code:
        sql += " AND main_hs_codes LIKE ?"
        count_sql += " AND main_hs_codes LIKE ?"
        params.append(f"%{hs_code}%")
        count_params.append(f"%{hs_code}%")

    if verified_only:
        sql += " AND verified_chamber = 1"
        count_sql += " AND verified_chamber = 1"

    # Total count
    cursor.execute(count_sql, count_params)
    total = cursor.fetchone()["cnt"]

    # Paginated results
    offset = (page - 1) * page_size
    sql += " ORDER BY verified_chamber DESC, export_years DESC, rating_avg DESC LIMIT ? OFFSET ?"
    params.extend([page_size, offset])
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    return {
        "suppliers": [_supplier_to_list_item(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/suppliers/countries")
async def list_supplier_countries():
    """
    List all countries that have suppliers in the database.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT s.country, ac.name_zh, ac.name_en,
                  COUNT(*) as supplier_count,
                  SUM(CASE WHEN s.verified_chamber = 1 THEN 1 ELSE 0 END) as verified_count
           FROM suppliers s
           LEFT JOIN africa_countries ac ON ac.code = s.country
           WHERE s.status != 'blocked'
           GROUP BY s.country
           ORDER BY supplier_count DESC"""
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "code": r["country"],
            "name_zh": r["name_zh"] or r["country"],
            "name_en": r["name_en"],
            "supplier_count": r["supplier_count"],
            "verified_count": r["verified_count"],
        }
        for r in rows
    ]


@router.get("/suppliers/categories")
async def list_supplier_categories():
    """
    List all product categories available from suppliers.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT main_hs_codes FROM suppliers WHERE status != 'blocked' AND main_hs_codes IS NOT NULL"""
    )
    rows = cursor.fetchall()
    conn.close()

    # Aggregate unique HS code prefixes
    prefixes = set()
    for r in rows:
        for code in r["main_hs_codes"].split("|"):
            code = code.strip()
            if code:
                prefixes.add(code[:4])

    return sorted(list(prefixes))


@router.get("/suppliers/{supplier_id}")
async def get_supplier(supplier_id: int):
    """
    Get detailed supplier information.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM suppliers WHERE id = ? AND status != 'blocked'", (supplier_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="供应商不存在")

    # Get country name
    conn2 = get_db(DB_PATH)
    cursor2 = conn2.cursor()
    cursor2.execute("SELECT name_zh FROM africa_countries WHERE code = ?", (row["country"],))
    country_row = cursor2.fetchone()
    conn2.close()

    result = _supplier_row_to_model(row)
    result["country_name_zh"] = country_row["name_zh"] if country_row else row["country"]

    return result


@router.get("/suppliers/{supplier_id}/reviews")
async def get_supplier_reviews(
    supplier_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
):
    """
    Get reviews for a specific supplier.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    # Verify supplier exists
    cursor.execute("SELECT id FROM suppliers WHERE id = ?", (supplier_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="供应商不存在")

    cursor.execute("SELECT COUNT(*) as cnt FROM supplier_reviews WHERE supplier_id = ?", (supplier_id,))
    total = cursor.fetchone()["cnt"]

    offset = (page - 1) * page_size
    cursor.execute(
        """SELECT * FROM supplier_reviews
           WHERE supplier_id = ?
           ORDER BY is_verified_deal DESC, created_at DESC
           LIMIT ? OFFSET ?""",
        (supplier_id, page_size, offset)
    )
    rows = cursor.fetchall()
    conn.close()

    return {
        "reviews": [
            {
                "id": r["id"],
                "supplier_id": r["supplier_id"],
                "user_email": r["user_email"],
                "quality_score": r["quality_score"],
                "delivery_score": r["delivery_score"],
                "communication_score": r["communication_score"],
                "comment": r["comment"],
                "is_verified_deal": bool(r["is_verified_deal"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/suppliers/{supplier_id}/reviews")
async def create_supplier_review(
    supplier_id: int,
    body: SupplierReviewCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Submit a review for a supplier. Requires login.
    """
    if body.supplier_id != supplier_id:
        raise HTTPException(status_code=400, detail="供应商ID不匹配")

    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    # Verify supplier
    cursor.execute("SELECT id, name_zh FROM suppliers WHERE id = ?", (supplier_id,))
    supplier = cursor.fetchone()
    if not supplier:
        conn.close()
        raise HTTPException(status_code=404, detail="供应商不存在")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """INSERT INTO supplier_reviews
           (supplier_id, user_id, user_email, quality_score, delivery_score,
            communication_score, comment, is_verified_deal, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            supplier_id, current_user["user_id"], current_user["email"],
            body.quality_score, body.delivery_score, body.communication_score,
            body.comment, 1 if body.is_verified_deal else 0, now
        )
    )
    review_id = cursor.lastrowid

    # Update supplier rating
    cursor.execute(
        """SELECT
               AVG(quality_score) as avg_quality,
               AVG(delivery_score) as avg_delivery,
               AVG(communication_score) as avg_comm,
               COUNT(*) as cnt
           FROM supplier_reviews WHERE supplier_id = ?""",
        (supplier_id,)
    )
    stats = cursor.fetchone()
    avg_rating = round((stats["avg_quality"] + stats["avg_delivery"] + stats["avg_comm"]) / 3, 1)
    cursor.execute(
        "UPDATE suppliers SET rating_avg = ?, review_count = ? WHERE id = ?",
        (avg_rating, stats["cnt"], supplier_id)
    )

    conn.commit()
    conn.close()

    return {
        "message": "评价已提交，感谢您的反馈",
        "review_id": review_id,
        "new_rating": avg_rating,
    }


@router.get("/suppliers/{supplier_id}/compare")
async def get_supplier_compare(supplier_id: int):
    """
    Get supplier detail with a cost comparison estimate.
    """
    supplier_resp = await get_supplier(supplier_id)

    # Find matching freight routes for this supplier
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT fr.*, ac.name_zh as country_name_zh
           FROM freight_routes fr
           LEFT JOIN africa_countries ac ON ac.code = fr.origin_country
           WHERE fr.origin_country = ? AND fr.dest_port = 'SHA' AND fr.is_active = 1
           ORDER BY fr.cost_min_usd ASC LIMIT 1""",
        (supplier_resp["country"],)
    )
    route = cursor.fetchone()
    conn.close()

    result = {
        "supplier": supplier_resp,
        "recommended_route": None,
        "estimated_freight": None,
    }

    if route:
        result["recommended_route"] = {
            "origin_port": route["origin_port"],
            "origin_port_zh": route["origin_port_zh"],
            "dest_port": route["dest_port"],
            "dest_port_zh": route["dest_port_zh"],
            "transit_days": f"{route['transit_days_min']}-{route['transit_days_max']}天",
            "cost_range_usd": f"${route['cost_min_usd']:,.0f}-${route['cost_max_usd']:,.0f}",
        }
        mid_cost = (route["cost_min_usd"] + route["cost_max_usd"]) / 2
        result["estimated_freight"] = {
            "sea_freight_usd": round(mid_cost, 2),
            "sea_freight_cny": round(mid_cost * 7.25, 2),
            "insurance_usd": round(mid_cost * 0.005, 2),
            "clearance_cny": 800,
            "total_estimate_cny": round(mid_cost * 1.005 * 7.25 + 800 + 500, 2),
        }

    return result
