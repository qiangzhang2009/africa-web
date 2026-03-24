"""
Authentication router: register, login, JWT token management.
"""
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.models.database import get_db, hash_password, verify_password, get_db_path, sql_now, _is_postgres, _adapt_insert
from app.schemas import (
    UserRegister, UserLogin, UserResponse,
    AuthResponse, SubAccountCreate, SubAccountResponse,
)

ALGORITHM = "HS256"
SECRET_KEY = os.getenv("JWT_SECRET", "africa-zero-secret-key-change-in-production-2026")
ACCESS_TOKEN_EXPIRE_DAYS = 30
FREE_DAILY_LIMIT = 3

router = APIRouter()
security = HTTPBearer(auto_error=False)


def _row_str(val) -> str | None:
    """Convert PostgreSQL datetime values to ISO string for Pydantic."""
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def create_access_token(user_id: int, email: str, tier: str, is_admin: bool) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "tier": tier,
        "is_admin": is_admin,
        "exp": datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="未登录，请先登录")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        tier, expires_at, is_admin, is_active = get_user_tier_from_db(user_id, DB_PATH)
        if not is_active:
            raise HTTPException(status_code=401, detail="账号已禁用")

        now = datetime.now().strftime("%Y-%m-%d")
        if tier != "free" and expires_at and expires_at < now:
            tier = "free"
            conn = get_db(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET tier = 'free' WHERE id = %s", (user_id,)) \
                if _is_postgres() else \
                cursor.execute("UPDATE users SET tier = 'free' WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()

        return {
            "user_id": user_id,
            "email": payload.get("email"),
            "tier": tier,
            "is_admin": is_admin,
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Token无效或已过期")


def get_user_daily_usage(user_id: int, db_path: str) -> int:
    """Return how many tariff calculations this user has done today."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    try:
        today_expr = sql_now()
        if _is_postgres():
            cursor.execute(
                f"SELECT COUNT(*) as cnt FROM calculations WHERE user_id = %s AND DATE(created_at) = {today_expr}",
                (user_id,)
            )
        else:
            cursor.execute(
                f"SELECT COUNT(*) as cnt FROM calculations WHERE user_id = ? AND DATE(created_at) = {today_expr}",
                (user_id,)
            )
        cnt = cursor.fetchone()["cnt"]
    except Exception:
        cnt = 0
    conn.close()
    return cnt


def get_user_tier_from_db(user_id: int, db_path: str) -> tuple[str, str | None, bool, bool]:
    """Return (tier, expires_at, is_admin, is_active) from the database."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,)) \
        if _is_postgres() else \
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return "free", None, False, False
    return row["tier"], row["expires_at"], bool(row["is_admin"]), bool(row["is_active"])


def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Returns user info if token provided, else None."""
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        tier, expires_at, is_admin, is_active = get_user_tier_from_db(user_id, DB_PATH)
        if not is_active:
            return None

        now = datetime.now().strftime("%Y-%m-%d")
        if tier != "free" and expires_at and expires_at < now:
            tier = "free"
            conn = get_db(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET tier = 'free' WHERE id = %s", (user_id,)) \
                if _is_postgres() else \
                cursor.execute("UPDATE users SET tier = 'free' WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()

        return {
            "user_id": user_id,
            "email": payload.get("email"),
            "tier": tier,
            "is_admin": is_admin,
        }
    except JWTError:
        return None


DB_PATH = get_db_path()


@router.post("/auth/register", response_model=AuthResponse)
async def register(body: UserRegister):
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE email = %s", (body.email.lower().strip(),)) \
        if _is_postgres() else \
        cursor.execute("SELECT id FROM users WHERE email = ?", (body.email.lower().strip(),))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="该邮箱已注册，请直接登录")

    password_hash = hash_password(body.password)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if _is_postgres():
        cursor.execute(
            "INSERT INTO users (email, password_hash, tier, subscribed_at, expires_at, is_admin, is_active) "
            "VALUES (%s, %s, 'free', %s, NULL, 0, 1) RETURNING id",
            (body.email.lower().strip(), password_hash, now)
        )
        user_id = cursor.fetchone()["id"]
    else:
        cursor.execute(
            "INSERT INTO users (email, password_hash, tier, subscribed_at, expires_at, is_admin, is_active) "
            "VALUES (?, ?, 'free', ?, NULL, 0, 1)",
            (body.email.lower().strip(), password_hash, now)
        )
        user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    token = create_access_token(user_id, body.email.lower().strip(), "free", False)
    user = UserResponse(
        id=user_id,
        email=body.email.lower().strip(),
        tier="free",
        is_admin=False,
        subscribed_at=now,
        expires_at=None,
        created_at=now,
    )
    return AuthResponse(access_token=token, user=user, remaining_today=FREE_DAILY_LIMIT, max_free_daily=FREE_DAILY_LIMIT)


@router.post("/auth/login", response_model=AuthResponse)
async def login(body: UserLogin):
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email = %s AND is_active = 1",
        (body.email.lower().strip(),)
    ) if _is_postgres() else \
        cursor.execute(
            "SELECT * FROM users WHERE email = ? AND is_active = 1",
            (body.email.lower().strip(),)
        )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    if not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    now_str = datetime.now().strftime("%Y-%m-%d")
    tier = row["tier"]
    expires_at = _row_str(row["expires_at"])

    if expires_at and expires_at < now_str:
        tier = "free"
        conn2 = get_db(DB_PATH)
        cursor2 = conn2.cursor()
        cursor2.execute("UPDATE users SET tier = 'free' WHERE id = %s", (row["id"],)) \
            if _is_postgres() else \
            cursor2.execute("UPDATE users SET tier = 'free' WHERE id = ?", (row["id"],))
        conn2.commit()
        conn2.close()

    used_today = get_user_daily_usage(row["id"], DB_PATH)

    token = create_access_token(
        row["id"],
        row["email"],
        tier,
        bool(row["is_admin"]),
    )
    user = UserResponse(
        id=row["id"],
        email=row["email"],
        tier=tier,
        is_admin=bool(row["is_admin"]),
        subscribed_at=_row_str(row["subscribed_at"]),
        expires_at=_row_str(expires_at),
        created_at=_row_str(row["created_at"]),
    )
    remaining_today = max(0, FREE_DAILY_LIMIT - used_today) if tier == "free" else 999999
    return AuthResponse(access_token=token, user=user, remaining_today=remaining_today, max_free_daily=FREE_DAILY_LIMIT)


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE id = %s AND is_active = 1",
        (current_user["user_id"],)
    ) if _is_postgres() else \
        cursor.execute(
            "SELECT * FROM users WHERE id = ? AND is_active = 1",
            (current_user["user_id"],)
        )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    now = datetime.now().strftime("%Y-%m-%d")
    tier = row["tier"]
    expires_at = _row_str(row["expires_at"])

    if expires_at and expires_at < now:
        tier = "free"

    return UserResponse(
        id=row["id"],
        email=row["email"],
        tier=tier,
        is_admin=bool(row["is_admin"]),
        subscribed_at=_row_str(row["subscribed_at"]),
        expires_at=expires_at,
        created_at=_row_str(row["created_at"]),
    )


@router.get("/auth/daily-usage")
async def get_daily_usage(current_user: dict = Depends(get_current_user)):
    """Return the user's remaining free daily queries and tier info, synced from the server."""
    used_today = get_user_daily_usage(current_user["user_id"], DB_PATH)
    remaining_today = max(0, FREE_DAILY_LIMIT - used_today) if current_user["tier"] == "free" else 999999
    return {
        "used_today": used_today,
        "remaining_today": remaining_today,
        "max_free_daily": FREE_DAILY_LIMIT,
        "tier": current_user["tier"],
    }


# ─── Sub-accounts (Enterprise) ─────────────────────────────────────────────────

@router.get("/sub-accounts", response_model=list[SubAccountResponse])
async def list_sub_accounts(current_user: dict = Depends(get_current_user)):
    if current_user["tier"] != "enterprise":
        raise HTTPException(status_code=403, detail="仅企业版用户可管理子账号")

    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM sub_accounts WHERE parent_user_id = %s AND is_active = 1",
        (current_user["user_id"],)
    ) if _is_postgres() else \
        cursor.execute(
            "SELECT * FROM sub_accounts WHERE parent_user_id = ? AND is_active = 1",
            (current_user["user_id"],)
        )
    rows = cursor.fetchall()
    conn.close()

    return [
        SubAccountResponse(
            id=r["id"],
            email=r["email"],
            name=r["name"],
            is_active=bool(r["is_active"]),
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("/sub-accounts", response_model=SubAccountResponse)
async def create_sub_account(body: SubAccountCreate, current_user: dict = Depends(get_current_user)):
    if current_user["tier"] != "enterprise":
        raise HTTPException(status_code=403, detail="仅企业版用户可管理子账号")

    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM sub_accounts WHERE parent_user_id = %s AND is_active = 1",
        (current_user["user_id"],)
    ) if _is_postgres() else \
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM sub_accounts WHERE parent_user_id = ? AND is_active = 1",
            (current_user["user_id"],)
        )
    if cursor.fetchone()["cnt"] >= 5:
        conn.close()
        raise HTTPException(status_code=400, detail="企业版最多5个子账号，已达上限")

    cursor.execute(
        "SELECT id FROM sub_accounts WHERE email = %s AND is_active = 1",
        (body.email.lower().strip(),)
    ) if _is_postgres() else \
        cursor.execute(
            "SELECT id FROM sub_accounts WHERE email = ? AND is_active = 1",
            (body.email.lower().strip(),)
        )
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="该邮箱已是子账号")

    password_hash = hash_password(body.password)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if _is_postgres():
        cursor.execute(
            "INSERT INTO sub_accounts (parent_user_id, email, password_hash, name, is_active) "
            "VALUES (%s, %s, %s, %s, 1) RETURNING id",
            (current_user["user_id"], body.email.lower().strip(), password_hash, body.name)
        )
        sub_id = cursor.fetchone()["id"]
    else:
        cursor.execute(
            "INSERT INTO sub_accounts (parent_user_id, email, password_hash, name, is_active) "
            "VALUES (?, ?, ?, ?, 1)",
            (current_user["user_id"], body.email.lower().strip(), password_hash, body.name)
        )
        sub_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return SubAccountResponse(
        id=sub_id,
        email=body.email.lower().strip(),
        name=body.name,
        is_active=True,
        created_at=now,
    )


@router.delete("/sub-accounts/{sub_id}")
async def delete_sub_account(sub_id: int, current_user: dict = Depends(get_current_user)):
    if current_user["tier"] != "enterprise":
        raise HTTPException(status_code=403, detail="仅企业版用户可管理子账号")

    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE sub_accounts SET is_active = 0 WHERE id = %s AND parent_user_id = %s",
        (sub_id, current_user["user_id"])
    ) if _is_postgres() else \
        cursor.execute(
            "UPDATE sub_accounts SET is_active = 0 WHERE id = ? AND parent_user_id = ?",
            (sub_id, current_user["user_id"])
        )
    conn.commit()
    affected = cursor.rowcount
    conn.close()

    if not affected:
        raise HTTPException(status_code=404, detail="子账号不存在或无权删除")
    return {"message": "子账号已删除"}
