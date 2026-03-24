"""
Admin router — user management, subscription activation, analytics.
Only accessible by is_admin=True users.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from app.models.database import get_db, get_db_path, hash_password, sql_now, sql_date_sub_days, sql_date_add_days, _adapt_insert, _is_postgres
from app.schemas import UserResponse, SubscriptionResponse
from app.routers.auth import get_current_user

DB_PATH = get_db_path()

router = APIRouter()


def _require_admin(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


class AdminUpdateUser(BaseModel):
    tier: Optional[str] = None
    expires_at: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class AdminCreateUser(BaseModel):
    email: str
    password: str
    tier: str = "free"
    expires_at: Optional[str] = None


class AdminCreateSubscription(BaseModel):
    user_id: int
    tier: str
    amount: float = 0
    payment_method: Optional[str] = None
    payment_channel: str = "manual"


# ─── User Management ──────────────────────────────────────────────────────────

@router.get("/admin/users", tags=["Admin"])
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tier: Optional[str] = None,
    search: Optional[str] = None,
    _: dict = Depends(_require_admin),
):
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    conditions = []
    params = []
    if tier:
        conditions.append("u.tier = ?")
        params.append(tier)
    if search:
        conditions.append("(u.email LIKE ? OR u.wechat_id LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # Count total
    cursor.execute(f"SELECT COUNT(*) as cnt FROM users u {where_clause}", params)
    total = cursor.fetchone()["cnt"]

    # Fetch page
    offset = (page - 1) * page_size
    cursor.execute(
        f"""SELECT u.*,
                   s.id as sub_id, s.tier as sub_tier, s.amount, s.status,
                   s.started_at as sub_started, s.expires_at as sub_expires,
                   (SELECT COUNT(*) FROM sub_accounts sa WHERE sa.parent_user_id = u.id AND sa.is_active = 1) as sub_count,
                   (SELECT COUNT(*) FROM api_keys ak WHERE ak.user_id = u.id AND ak.is_active = 1) as api_key_count
            FROM users u
            LEFT JOIN subscriptions s ON s.id = (
                SELECT id FROM subscriptions WHERE user_id = u.id ORDER BY created_at DESC LIMIT 1
            )
            {where_clause}
            ORDER BY u.created_at DESC
            LIMIT ? OFFSET ?""",
        params + [page_size, offset]
    )
    rows = cursor.fetchall()
    conn.close()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "users": [
            {
                "id": r["id"],
                "email": r["email"],
                "tier": r["tier"],
                "is_admin": bool(r["is_admin"]),
                "is_active": bool(r["is_active"]),
                "subscribed_at": r["subscribed_at"],
                "expires_at": r["expires_at"],
                "created_at": r["created_at"],
                "latest_subscription": {
                    "id": r["sub_id"],
                    "tier": r["sub_tier"],
                    "amount": r["amount"],
                    "status": r["status"],
                    "started_at": r["sub_started"],
                    "expires_at": r["sub_expires"],
                } if r["sub_id"] else None,
                "sub_accounts_count": r["sub_count"],
                "api_keys_count": r["api_key_count"],
            }
            for r in rows
        ],
    }


@router.get("/admin/users/{user_id}", tags=["Admin"])
async def get_user(user_id: int, _: dict = Depends(_require_admin)):
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="用户不存在")

    # Get subscriptions
    cursor.execute(
        "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
        (user_id,)
    )
    subs = cursor.fetchall()

    # Get sub-accounts
    cursor.execute(
        "SELECT * FROM sub_accounts WHERE parent_user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    sub_accounts = cursor.fetchall()

    # Get API keys
    cursor.execute(
        "SELECT * FROM api_keys WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    api_keys = cursor.fetchall()

    conn.close()

    return {
        "user": dict(row),
        "subscriptions": [dict(s) for s in subs],
        "sub_accounts": [dict(sa) for sa in sub_accounts],
        "api_keys": [
            {**dict(ak), "key_hash": ak["key_hash"][:10] + "***"}
            for ak in api_keys
        ],
    }


@router.patch("/admin/users/{user_id}", tags=["Admin"])
async def update_user(user_id: int, body: AdminUpdateUser, _: dict = Depends(_require_admin)):
    updates = []
    params = []
    if body.tier is not None:
        updates.append("tier = ?")
        params.append(body.tier)
    if body.expires_at is not None:
        updates.append("expires_at = ?")
        params.append(body.expires_at)
    if body.is_active is not None:
        updates.append("is_active = ?")
        params.append(int(body.is_active))
    if body.is_admin is not None:
        updates.append("is_admin = ?")
        params.append(int(body.is_admin))

    if not updates:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    params.append(user_id)
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="用户不存在")
    cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return {"message": "用户已更新"}


@router.post("/admin/users", tags=["Admin"])
async def create_user(body: AdminCreateUser, _: dict = Depends(_require_admin)):
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (body.email.lower().strip(),))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="该邮箱已存在")

    password_hash = hash_password(body.password)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    expires_at = body.expires_at

    cursor.execute(
        _adapt_insert(
            """INSERT INTO users (email, password_hash, tier, subscribed_at, expires_at, is_admin, is_active)
               VALUES (?, ?, ?, ?, ?, 0, 1)"""
        ),
        (body.email.lower().strip(), password_hash, body.tier, now, expires_at)
    )
    conn.commit()
    user_id = cursor.fetchone()["id"] if _is_postgres() else cursor.lastrowid
    conn.close()
    return {"id": user_id, "email": body.email.lower().strip(), "tier": body.tier}


@router.post("/admin/subscriptions", response_model=SubscriptionResponse, tags=["Admin"])
async def admin_create_subscription(body: AdminCreateSubscription, _: dict = Depends(_require_admin)):
    if body.tier not in ("free", "pro", "enterprise"):
        raise HTTPException(status_code=400, detail="无效的订阅方案")

    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE id = ?", (body.user_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="用户不存在")

    now = datetime.now()
    started_at = now.strftime("%Y-%m-%d")
    duration = 365 if body.tier != "free" else None
    expires_at = (now + timedelta(days=duration)).strftime("%Y-%m-%d") if duration else None

    cursor.execute(
        _adapt_insert(
            """INSERT INTO subscriptions
               (user_id, tier, amount, payment_method, payment_channel, status, started_at, expires_at)
               VALUES (?, ?, ?, ?, ?, 'active', ?, ?)"""
        ),
        (body.user_id, body.tier, body.amount, body.payment_method, body.payment_channel, started_at, expires_at)
    )
    sub_id = cursor.fetchone()["id"] if _is_postgres() else cursor.lastrowid
    conn.commit()

    cursor.execute(
        "UPDATE users SET tier = ?, subscribed_at = ?, expires_at = ? WHERE id = ?",
        (body.tier, started_at, expires_at, body.user_id)
    )
    conn.commit()
    conn.close()

    return SubscriptionResponse(
        id=sub_id,
        tier=body.tier,
        amount=body.amount,
        currency="CNY",
        payment_method=body.payment_method,
        payment_channel=body.payment_channel,
        status="active",
        started_at=started_at,
        expires_at=expires_at,
        auto_renew=False,
    )


# ─── Analytics ────────────────────────────────────────────────────────────────

@router.get("/admin/stats", tags=["Admin"])
async def get_stats(_: dict = Depends(_require_admin)):
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM users")
    total_users = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE tier != 'free' AND is_active = 1")
    paying_users = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE tier = 'pro'")
    pro_users = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE tier = 'enterprise'")
    enterprise_users = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM api_keys WHERE is_active = 1")
    api_keys = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM sub_accounts WHERE is_active = 1")
    sub_accounts = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM subscriptions WHERE status = 'active'")
    active_subs = cursor.fetchone()["cnt"]

    # Revenue
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM subscriptions"
    )
    total_revenue = cursor.fetchone()["total"]

    # New users this week
    cursor.execute(
        f"SELECT COUNT(*) as cnt FROM users WHERE DATE(created_at) >= {sql_date_sub_days(7)}"
    )
    new_users_week = cursor.fetchone()["cnt"]

    # Expiring soon (next 7 days)
    cursor.execute(
        f"SELECT COUNT(*) as cnt FROM users WHERE expires_at BETWEEN {sql_now()} AND {sql_date_add_days(7)} AND tier != 'free'"
    )
    expiring_soon = cursor.fetchone()["cnt"]

    conn.close()

    return {
        "total_users": total_users,
        "paying_users": paying_users,
        "pro_users": pro_users,
        "enterprise_users": enterprise_users,
        "api_keys_active": api_keys,
        "sub_accounts_active": sub_accounts,
        "active_subscriptions": active_subs,
        "total_revenue": total_revenue,
        "new_users_this_week": new_users_week,
        "expiring_soon_7d": expiring_soon,
    }
