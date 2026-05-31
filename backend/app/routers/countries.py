
from fastapi import APIRouter, Query

from app.models.database import get_db, get_db_path

DB_PATH = get_db_path()

router = APIRouter()


@router.get("/countries")
async def list_countries(market: str | None = Query(default=None)):
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
