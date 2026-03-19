from fastapi import APIRouter
from app.schemas import (
    TariffCalcInput, TariffCalcResult,
    ImportCostInput, ImportCostResult,
    OriginCheckInput, OriginCheckResult,
)
from pathlib import Path
import os, json
from openai import OpenAI
from app.services import tariff as tariff_service
from app.models.database import get_db

DB_PATH = os.getenv("DATABASE_URL", "data/africa_zero.db")
DB_PATH = str(Path(DB_PATH).resolve())

router = APIRouter()


# ─── POST /calculate/tariff ─────────────────────────────────────────────────

@router.post("/calculate/tariff", response_model=TariffCalcResult)
async def calc_tariff(input: TariffCalcInput):
    result = tariff_service.calculate_tariff(
        hs_code=input.hs_code,
        origin_country=input.origin_country,
        destination=input.destination,
        fob_value=input.fob_value,
        db_path=DB_PATH,
    )
    result["input"] = input.model_dump()
    return result


# ─── POST /calculate/import-cost ─────────────────────────────────────────────

@router.post("/calculate/import-cost", response_model=ImportCostResult)
async def calc_import_cost(input: ImportCostInput):
    result = tariff_service.calculate_import_cost(
        product_name=input.product_name,
        quantity_kg=input.quantity_kg,
        fob_per_kg=input.fob_per_kg,
        origin=input.origin,
        db_path=DB_PATH,
    )
    result["input"] = input.model_dump()
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
