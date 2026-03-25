from fastapi import APIRouter, HTTPException, Depends
from app.schemas import (
    TariffCalcInput,
    ImportCostInput,
    OriginCheckInput, OriginCheckResult,
)
import os, json
from datetime import datetime
from openai import OpenAI
from app.services import tariff as tariff_service
from app.models.database import get_db, get_db_path, _is_postgres
from app.routers.auth import get_optional_user, get_user_daily_usage

DB_PATH = get_db_path()
FREE_DAILY_LIMIT = 3

router = APIRouter()


# ─── POST /calculate/tariff ─────────────────────────────────────────────────

def _ensure_calc_table(db_path: str) -> None:
    """Self-healing: create calculations table if it doesn't exist yet (SQLite only).
    
    For PostgreSQL, the table is created by init_db(). This function is a no-op.
    """
    if _is_postgres():
        return  # PostgreSQL: table already exists via init_db()
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calculations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER,
            product_name    TEXT,
            hs_code         TEXT,
            origin          TEXT,
            destination     TEXT,
            fob_value       REAL,
            result_json     TEXT,
            total           REAL,
            created_at      TEXT DEFAULT (datetime('now'))
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calc_user ON calculations(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calc_day ON calculations(created_at)")
    conn.commit()
    conn.close()


def _check_and_record_calculation(user_id: int | None, db_path: str) -> tuple[bool, int, int]:
    """
    Check if a free user has remaining daily quota.
    Returns (allowed, used_today, remaining).
    For non-free users or anonymous users, always allowed.
    """
    if user_id is None:
        return True, 0, 999999

    # Get user tier from DB
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT tier, expires_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return True, 0, 999999

    tier = row["tier"]
    # Convert datetime objects to ISO string for string comparison
    def _ts(v):
        return v.isoformat() if hasattr(v, "isoformat") else (v or "")
    expires_at = _ts(row["expires_at"])
    now = datetime.now().strftime("%Y-%m-%d")

    # Downgrade expired subscriptions
    if tier != "free" and expires_at and expires_at < now:
        tier = "free"

    if tier != "free":
        return True, 0, 999999

    # Free user: check daily quota
    used_today = get_user_daily_usage(user_id, db_path)
    remaining = FREE_DAILY_LIMIT - used_today
    return remaining > 0, used_today, max(0, remaining)


@router.post("/calculate/tariff")
async def calc_tariff(input: TariffCalcInput, current_user: dict = Depends(get_optional_user)):
    user_id = current_user["user_id"] if current_user else None

    # Self-healing: ensure calculations table exists
    _ensure_calc_table(DB_PATH)

    # Server-side rate limit check
    allowed, used_today, remaining = _check_and_record_calculation(user_id, DB_PATH)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "quota_exceeded",
                "message": "今日免费次数已用完，请开通 Pro 版",
                "remaining_today": 0,
                "max_free_daily": FREE_DAILY_LIMIT,
            }
        )

    result = tariff_service.calculate_tariff(
        hs_code=input.hs_code,
        origin_country=input.origin_country,
        destination=input.destination,
        fob_value=input.fob_value,
        db_path=DB_PATH,
        quantity_kg=input.quantity_kg,
        freight_override=input.freight_override,
        exchange_rate=input.exchange_rate,
    )
    result["input"] = input.model_dump()

    # Record successful calculation for quota tracking
    if user_id and result.get("success"):
        # Convert Pydantic breakdown models to dicts for JSON serialization
        serializable = dict(result)
        if "breakdown" in serializable and hasattr(serializable["breakdown"], "model_dump"):
            serializable["breakdown"] = serializable["breakdown"].model_dump()
        if "input" in serializable and hasattr(serializable["input"], "model_dump"):
            serializable["input"] = serializable["input"].model_dump()

        bd = serializable.get("breakdown", {})
        total_val = bd.get("total_cost", 0) if isinstance(bd, dict) else 0

        conn = get_db(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO calculations (user_id, product_name, hs_code, origin, destination, fob_value, result_json, total) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, input.hs_code, input.hs_code, input.origin_country, input.destination, input.fob_value, json.dumps(serializable), total_val)
        )
        conn.commit()
        conn.close()

    return result


# ─── GET /calculate/daily-usage ───────────────────────────────────────────────

