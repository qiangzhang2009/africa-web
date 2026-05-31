"""AI prompt templates for consistent, maintainable prompts."""
from typing import Literal

ModelName = Literal["deepseek-chat", "gpt-4", "claude-3"]

# ─── Origin Check Prompt ──────────────────────────────────────────────────────

ORIGIN_CHECK_SYSTEM_PROMPT = """你是一名非洲原产地证书合规专家。你精通以下规则：
1. 中国对非洲53个建交国的零关税政策（2026年5月起生效）
2. 非洲大陆自由贸易区（AfCFTA）原产地规则（增值≥40%）
3. 欧盟-非洲EPA临时/踏板协议
4. 一般原产地规则（CTC、增值、混合规则）

请严格、客观地评估原产地资格，给出置信度和改进建议。"""

def origin_check_user_prompt(
    hs_code: str,
    origin_country: str,
    processing_steps: list[str],
    material_sources: list[str],
) -> str:
    steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(processing_steps)) if processing_steps else "无加工工序"
    materials_text = "\n".join(material_sources) if material_sources else "全部为本地原料"

    return f"""请评估以下产品的原产地资格：

产品信息：
- HS编码：{hs_code}
- 原产国：{origin_country}

加工工序：
{steps_text}

原料来源：
{materials_text}

请判断：
1. 是否符合中国/非洲零关税原产地条件？
2. 适用哪条原产地规则？
3. 置信度（0-1）
4. 如果不符合，给出改进建议

JSON格式响应（不包含markdown代码块）：
{{"qualifies": true/false, "rule_applied": "规则名称", "confidence": 0.0-1.0, "reasons": ["原因"], "suggestions": ["建议"]}}
"""

# ─── Supplier Risk Assessment Prompt ──────────────────────────────────────────

def supplier_risk_prompt(country: str, product_hs_codes: list[str]) -> str:
    return f"""作为非洲贸易风险评估专家，请评估从{country}进口以下HS编码产品的供应链风险：
HS编码：{', '.join(product_hs_codes)}

请从以下维度评估（每项1-10分，10为最高风险）：
1. 政治稳定性
2. 经济稳定性
3. 贸易便利化程度
4. 汇率风险
5. 物流基础设施

并给出：
- 综合风险评分（1-10）
- 主要风险因素
- 缓解建议
- 推荐采购策略

JSON格式响应：
{{"risk_score": 1-10, "political": 1-10, "economic": 1-10, "trade_facility": 1-10, "currency_risk": 1-10, "logistics": 1-10, "major_risks": ["风险1"], "mitigations": ["建议1"], "procurement_strategy": "策略描述"}}
"""
