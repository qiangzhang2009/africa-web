from fastapi import APIRouter, Query
from app.models.database import get_db
from app.schemas import HSSearchResult
from typing import Optional
import os
from pathlib import Path

DB_PATH = os.getenv("DATABASE_URL", "data/africa_zero.db")
DB_PATH = str(Path(DB_PATH).resolve())

router = APIRouter()


def _normalize_hs(code: str) -> str:
    return code.replace(".", "").replace(" ", "").replace("-", "")


def _format_hs(code: str) -> str:
    c = _normalize_hs(code)
    if len(c) <= 4:
        return c
    return ".".join(c[i*2:i*2+2] for i in range((len(c)+1)//2))


@router.get("/hs-codes/search")
async def search_hs_codes(q: str = Query(..., min_length=1), limit: int = Query(default=10, le=50)):
    """Search HS codes by Chinese name or HS code number."""
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    normalized = _normalize_hs(q)

    results: list[dict] = []

    # Exact or prefix HS code match
    cursor.execute(
        """
        SELECT * FROM hs_codes
        WHERE REPLACE(REPLACE(REPLACE(REPLACE(hs_10, '.', ''), ' ', ''), '-', ''), '*', '') LIKE ?
           OR REPLACE(REPLACE(REPLACE(REPLACE(hs_8, '.', ''), ' ', ''), '-', ''), '*', '') LIKE ?
           OR REPLACE(REPLACE(REPLACE(REPLACE(hs_6, '.', ''), ' ', ''), '-', ''), '*', '') LIKE ?
           OR REPLACE(REPLACE(REPLACE(REPLACE(hs_4, '.', ''), ' ', ''), '-', ''), '*', '') LIKE ?
        LIMIT ?
        """,
        (normalized + "%", normalized + "%", normalized + "%", normalized + "%", limit)
    )
    for row in cursor.fetchall():
        results.append(dict(row))

    # Name fuzzy match
    if len(results) < limit:
        cursor.execute(
            "SELECT * FROM hs_codes WHERE name_zh LIKE ? LIMIT ?",
            (f"%{q}%", limit - len(results))
        )
        for row in cursor.fetchall():
            if not any(r["hs_10"] == dict(row)["hs_10"] for r in results):
                results.append(dict(row))

    conn.close()

    return {
        "results": [
            {
                "hs_10": r.get("hs_10"),
                "name_zh": r["name_zh"],
                "mfn_rate": r["mfn_rate"],
                "category": r.get("category"),
                "match_score": 1.0,
            }
            for r in results[:limit]
        ]
    }
