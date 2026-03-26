from fastapi import APIRouter, Query
from app.models.database import get_db, get_db_path, _is_postgres
from app.schemas import HSSearchResult
from typing import Optional

# HS编码零关税状态映射：品名关键词 → (是否零关税, 说明文字)
ZERO_TARIFF_MAP = {
    "咖啡": True,
    "可可": True,
    "坚果": True,
    "矿产": True,
    "油籽": True,
    "茶叶": True,
    "皮革": True,
    "木材": True,
    "香料": True,
    "棉麻": True,
    "油脂": True,
    "橡胶": True,
    "水产": True,
    "食品": True,
    "钢铁": False,   # 钢铁不在零关税范围
    "汽车": False,   # 汽车不在零关税范围，且需3C认证
    "电子": False,   # 手机/电子需3C认证
    "服装": False,   # 服装纺织品不在零关税范围
    "塑料": False,   # 塑料部分品类零关税
}

# 非零关税品类的引导说明
NON_ZERO_GUIDANCE = {
    "钢铁": "注意：钢铁类产品(72章)目前不在非洲零关税政策范围内，进口需缴纳6-8%的MFN关税。",
    "汽车": "注意：汽车(87章)目前不在非洲零关税政策范围内，且整车进口需3C认证，门槛较高。建议关注矿产、农产品等零关税品类。",
    "电子": "注意：手机及电子产品(85章)进口需3C认证，门槛较高。建议关注矿产品、农产品等零关税品类。",
    "服装": "注意：服装纺织品(61-62章)目前不在非洲零关税政策范围内。建议关注皮革、棉纤维等零关税品类。",
    "塑料": "注意：初级塑料(39章)部分品类可享零关税，上表已标注MFN税率，请以实际查询结果为准。",
}

DB_PATH = get_db_path()

router = APIRouter()


def _normalize_hs_sql(col: str) -> str:
    """Return SQL to normalize HS code column for search (handles both SQLite and PostgreSQL)."""
    # PostgreSQL REPLACE works the same way as SQLite
    return f"REPLACE(REPLACE(REPLACE(REPLACE({col}, '.', ''), ' ', ''), '-', ''), '*', '')"


def _normalize_hs(code: str) -> str:
    return code.replace(".", "").replace(" ", "").replace("-", "")


def _format_hs(code: str) -> str:
    c = _normalize_hs(code)
    if len(c) <= 4:
        return c
    return ".".join(c[i*2:i*2+2] for i in range((len(c)+1)//2))


def _get_zero_tariff_status(category: str | None) -> dict:
    """判断品类是否享受零关税。"""
    if not category:
        return {"zero_tariff": None, "guidance": None}
    status = ZERO_TARIFF_MAP.get(category, None)
    if status is False:
        return {"zero_tariff": False, "guidance": NON_ZERO_GUIDANCE.get(category, None)}
    return {"zero_tariff": status, "guidance": None}


@router.get("/hs-codes/search")
async def search_hs_codes(q: str = Query(..., min_length=1), limit: int = Query(default=10, le=50)):
    """Search HS codes by Chinese name or HS code number."""
    try:
        conn = get_db(DB_PATH)
        cursor = conn.cursor()
    except Exception as e:
        return {"results": [], "error": f"数据库连接失败: {str(e)}"}

    normalized = _normalize_hs(q)
    results: list[dict] = []

    # Build normalized column expressions for both SQLite and PostgreSQL
    norm_hs_10 = _normalize_hs_sql("hs_10")
    norm_hs_8 = _normalize_hs_sql("hs_8")
    norm_hs_6 = _normalize_hs_sql("hs_6")
    norm_hs_4 = _normalize_hs_sql("hs_4")

    # Exact or prefix HS code match
    try:
        cursor.execute(
            f"""
            SELECT * FROM hs_codes
            WHERE {norm_hs_10} LIKE ?
               OR {norm_hs_8} LIKE ?
               OR {norm_hs_6} LIKE ?
               OR {norm_hs_4} LIKE ?
            LIMIT ?
            """,
            (normalized + "%", normalized + "%", normalized + "%", normalized + "%", limit)
        )
        for row in cursor.fetchall():
            results.append(dict(row))
    except Exception as e:
        # Log error for debugging but don't fail
        print(f"HS code search error (code match): {e}")

    # Name fuzzy match
    if len(results) < limit:
        try:
            cursor.execute(
                "SELECT * FROM hs_codes WHERE name_zh LIKE ? OR category LIKE ? LIMIT ?",
                (f"%{q}%", f"%{q}%", limit - len(results))
            )
            for row in cursor.fetchall():
                if not any(r["hs_10"] == dict(row)["hs_10"] for r in results):
                    results.append(dict(row))
        except Exception as e:
            print(f"HS code search error (name match): {e}")

    conn.close()

    # 构建返回结果，添加零关税状态
    formatted_results = []
    has_non_zero = False
    guidance_messages: list[str] = []

    for r in results[:limit]:
        tariff_info = _get_zero_tariff_status(r.get("category"))
        result_item = {
            "hs_10": r.get("hs_10"),
            "name_zh": r["name_zh"],
            "mfn_rate": r["mfn_rate"],
            "category": r.get("category"),
            "match_score": 1.0,
            "zero_tariff": tariff_info["zero_tariff"],
            "category_guidance": tariff_info["guidance"],
        }
        formatted_results.append(result_item)
        if tariff_info["zero_tariff"] is False:
            has_non_zero = True
        if tariff_info["guidance"] and tariff_info["guidance"] not in guidance_messages:
            guidance_messages.append(tariff_info["guidance"])

    # 判断是否有非零关税品类，添加通用引导
    summary_guidance = None
    if has_non_zero and guidance_messages:
        summary_guidance = "提示：以上品类中，非零关税项已标注，进口需缴纳MFN关税。部分品类（如汽车、电子)另有3C认证要求，详情请查看选品清单。"

    return {
        "results": formatted_results,
        "has_non_zero_tariff": has_non_zero,
        "summary_guidance": summary_guidance,
    }
