"""
Authentication router: register, login, JWT token management.
"""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.models.database import get_db, hash_password, verify_password
from app.schemas import (
    UserRegister, UserLogin, UserResponse,
    AuthResponse, SubAccountCreate, SubAccountResponse,
)

ALGORITHM = "HS256"
SECRET_KEY = os.getenv("JWT_SECRET", "africa-zero-secret-key-change-in-production-2026")
ACCESS_TOKEN_EXPIRE_DAYS = 30

router = APIRouter()
security = HTTPBearer(auto_error=False)


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
        return {
            "user_id": user_id,
            "email": payload.get("email"),
            "tier": payload.get("tier"),
            "is_admin": payload.get("is_admin", False),
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Token无效或已过期")


def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Returns user info if token provided, else None."""
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "user_id": int(payload.get("sub")),
            "email": payload.get("email"),
            "tier": payload.get("tier"),
            "is_admin": payload.get("is_admin", False),
        }
    except JWTError:
        return None


DB_PATH = os.getenv("DATABASE_URL", "data/africa_zero.db")
DB_PATH = str(Path(DB_PATH).resolve())


@router.post("/auth/register", response_model=AuthResponse)
async def register(body: UserRegister):
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE email = ?", (body.email.lower().strip(),))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="该邮箱已注册，请直接登录")

    password_hash = hash_password(body.password)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """INSERT INTO users (email, password_hash, tier, subscribed_at, expires_at, is_admin, is_active)
           VALUES (?, ?, 'free', ?, NULL, 0, 1)""",
        (body.email.lower().strip(), password_hash, now)
    )
    conn.commit()
    user_id = cursor.lastrowid
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
    return AuthResponse(access_token=token, user=user)


@router.post("/auth/login", response_model=AuthResponse)
async def login(body: UserLogin):
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

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

    # Check subscription expiry
    now = datetime.now().strftime("%Y-%m-%d")
    tier = row["tier"]
    expires_at = row["expires_at"]

    if expires_at and expires_at < now:
        tier = "free"
        conn2 = get_db(DB_PATH)
        cursor2 = conn2.cursor()
        cursor2.execute(
            "UPDATE users SET tier = 'free' WHERE id = ?", (row["id"],)
        )
        conn2.commit()
        conn2.close()

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
        subscribed_at=row["subscribed_at"],
        expires_at=expires_at,
        created_at=row["created_at"],
    )
    return AuthResponse(access_token=token, user=user)


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ? AND is_active = 1", (current_user["user_id"],))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    now = datetime.now().strftime("%Y-%m-%d")
    tier = row["tier"]
    expires_at = row["expires_at"]

    if expires_at and expires_at < now:
        tier = "free"

    return UserResponse(
        id=row["id"],
        email=row["email"],
        tier=tier,
        is_admin=bool(row["is_admin"]),
        subscribed_at=row["subscribed_at"],
        expires_at=expires_at,
        created_at=row["created_at"],
    )


# ─── Sub-accounts (Enterprise) ─────────────────────────────────────────────────

@router.get("/sub-accounts", response_model=list[SubAccountResponse])
async def list_sub_accounts(current_user: dict = Depends(get_current_user)):
    if current_user["tier"] != "enterprise":
        raise HTTPException(status_code=403, detail="仅企业版用户可管理子账号")

    conn = get_db(DB_PATH)
    cursor = conn.cursor()
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
        raise HTTPException(status_code=403, detail="仅企业版用户可创建子账号")

    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM sub_accounts WHERE parent_user_id = ? AND is_active = 1",
                   (current_user["user_id"],))
    if cursor.fetchone()["cnt"] >= 5:
        conn.close()
        raise HTTPException(status_code=400, detail="企业版最多5个子账号，已达上限")

    cursor.execute("SELECT id FROM sub_accounts WHERE email = ? AND is_active = 1",
                   (body.email.lower().strip(),))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="该邮箱已是子账号")

    password_hash = hash_password(body.password)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """INSERT INTO sub_accounts (parent_user_id, email, password_hash, name, is_active)
           VALUES (?, ?, ?, ?, 1)""",
        (current_user["user_id"], body.email.lower().strip(), password_hash, body.name)
    )
    conn.commit()
    sub_id = cursor.lastrowid
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
        "UPDATE sub_accounts SET is_active = 0 WHERE id = ? AND parent_user_id = ?",
        (sub_id, current_user["user_id"])
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()

    if not affected:
        raise HTTPException(status_code=404, detail="子账号不存在或无权删除")
    return {"message": "子账号已删除"}
