"""
Market Analysis / Product Selection API.
Provides curated product recommendations for importing from Africa to China.
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from app.models.database import get_db, get_db_path

router = APIRouter()
DB_PATH = get_db_path()


class MarketProduct(BaseModel):
    id: int
    category: str
    product_name_zh: str
    product_name_en: Optional[str]
    main_hs_codes: str
    origin_countries: str
    target_china_market: str
    import_requirements: Optional[str]
    zero_tariff_china: bool
    tariff_rate: float
    market_size_usd: Optional[str]
    growth_rate: Optional[str]
    top_importers: Optional[str]
    supplier_countries: Optional[str]
    key_suppliers: Optional[str]
    certification_needs: Optional[str]
    logistics_notes: Optional[str]
    risk_factors: Optional[str]
    recommendation: Optional[str]
    status: str


class MarketCategoryStat(BaseModel):
    category: str
    product_count: int


@router.get("/market-analysis/products")
async def list_market_products(
    category: Optional[str] = Query(None, description="按品类筛选"),
    featured: bool = Query(False, description="仅显示推荐品类"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    """
    List all market analysis products with optional filtering.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    sql = "SELECT * FROM market_analysis WHERE status != 'hidden'"
    count_sql = "SELECT COUNT(*) as cnt FROM market_analysis WHERE status != 'hidden'"
    params = []
    count_params = []

    if category:
        sql += " AND category = ?"
        count_sql += " AND category = ?"
        params.append(category)
        count_params.append(category)

    if featured:
        sql += " AND status = 'featured'"
        count_sql += " AND status = 'featured'"

    if search:
        sql += " AND (product_name_zh LIKE ? OR product_name_en LIKE ? OR category LIKE ? OR origin_countries LIKE ?)"
        count_sql += " AND (product_name_zh LIKE ? OR product_name_en LIKE ? OR category LIKE ? OR origin_countries LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like, like])
        count_params.extend([like, like, like, like])

    cursor.execute(count_sql, count_params)
    total = cursor.fetchone()["cnt"]

    offset = (page - 1) * page_size
    sql += " ORDER BY status='featured' DESC, category, product_name_zh LIMIT ? OFFSET ?"
    params.extend([page_size, offset])
    cursor.execute(sql, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "products": [
            {
                "id": r["id"],
                "category": r["category"],
                "product_name_zh": r["product_name_zh"],
                "product_name_en": r.get("product_name_en"),
                "main_hs_codes": r["main_hs_codes"],
                "origin_countries": r["origin_countries"],
                "target_china_market": r["target_china_market"],
                "import_requirements": r.get("import_requirements"),
                "zero_tariff_china": bool(r.get("zero_tariff_china")),
                "tariff_rate": r.get("tariff_rate") or 0,
                "market_size_usd": r.get("market_size_usd"),
                "growth_rate": r.get("growth_rate"),
                "top_importers": r.get("top_importers"),
                "supplier_countries": r.get("supplier_countries"),
                "key_suppliers": r.get("key_suppliers"),
                "certification_needs": r.get("certification_needs"),
                "logistics_notes": r.get("logistics_notes"),
                "risk_factors": r.get("risk_factors"),
                "recommendation": r.get("recommendation"),
                "status": r.get("status") or "active",
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/market-analysis/categories")
async def list_categories():
    """
    List all product categories with counts.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT category, COUNT(*) as product_count
           FROM market_analysis
           WHERE status != 'hidden'
           GROUP BY category
           ORDER BY product_count DESC"""
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


@router.get("/market-analysis/products/{product_id}")
async def get_market_product(product_id: int):
    """
    Get detailed market analysis for a specific product.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM market_analysis WHERE id = ? AND status != 'hidden'",
        (product_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="产品不存在")

    r = dict(row)
    return {
        "id": r["id"],
        "category": r["category"],
        "product_name_zh": r["product_name_zh"],
        "product_name_en": r.get("product_name_en"),
        "main_hs_codes": r["main_hs_codes"],
        "origin_countries": r["origin_countries"],
        "target_china_market": r["target_china_market"],
        "import_requirements": r.get("import_requirements"),
        "zero_tariff_china": bool(r.get("zero_tariff_china")),
        "tariff_rate": r.get("tariff_rate") or 0,
        "market_size_usd": r.get("market_size_usd"),
        "growth_rate": r.get("growth_rate"),
        "top_importers": r.get("top_importers"),
        "supplier_countries": r.get("supplier_countries"),
        "key_suppliers": r.get("key_suppliers"),
        "certification_needs": r.get("certification_needs"),
        "logistics_notes": r.get("logistics_notes"),
        "risk_factors": r.get("risk_factors"),
        "recommendation": r.get("recommendation"),
        "status": r.get("status") or "active",
    }
