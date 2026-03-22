"""
API Key management router (enterprise tier).
"""
import os
from datetime import datetime
from pathlib import Path
import hashlib

from fastapi import APIRouter, HTTPException, Depends, Request
from app.models.database import get_db, generate_api_key, mask_api_key
from app.schemas import ApiKeyCreate, ApiKeyResponse, ApiKeyWithPlain
from app.routers.auth import get_current_user

DB_PATH = os.getenv("DATABASE_URL", "data/africa_zero.db")
DB_PATH = str(Path(DB_PATH).resolve())

router = APIRouter()


def _log_usage(
    db_path: str,
    user_id: int | None,
    api_key_id: int | None,
    endpoint: str,
    ip: str | None,
    ua: str | None,
    response_time_ms: int,
    status_code: int,
):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO usage_logs
           (user_id, api_key_id, endpoint, ip_address, user_agent, response_time_ms, status_code)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, api_key_id, endpoint, ip, ua, response_time_ms, status_code)
    )
    conn.commit()
    conn.close()


def _check_api_quota(db_path: str, user_id: int, api_key_id: int | None, tier: str) -> tuple[bool, str]:
    """Check daily API quota. Returns (allowed, error_message)."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db(db_path)
    cursor = conn.cursor()

    # Get rate limit
    if api_key_id:
        cursor.execute("SELECT rate_limit_day FROM api_keys WHERE id = ? AND is_active = 1", (api_key_id,))
    else:
        cursor.execute("SELECT tier FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return True, ""

    rate_limit = row["rate_limit_day"] if api_key_id else 100
    conn.close()

    # Count today's usage
    conn2 = get_db(db_path)
    cursor2 = conn2.cursor()
    if api_key_id:
        cursor2.execute(
            "SELECT COUNT(*) as cnt FROM usage_logs WHERE api_key_id = ? AND DATE(created_at) = ?",
            (api_key_id, today)
        )
    else:
        cursor2.execute(
            "SELECT COUNT(*) as cnt FROM usage_logs WHERE user_id = ? AND DATE(created_at) = ?",
            (user_id, today)
        )
    count = cursor2.fetchone()["cnt"]
    conn2.close()

    if count >= rate_limit:
        return False, f"今日API调用已达上限（{rate_limit}次/天），请明日再试"
    return True, ""


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(current_user: dict = Depends(get_current_user)):
    if current_user["tier"] != "enterprise":
        raise HTTPException(status_code=403, detail="仅企业版用户可使用API Key功能")

    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM api_keys WHERE user_id = ? AND is_active = 1 ORDER BY created_at DESC",
        (current_user["user_id"],)
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        ApiKeyResponse(
            id=r["id"],
            key_prefix=r["key_prefix"],
            name=r["name"],
            tier=r["tier"],
            rate_limit_day=r["rate_limit_day"],
            is_active=bool(r["is_active"]),
            last_used_at=r["last_used_at"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("/api-keys", response_model=ApiKeyWithPlain)
async def create_api_key(
    body: ApiKeyCreate,
    current_user: dict = Depends(get_current_user),
):
    if current_user["tier"] != "enterprise":
        raise HTTPException(status_code=403, detail="仅企业版用户可创建API Key")

    plain_key, key_hash = generate_api_key()

    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO api_keys (user_id, key_hash, key_prefix, name, tier, rate_limit_day, is_active)
           VALUES (?, ?, ?, ?, 'enterprise', ?, 1)""",
        (current_user["user_id"], key_hash, plain_key[:10], body.name, body.rate_limit_day)
    )
    conn.commit()
    key_id = cursor.lastrowid
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.close()

    return ApiKeyWithPlain(
        id=key_id,
        plain_key=plain_key,
        key_prefix=plain_key[:10],
        name=body.name,
        tier="enterprise",
        rate_limit_day=body.rate_limit_day,
        created_at=now,
    )


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: int, current_user: dict = Depends(get_current_user)):
    if current_user["tier"] != "enterprise":
        raise HTTPException(status_code=403, detail="仅企业版用户可管理API Key")

    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE api_keys SET is_active = 0 WHERE id = ? AND user_id = ?",
        (key_id, current_user["user_id"])
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()

    if not affected:
        raise HTTPException(status_code=404, detail="API Key不存在或无权删除")
    return {"message": "API Key已吊销"}


@router.get("/api-keys/{key_id}/usage")
async def get_key_usage(key_id: int, current_user: dict = Depends(get_current_user)):
    if current_user["tier"] != "enterprise":
        raise HTTPException(status_code=403, detail="仅企业版用户可查看API使用情况")

    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM api_keys WHERE id = ? AND user_id = ?",
        (key_id, current_user["user_id"])
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="API Key不存在")

    # Get last 30 days usage
    cursor.execute(
        """SELECT DATE(created_at) as day, COUNT(*) as calls
           FROM usage_logs WHERE api_key_id = ?
           GROUP BY day ORDER BY day DESC LIMIT 30""",
        (key_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    return {"usage": [dict(r) for r in rows]}


def verify_api_key(db_path: str, api_key: str) -> dict | None:
    """Verify an API key and return user info if valid."""
    try:
        parts = api_key.split("$")
        if len(parts) != 2:
            return None
        key_prefix, _ = parts
    except Exception:
        return None

    # Hash the plain key for comparison against stored hash
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT ak.id as key_id, ak.user_id, ak.rate_limit_day, ak.is_active,
                  u.email, u.tier, u.is_admin, u.is_active as user_active
           FROM api_keys ak
           JOIN users u ON u.id = ak.user_id
           WHERE ak.key_prefix = ? AND ak.key_hash = ?""",
        (key_prefix, key_hash)
    )
    row = cursor.fetchone()
    conn.close()

    if not row or not row["is_active"] or not row["user_active"]:
        return None

    return {
        "key_id": row["key_id"],
        "user_id": row["user_id"],
        "email": row["email"],
        "tier": row["tier"],
        "is_admin": bool(row["is_admin"]),
        "rate_limit_day": row["rate_limit_day"],
    }


def update_key_last_used(db_path: str, key_id: int):
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), key_id)
    )
    conn.commit()
    conn.close()
