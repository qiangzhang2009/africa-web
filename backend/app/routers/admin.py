"""
Admin router — user management, subscription activation, analytics.
Only accessible by is_admin=True users.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from app.models.database import (
    get_db, get_db_path, hash_password,
    sql_now, sql_date_sub_days, sql_date_add_days, sql_cast_date,
    _adapt_insert, _is_postgres,
)
from app.schemas import SubscriptionResponse
from app.routers.auth import get_current_user

DB_PATH = get_db_path()
PH = "%s" if _is_postgres() else "?"

router = APIRouter()


def _require_admin(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


def _pg(sql: str) -> str:
    """Convert SQLite-style ? placeholders to %s for PostgreSQL."""
    return sql.replace("?", "%s") if _is_postgres() else sql


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
    notes: Optional[str] = None


# ─── Tier & Expiry Change ─────────────────────────────────────────────────────

class TierChangeRequest(BaseModel):
    tier: str
    expires_at: Optional[str] = None
    reason: Optional[str] = None
    duration_days: Optional[int] = None


@router.post("/admin/users/{user_id}/tier", tags=["Admin"])
async def change_user_tier(
    user_id: int,
    body: TierChangeRequest,
    _: dict = Depends(_require_admin),
):
    """
    Change a user's tier with optional custom expiry.
    Supports upgrade AND downgrade.
    Duration_days overrides expires_at if provided.
    """
    if body.tier not in ("free", "pro", "enterprise"):
        raise HTTPException(status_code=400, detail="无效的订阅方案")

    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    # Verify user exists
    cursor.execute(_pg("SELECT id, email FROM users WHERE id = ?"), (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="用户不存在")

    # Resolve expiry
    if body.duration_days is not None:
        expires_at = (datetime.now() + timedelta(days=body.duration_days)).strftime("%Y-%m-%d")
    elif body.expires_at is not None:
        expires_at = body.expires_at
    else:
        # Default durations: pro=365d, enterprise=365d, free=never
        duration = 365 if body.tier != "free" else None
        expires_at = (datetime.now() + timedelta(days=duration)).strftime("%Y-%m-%d") if duration else None

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    started_at = now[:10]

    # Record the subscription change
    cursor.execute(
        _adapt_insert(
            """INSERT INTO subscriptions
               (user_id, tier, amount, payment_method, payment_channel, status, started_at, expires_at)
               VALUES (?, ?, ?, ?, ?, 'active', ?, ?)"""
        ),
        (user_id, body.tier, 0, "admin_change", "manual", started_at, expires_at),
    )
    sub_id = cursor.fetchone()["id"] if _is_postgres() else cursor.lastrowid
    conn.commit()

    # Update users table
    cursor.execute(
        _pg("UPDATE users SET tier = ?, expires_at = ?, subscribed_at = COALESCE(subscribed_at, ?) WHERE id = ?"),
        (body.tier, expires_at, started_at, user_id),
    )
    conn.commit()
    conn.close()

    return {
        "message": f"用户 tier 已更新为 {body.tier}",
        "tier": body.tier,
        "expires_at": expires_at,
        "subscription_id": sub_id,
    }


# ─── User Management ──────────────────────────────────────────────────────────

@router.get("/admin/users", tags=["Admin"])
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tier: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = Query(default="created_at", description="排序字段: created_at/calculations_count/last_active"),
    order: Optional[str] = Query(default="desc", description="asc 或 desc"),
    _: dict = Depends(_require_admin),
):
    valid_sorts = {"created_at", "calculations_count", "last_active", "total_revenue"}
    sort_field = sort if sort in valid_sorts else "created_at"
    sort_dir = "DESC" if order == "desc" else "ASC"

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

    offset = (page - 1) * page_size

    if sort_field == "calculations_count":
        sort_sql = f"(SELECT COUNT(*) FROM calculations c WHERE c.user_id = u.id) {sort_dir}"
    elif sort_field == "last_active":
        sort_sql = f"(SELECT MAX(c.created_at) FROM calculations c WHERE c.user_id = u.id) {sort_dir} NULLS LAST"
    elif sort_field == "total_revenue":
        sort_sql = f"(SELECT COALESCE(SUM(s.amount), 0) FROM subscriptions s WHERE s.user_id = u.id) {sort_dir}"
    else:
        sort_sql = f"u.{sort_field} {sort_dir}"

    cursor.execute(
        _pg(f"""SELECT u.*,
                   s.id as sub_id, s.tier as sub_tier, s.amount, s.status,
                   s.started_at as sub_started, s.expires_at as sub_expires,
                   (SELECT COUNT(*) FROM calculations c WHERE c.user_id = u.id) as calc_count,
                   (SELECT MAX(c.created_at) FROM calculations c WHERE c.user_id = u.id) as last_active_ts,
                   (SELECT COUNT(*) FROM sub_accounts sa WHERE sa.parent_user_id = u.id AND sa.is_active = 1) as sub_count,
                   (SELECT COUNT(*) FROM api_keys ak WHERE ak.user_id = u.id AND ak.is_active = 1) as api_key_count,
                   (SELECT COUNT(*) FROM api_keys ak WHERE ak.user_id = u.id AND ak.is_active = 1 AND ak.last_used_at IS NOT NULL) as api_key_used
            FROM users u
            LEFT JOIN subscriptions s ON s.id = (
                SELECT id FROM subscriptions WHERE user_id = u.id ORDER BY created_at DESC LIMIT 1
            )
            {where_clause}
            ORDER BY {sort_sql}
            LIMIT ? OFFSET ?"""),
        params + [page_size, offset],
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
                "wechat_id": r.get("wechat_id"),
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
                "calculations_count": r["calc_count"] or 0,
                "last_active": r["last_active_ts"],
                "sub_accounts_count": r["sub_count"],
                "api_keys_count": r["api_key_count"],
                "api_keys_used": r["api_key_used"],
            }
            for r in rows
        ],
    }


@router.get("/admin/users/{user_id}", tags=["Admin"])
async def get_user(user_id: int, _: dict = Depends(_require_admin)):
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(_pg("SELECT * FROM users WHERE id = ?"), (user_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="用户不存在")

    # Usage stats
    cursor.execute(
        _pg("SELECT COUNT(*) as cnt FROM calculations WHERE user_id = ?"),
        (user_id,),
    )
    total_calcs = cursor.fetchone()["cnt"]

    cursor.execute(
        _pg("SELECT COUNT(*) as cnt FROM calculations WHERE user_id = ? AND DATE(created_at) >= ?"),
        (user_id, (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")),
    )
    calcs_30d = cursor.fetchone()["cnt"]

    cursor.execute(
        _pg("SELECT MAX(created_at) as last_calc FROM calculations WHERE user_id = ?"),
        (user_id,),
    )
    last_calc = cursor.fetchone()["last_calc"]

    # Daily usage breakdown (last 30 days)
    cursor.execute(
        _pg("""
            SELECT DATE(created_at) as day, COUNT(*) as cnt
            FROM calculations
            WHERE user_id = ? AND DATE(created_at) >= ?
            GROUP BY DATE(created_at)
            ORDER BY day DESC
            LIMIT 30
        """),
        (user_id, (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")),
    )
    daily_usage = [dict(r) for r in cursor.fetchall()]

    # Subscriptions
    cursor.execute(
        _pg("SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC LIMIT 20"),
        (user_id,),
    )
    subs = cursor.fetchall()

    # Sub-accounts
    cursor.execute(
        _pg("SELECT * FROM sub_accounts WHERE parent_user_id = ? ORDER BY created_at DESC"),
        (user_id,),
    )
    sub_accounts = cursor.fetchall()

    # API keys
    cursor.execute(
        _pg("SELECT * FROM api_keys WHERE user_id = ? ORDER BY created_at DESC"),
        (user_id,),
    )
    api_keys = cursor.fetchall()

    conn.close()

    return {
        "user": dict(row),
        "usage": {
            "total_calculations": total_calcs,
            "calculations_30d": calcs_30d,
            "last_calculation": last_calc,
            "daily_usage_30d": daily_usage,
        },
        "subscriptions": [dict(s) for s in subs],
        "sub_accounts": [dict(sa) for sa in sub_accounts],
        "api_keys": [
            {**dict(ak), "key_hash": (ak["key_hash"] or "")[:10] + "***"}
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
    cursor.execute(_pg("SELECT id FROM users WHERE id = ?"), (user_id,))
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
    cursor.execute(_pg("SELECT id FROM users WHERE email = ?"), (body.email.lower().strip(),))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="该邮箱已存在")

    password_hash = hash_password(body.password)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        _adapt_insert(
            """INSERT INTO users (email, password_hash, tier, subscribed_at, expires_at, is_admin, is_active)
               VALUES (?, ?, ?, ?, ?, 0, 1)"""
        ),
        (body.email.lower().strip(), password_hash, body.tier, now, body.expires_at),
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
    cursor.execute(_pg("SELECT id FROM users WHERE id = ?"), (body.user_id,))
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
        (body.user_id, body.tier, body.amount, body.payment_method, body.payment_channel, started_at, expires_at),
    )
    sub_id = cursor.fetchone()["id"] if _is_postgres() else cursor.lastrowid
    conn.commit()

    cursor.execute(
        _pg("UPDATE users SET tier = ?, subscribed_at = ?, expires_at = ? WHERE id = ?"),
        (body.tier, started_at, expires_at, body.user_id),
    )
    conn.commit()
    conn.close()

    return SubscriptionResponse(
        id=sub_id,
        tier=body.tier,
        amount=body.amount,
        currency="CNY",
        payment_method=body.payment_channel,
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

    def count(q: str) -> int:
        try:
            cursor.execute(q)
            return cursor.fetchone()["cnt"]
        except Exception:
            return 0

    total_users = count("SELECT COUNT(*) as cnt FROM users")
    paying_users = count(
        "SELECT COUNT(*) as cnt FROM users WHERE tier != 'free' AND is_active = 1"
    )
    pro_users = count("SELECT COUNT(*) as cnt FROM users WHERE tier = 'pro'")
    enterprise_users = count("SELECT COUNT(*) as cnt FROM users WHERE tier = 'enterprise'")
    disabled_users = count("SELECT COUNT(*) as cnt FROM users WHERE is_active = 0")

    active_api_keys = count("SELECT COUNT(*) as cnt FROM api_keys WHERE is_active = 1")
    active_subs = count("SELECT COUNT(*) as cnt FROM subscriptions WHERE status = 'active'")
    sub_accounts = count("SELECT COUNT(*) as cnt FROM sub_accounts WHERE is_active = 1")

    total_revenue = 0
    cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM subscriptions")
    try:
        total_revenue = cursor.fetchone()["total"]
    except Exception:
        pass

    new_today = count(f"SELECT COUNT(*) as cnt FROM users WHERE DATE(created_at) = {sql_now()}")
    new_week = count(f"SELECT COUNT(*) as cnt FROM users WHERE DATE(created_at) >= {sql_date_sub_days(7)}")
    new_month = count(f"SELECT COUNT(*) as cnt FROM users WHERE DATE(created_at) >= {sql_date_sub_days(30)}")

    expiring_7d = count(
        f"SELECT COUNT(*) as cnt FROM users WHERE {sql_cast_date('expires_at')} "
        f"BETWEEN {sql_now()} AND {sql_date_add_days(7)} AND tier != 'free'"
    )
    expired_recently = count(
        f"SELECT COUNT(*) as cnt FROM users WHERE {sql_cast_date('expires_at')} "
        f"BETWEEN {sql_date_sub_days(7)} AND {sql_now()} AND tier != 'free'"
    )

    # Active users (made a calculation in last 30 days)
    active_30d = count(
        f"SELECT COUNT(DISTINCT user_id) as cnt FROM calculations "
        f"WHERE DATE(created_at) >= {sql_date_sub_days(30)}"
    )

    # Total calculations
    total_calcs = count("SELECT COUNT(*) as cnt FROM calculations")

    # Avg calculations per paying user
    avg_calcs_paying = 0
    if paying_users > 0:
        cursor.execute(
            f"SELECT COUNT(*) as cnt FROM calculations WHERE user_id IN "
            f"(SELECT id FROM users WHERE tier != 'free')"
        )
        try:
            paying_calcs = cursor.fetchone()["cnt"]
            avg_calcs_paying = round(paying_calcs / paying_users, 1) if paying_users else 0
        except Exception:
            pass

    conn.close()

    return {
        "total_users": total_users,
        "paying_users": paying_users,
        "pro_users": pro_users,
        "enterprise_users": enterprise_users,
        "disabled_users": disabled_users,
        "api_keys_active": active_api_keys,
        "sub_accounts_active": sub_accounts,
        "active_subscriptions": active_subs,
        "total_revenue": total_revenue,
        "total_calculations": total_calcs,
        "active_users_30d": active_30d,
        "avg_calcs_per_paying_user": avg_calcs_paying,
        "new_users_today": new_today,
        "new_users_this_week": new_week,
        "new_users_this_month": new_month,
        "expiring_soon_7d": expiring_7d,
        "expired_recently_7d": expired_recently,
    }


@router.get("/admin/stats/revenue", tags=["Admin"])
async def get_revenue_stats(
    days: int = Query(default=90, ge=7, le=365),
    _: dict = Depends(_require_admin),
):
    """
    Revenue breakdown by tier, daily revenue for the past N days.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    # Revenue by tier (all time)
    tier_revenue = {}
    for tier in ("free", "pro", "enterprise"):
        cursor.execute(
            _pg("SELECT COALESCE(SUM(amount), 0) as total FROM subscriptions WHERE tier = ?"),
            (tier,),
        )
        tier_revenue[tier] = cursor.fetchone()["total"]

    total_revenue = sum(tier_revenue.values())

    # Daily revenue (last N days)
    cursor.execute(
        _pg("""
            SELECT DATE(created_at) as day,
                   tier,
                   SUM(amount) as daily_amount,
                   COUNT(*) as sub_count
            FROM subscriptions
            WHERE DATE(created_at) >= ?
            GROUP BY DATE(created_at), tier
            ORDER BY day DESC
        """),
        ((datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),),
    )
    daily_rows = cursor.fetchall()

    # Build daily series
    daily_map: dict = {}
    for r in daily_rows:
        day = r["day"]
        if day not in daily_map:
            daily_map[day] = {"day": day, "pro": 0, "enterprise": 0, "free": 0, "total": 0, "count": 0}
        tier = r["tier"]
        daily_map[day][tier] = float(r["daily_amount"] or 0)
        daily_map[day]["total"] += float(r["daily_amount"] or 0)
        daily_map[day]["count"] += r["sub_count"]

    daily_series = sorted(daily_map.values(), key=lambda x: x["day"], reverse=True)

    # Paying user count by tier
    paying_counts = {}
    for tier in ("pro", "enterprise"):
        cursor.execute(
            _pg("SELECT COUNT(*) as cnt FROM users WHERE tier = ? AND is_active = 1"),
            (tier,),
        )
        paying_counts[tier] = cursor.fetchone()["cnt"]

    conn.close()

    return {
        "tier_revenue": tier_revenue,
        "total_revenue": total_revenue,
        "paying_counts": paying_counts,
        "daily_series": daily_series,
        "period_days": days,
    }


