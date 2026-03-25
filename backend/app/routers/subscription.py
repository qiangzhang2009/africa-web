"""
Subscription management router.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from app.models.database import get_db, get_db_path
from app.schemas import (
    SubscriptionCreate, SubscriptionResponse, SubscriptionStatus,
    UserResponse,
)
from app.routers.auth import get_current_user

DB_PATH = get_db_path()

router = APIRouter()

TIER_PRICES = {
    "free": 0,
    "pro": 99,
    "enterprise": 298,
}
TIER_DURATION_DAYS = {
    "free": None,
    "pro": 365,
    "enterprise": 365,
}
FREE_DAILY_QUOTA = 3


def _get_user_subscription_info(user_id: int) -> dict:
    """Return subscription status details for a user."""
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    now = datetime.now().strftime("%Y-%m-%d")
    tier = row["tier"]
    # Convert datetime objects to ISO string for consistent string comparison
    def _ts(v):
        if v is None:
            return None
        if hasattr(v, "isoformat"):
            return v.isoformat()[:10]
        return str(v)[:10]
    expires_at = _ts(row["expires_at"])

    is_active = True
    days_remaining = None
    if expires_at:
        if expires_at < now:
            is_active = False
            tier = "free"
        else:
            exp = datetime.strptime(expires_at, "%Y-%m-%d")
            days_remaining = (exp - datetime.now()).days

    api_enabled = tier in ("pro", "enterprise")

    sub_accounts_remaining = 0
    if tier == "enterprise":
        conn2 = get_db(DB_PATH)
        cursor2 = conn2.cursor()
        cursor2.execute(
            "SELECT COUNT(*) as cnt FROM sub_accounts WHERE parent_user_id = ? AND is_active = 1",
            (user_id,)
        )
        sub_accounts_remaining = max(0, 5 - cursor2.fetchone()["cnt"])
        conn2.close()

    remaining_queries = None if tier != "free" else FREE_DAILY_QUOTA

    def _ts(v):
        if v is None:
            return None
        if hasattr(v, "isoformat"):
            return v.isoformat()[:10]
        return str(v)[:10]

    return {
        "tier": tier,
        "expires_at": expires_at,
        "remaining_queries": remaining_queries,
        "is_active": is_active,
        "days_remaining": days_remaining,
        "api_enabled": api_enabled,
        "sub_accounts_remaining": sub_accounts_remaining,
        "user": UserResponse(
            id=row["id"],
            email=row["email"],
            tier=tier,
            is_admin=bool(row["is_admin"]),
            subscribed_at=_ts(row["subscribed_at"]),
            expires_at=expires_at,
            created_at=_ts(row["created_at"]),
        ),
    }


@router.get("/subscribe/status", response_model=SubscriptionStatus)
async def get_subscription_status(current_user: dict = Depends(get_current_user)):
    return _get_user_subscription_info(current_user["user_id"])


@router.post("/subscribe/create", response_model=SubscriptionStatus)
async def create_subscription(
    body: SubscriptionCreate,
    current_user: dict = Depends(get_current_user),
):
    if body.tier not in TIER_PRICES:
        raise HTTPException(status_code=400, detail="无效的订阅方案")

    user_id = current_user["user_id"]
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    now = datetime.now()
    started_at = now.strftime("%Y-%m-%d")
    duration = TIER_DURATION_DAYS.get(body.tier)
    if duration:
        expires_at = (now + timedelta(days=duration)).strftime("%Y-%m-%d")
    else:
        expires_at = None

    # Record subscription
    cursor.execute(
        """INSERT INTO subscriptions
           (user_id, tier, amount, payment_method, payment_channel, status, started_at, expires_at)
           VALUES (?, ?, ?, ?, ?, 'active', ?, ?)""",
        (user_id, body.tier, TIER_PRICES[body.tier], body.payment_method,
         body.payment_channel, started_at, expires_at)
    )
    conn.commit()

    # Update user tier
    cursor.execute(
        """UPDATE users SET tier = ?, subscribed_at = ?, expires_at = ? WHERE id = ?""",
        (body.tier, started_at, expires_at, user_id)
    )
    conn.commit()
    conn.close()

    return _get_user_subscription_info(user_id)


@router.get("/subscribe/history", response_model=list[SubscriptionResponse])
async def get_subscription_history(current_user: dict = Depends(get_current_user)):
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC""",
        (current_user["user_id"],)
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        SubscriptionResponse(
            id=r["id"],
            tier=r["tier"],
            amount=r["amount"],
            currency=r["currency"],
            payment_method=r["payment_method"],
            payment_channel=r["payment_channel"],
            status=r["status"],
            started_at=r["started_at"],
            expires_at=r["expires_at"],
            auto_renew=bool(r["auto_renew"]),
        )
        for r in rows
    ]