@router.get("/calculate/daily-usage")
async def get_calc_daily_usage(current_user: dict = Depends(get_optional_user)):
    """Return remaining daily quota for the current user."""
    _ensure_calc_table(DB_PATH)
    if not current_user:
        return {"remaining_today": 999999, "max_free_daily": FREE_DAILY_LIMIT, "tier": "anonymous"}

    allowed, used_today, remaining = _check_and_record_calculation(current_user["user_id"], DB_PATH)
    return {
        "remaining_today": remaining,
        "used_today": used_today,
        "max_free_daily": FREE_DAILY_LIMIT,
        "tier": current_user["tier"],
    }


# ─── POST /calculate/import-cost ─────────────────────────────────────────────

@router.post("/calculate/import-cost")
async def calc_import_cost(input: ImportCostInput, current_user: dict = Depends(get_optional_user)):
    user_id = current_user["user_id"] if current_user else None

    # Self-healing: ensure calculations table exists
    _ensure_calc_table(DB_PATH)

    # Apply same rate limit
    allowed, _, _ = _check_and_record_calculation(user_id, DB_PATH)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "quota_exceeded",
                "message": "今日免费次数已用完，请开通 Pro 版",
                "remaining_today": 0,
                "max_free_daily": FREE_DAILY_LIMIT,
            }
        )

    result = tariff_service.calculate_import_cost(
        product_name=input.product_name,
        quantity_kg=input.quantity_kg,
        fob_per_kg=input.fob_per_kg,
        origin=input.origin,
        db_path=DB_PATH,
    )
    result["input"] = input.model_dump()

    # Record successful import-cost calculation for quota tracking consistency.
    if user_id and result.get("success"):
        # Convert Pydantic breakdown to dict for JSON serialization
        breakdown = result.get("breakdown")
        if breakdown is not None and hasattr(breakdown, "model_dump"):
            breakdown_dict = breakdown.model_dump()
            serializable_result = dict(result)
            serializable_result["breakdown"] = breakdown_dict
            serializable_result["input"] = input.model_dump()
        else:
            breakdown_dict = breakdown or {}
            serializable_result = result

        total_val = breakdown_dict.get("total_cost") or 0
        fob_cny = breakdown_dict.get("fob_value") or 0
        conn = get_db(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO calculations (user_id, product_name, hs_code, origin, destination, fob_value, result_json, total) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                input.product_name,
                None,
                input.origin,
                input.destination,
                fob_cny,
                json.dumps(serializable_result),
                total_val,
            ),
        )
        conn.commit()
        conn.close()
    return result


# ─── POST /origin/check ────────────────────────────────────────────────────────

@router.post("/origin/check", response_model=OriginCheckResult)
async def check_origin(input: OriginCheckInput):
    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key or not api_key.startswith("sk-"):
        return {
            "qualifies": True,
            "rule_applied": "规则估算模式",
            "confidence": 0.7,
            "reasons": [
                f"原产国: {input.origin}",
                f"HS编码: {input.hs_code}",
                f"加工工序: {len(input.processing_steps)}步",
            ],
            "suggestions": [
                "AI API key未配置，采用规则估算模式",
                "配置DEEPSEEK_API_KEY后获得更准确的AI判定",
            ],
        }

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )
        prompt = f"""你是非洲原产地证书合规专家。用户正在申请从 {input.origin} 进口 HS编码 {input.hs_code} 的产品。

加工工序：
{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(input.processing_steps))}

原料来源：
{chr(10).join(input.material_sources) if input.material_sources else "全部为本地原料"}

请判断：
1. 该产品是否符合中国/非洲零关税的原产地条件？
2. 适用的原产地规则是什么？
3. 给出判断置信度（0-1）
4. 如有问题，指出具体建议

请严格用JSON格式回答，不要加任何markdown代码块：
{{"qualifies": true/false, "rule_applied": "规则名称", "confidence": 0.7, "reasons": ["原因1", "原因2"], "suggestions": ["建议1"]}}
"""
        response = client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            for block in raw.split("```"):
                block = block.strip()
                if block and not block.startswith("json"):
                    raw = block
                    break
        result = json.loads(raw.strip())
        return result

    except json.JSONDecodeError as e:
        return {
            "qualifies": True,
            "rule_applied": "规则估算模式",
            "confidence": 0.5,
            "reasons": [f"AI返回格式异常，已切换为规则估算: {str(e)}"],
            "suggestions": ["请稍后重试"],
        }
    except Exception as e:
        return {
            "qualifies": False,
            "rule_applied": None,
            "confidence": 0.3,
            "reasons": [f"AI服务暂时不可用: {str(e)}"],
            "suggestions": ["请稍后重试，或手动确认原产地条件"],
        }