@router.get("/admin/stats/usage", tags=["Admin"])
async def get_usage_stats(
    days: int = Query(default=30, ge=7, le=90),
    _: dict = Depends(_require_admin),
):
    """
    Usage analytics: daily calculations, active users per day, top HS codes.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # Daily calculation counts
    cursor.execute(
        _pg("""
            SELECT DATE(created_at) as day,
                   COUNT(*) as calc_count,
                   COUNT(DISTINCT user_id) as active_users
            FROM calculations
            WHERE DATE(created_at) >= ?
            GROUP BY DATE(created_at)
            ORDER BY day DESC
        """),
        (since,),
    )
    daily = [dict(r) for r in cursor.fetchall()]

    # Top destinations
    cursor.execute(
        _pg("""
            SELECT destination, COUNT(*) as cnt
            FROM calculations
            WHERE DATE(created_at) >= ? AND destination IS NOT NULL
            GROUP BY destination
            ORDER BY cnt DESC
            LIMIT 10
        """),
        (since,),
    )
    top_destinations = [dict(r) for r in cursor.fetchall()]

    # Top origin countries
    cursor.execute(
        _pg("""
            SELECT origin_country, COUNT(*) as cnt
            FROM calculations
            WHERE DATE(created_at) >= ? AND origin_country IS NOT NULL
            GROUP BY origin_country
            ORDER BY cnt DESC
            LIMIT 10
        """),
        (since,),
    )
    top_origins = [dict(r) for r in cursor.fetchall()]

    # Top HS codes (most frequently calculated)
    cursor.execute(
        _pg("""
            SELECT hs_code, COUNT(*) as cnt
            FROM calculations
            WHERE DATE(created_at) >= ? AND hs_code IS NOT NULL
            GROUP BY hs_code
            ORDER BY cnt DESC
            LIMIT 10
        """),
        (since,),
    )
    top_hs_codes = [dict(r) for r in cursor.fetchall()]

    # Active vs new users per day
    cursor.execute(
        _pg("""
            SELECT DATE(c.created_at) as day,
                   COUNT(DISTINCT c.user_id) as calc_users,
                   COUNT(DISTINCT u.id) as registered_users
            FROM calculations c
            LEFT JOIN users u ON DATE(u.created_at) = DATE(c.created_at)
            WHERE DATE(c.created_at) >= ?
            GROUP BY DATE(c.created_at)
            ORDER BY day DESC
        """),
        (since,),
    )
    user_activity = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "period_days": days,
        "daily_calculations": daily,
        "top_destinations": top_destinations,
        "top_origin_countries": top_origins,
        "top_hs_codes": top_hs_codes,
        "user_activity": user_activity,
    }


@router.get("/admin/stats/subscriptions", tags=["Admin"])
async def get_subscription_analytics(
    _: dict = Depends(_require_admin),
):
    """
    Subscription funnel: conversions, upgrades, downgrades, churn.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    # Count subscriptions by tier and status
    cursor.execute(
        """SELECT tier, status, COUNT(*) as cnt FROM subscriptions GROUP BY tier, status"""
    )
    sub_breakdown = {}
    for r in cursor.fetchall():
        tier = r["tier"]
        if tier not in sub_breakdown:
            sub_breakdown[tier] = {}
        sub_breakdown[tier][r["status"]] = r["cnt"]

    # Average subscription duration (active subs)
    avg_duration = 0
    cursor.execute(
        _pg("""
            SELECT AVG(
                CASE
                    WHEN expires_at IS NOT NULL AND started_at IS NOT NULL
                    THEN JULIANDAY(expires_at) - JULIANDAY(started_at)
                    ELSE NULL
                END
            ) as avg_days
            FROM subscriptions
            WHERE status = 'active' AND started_at IS NOT NULL
        """),
    )
    try:
        raw = cursor.fetchone()["avg_days"]
        avg_duration = round(float(raw), 1) if raw else 0
    except Exception:
        pass

    # Churn rate (users who had paying subs but now free + expired recently)
    cursor.execute(
        f"""
            SELECT COUNT(*) as cnt FROM users
            WHERE tier = 'free'
            AND expires_at IS NOT NULL
            AND {sql_cast_date('expires_at')} < {sql_now()}
        """,
    )
    churned = cursor.fetchone()["cnt"]

    conn.close()

    return {
        "subscription_breakdown": sub_breakdown,
        "avg_subscription_days": avg_duration,
        "churned_users": churned,
    }
