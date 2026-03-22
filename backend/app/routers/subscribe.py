from fastapi import APIRouter, Query
from app.models.database import get_db, get_db_path
from datetime import datetime

DB_PATH = get_db_path()

router = APIRouter()


@router.get("/subscribe/check")
async def check_subscription(
    email: str = Query(default=None),
    wechat_id: str = Query(default=None),
):
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    if email:
        cursor.execute("SELECT * FROM users WHERE email = ? LIMIT 1", (email,))
    elif wechat_id:
        cursor.execute("SELECT * FROM users WHERE wechat_id = ? LIMIT 1", (wechat_id,))
    else:
        conn.close()
        return {"tier": "free", "expires_at": None, "remaining_queries": 3}

    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"tier": "free", "expires_at": None, "remaining_queries": 3}

    expires = row["expires_at"]
    now = datetime.now().strftime("%Y-%m-%d")

    if expires and expires < now:
        return {"tier": "free", "expires_at": None, "remaining_queries": 3}

    return {
        "tier": row["tier"],
        "expires_at": expires,
        "remaining_queries": None if row["tier"] != "free" else 3,
    }
