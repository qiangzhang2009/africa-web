from fastapi import APIRouter, Query
from app.models.database import get_db
from app.schemas import Country
from typing import Optional
import os
from pathlib import Path

DB_PATH = os.getenv("DATABASE_URL", "data/africa_zero.db")
DB_PATH = str(Path(DB_PATH).resolve())

router = APIRouter()


@router.get("/countries")
async def list_countries(market: Optional[str] = Query(default=None)):
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    if market == "CN":
        cursor.execute("SELECT * FROM africa_countries ORDER BY name_zh")
    elif market == "EU":
        cursor.execute("SELECT * FROM africa_countries WHERE has_epa = 1 ORDER BY name_zh")
    else:
        cursor.execute("SELECT * FROM africa_countries ORDER BY name_zh")

    rows = cursor.fetchall()
    conn.close()

    return {
        "countries": [
            {
                "id": r["id"],
                "code": r["code"],
                "name_zh": r["name_zh"],
                "name_en": r["name_en"],
                "in_afcfta": bool(r["in_afcfta"]),
                "has_epa": bool(r["has_epa"]),
            }
            for r in rows
        ]
    }
