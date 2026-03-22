"""
Certificate of Origin guidance API.
Step-by-step workflow for obtaining CO certificates.
"""
import json
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from app.models.database import get_db, get_db_path
from app.routers.auth import get_current_user, get_optional_user

router = APIRouter()
DB_PATH = get_db_path()


# ─── Schemas ────────────────────────────────────────────────────────────────────

class CertGuide(BaseModel):
    id: int
    country_code: str
    country_name_zh: str
    cert_type: str
    cert_type_zh: str
    issuing_authority: str
    issuing_authority_zh: str
    website_url: Optional[str]
    fee_usd_min: float
    fee_usd_max: float
    fee_cny_note: Optional[str]
    days_min: int
    days_max: int
    doc_requirements: list[str]
    step_sequence: list[dict]
    api_available: bool
    notes: Optional[str]


class CertGuideListItem(BaseModel):
    id: int
    country_code: str
    country_name_zh: str
    cert_type_zh: str
    issuing_authority_zh: str
    fee_usd_min: float
    fee_usd_max: float
    days_min: int
    days_max: int
    api_available: bool


class CertApplicationCreate(BaseModel):
    hs_code: str
    origin_country: str
    cert_type: str = "CO"


class CertApplication(BaseModel):
    id: int
    user_id: int
    hs_code: str
    origin_country: str
    cert_type: str
    status: str
    current_step: int
    steps_completed: dict
    ai_doc_generated: bool
    submitted_at: Optional[str]
    cert_number: Optional[str]
    created_at: Optional[str]


class CertDocGenerateInput(BaseModel):
    hs_code: str
    origin_country: str
    processing_steps: list[str] = Field(default_factory=list)
    material_sources: list[str] = Field(default_factory=list)
    exporter_name: str = ""
    importer_name: str = ""
    product_description: str = ""
    fob_value_usd: float = 0
    quantity_kg: float = 0
    destination_country: str = "CN"


class CertDocGenerateResult(BaseModel):
    document_type: str
    content: str
    format: str  # "pdf" or "text"
    generated_at: str
    usage_note: str


# ─── Helpers ────────────────────────────────────────────────────────────────────

def _parse_json_field(raw: str, default=None):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


# ─── Routes ────────────────────────────────────────────────────────────────────

@router.get("/certificate/guides")
async def list_cert_guides(
    country: Optional[str] = None,
):
    """
    List certificate of origin guides for all or specific countries.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    sql = "SELECT * FROM cert_guides WHERE is_active = 1"
    params = []
    if country:
        sql += " AND country_code = ?"
        params.append(country.upper())

    sql += " ORDER BY country_name_zh"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "country_code": r["country_code"],
            "country_name_zh": r["country_name_zh"],
            "cert_type": r["cert_type"],
            "cert_type_zh": r["cert_type_zh"],
            "issuing_authority": r["issuing_authority"],
            "issuing_authority_zh": r["issuing_authority_zh"],
            "website_url": r["website_url"],
            "fee_usd_min": r["fee_usd_min"],
            "fee_usd_max": r["fee_usd_max"],
            "fee_cny_note": r["fee_cny_note"],
            "days_min": r["days_min"],
            "days_max": r["days_max"],
            "doc_requirements": _parse_json_field(r["doc_requirements"], []),
            "step_sequence": _parse_json_field(r["step_sequence"], []),
            "api_available": bool(r["api_available"]),
            "notes": r["notes"],
        }
        for r in rows
    ]


@router.get("/certificate/guides/{country_code}")
async def get_cert_guide(country_code: str):
    """
    Get detailed certificate guide for a specific country.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM cert_guides WHERE is_active = 1 AND country_code = ? LIMIT 1",
        (country_code.upper(),)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"暂无 {country_code} 的办证指南")

    return CertGuide(
        id=row["id"],
        country_code=row["country_code"],
        country_name_zh=row["country_name_zh"],
        cert_type=row["cert_type"],
        cert_type_zh=row["cert_type_zh"],
        issuing_authority=row["issuing_authority"],
        issuing_authority_zh=row["issuing_authority_zh"],
        website_url=row["website_url"],
        fee_usd_min=row["fee_usd_min"],
        fee_usd_max=row["fee_usd_max"],
        fee_cny_note=row["fee_cny_note"],
        days_min=row["days_min"],
        days_max=row["days_max"],
        doc_requirements=_parse_json_field(row["doc_requirements"], []),
        step_sequence=_parse_json_field(row["step_sequence"], []),
        api_available=bool(row["api_available"]),
        notes=row["notes"],
    )


@router.post("/certificate/application/start")
async def start_cert_application(
    body: CertApplicationCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Start a new certificate application workflow.
    Creates a record to track progress.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    # Check if there's already an active application for this country/product
    cursor.execute(
        """SELECT id FROM cert_applications
           WHERE user_id = ? AND origin_country = ? AND hs_code = ?
           AND status IN ('in_progress', 'step1', 'step2')
           ORDER BY created_at DESC LIMIT 1""",
        (current_user["user_id"], body.origin_country.upper(), body.hs_code)
    )
    existing = cursor.fetchone()

    if existing:
        app_id = existing["id"]
        conn.close()
        return {"message": "已有进行中的申请记录，继续使用", "application_id": app_id}

    cursor.execute(
        """INSERT INTO cert_applications
           (user_id, hs_code, origin_country, cert_type, status, current_step, steps_completed)
           VALUES (?, ?, ?, ?, 'in_progress', 1, '{}')""",
        (current_user["user_id"], body.hs_code, body.origin_country.upper(), body.cert_type)
    )
    conn.commit()
    app_id = cursor.lastrowid
    conn.close()

    return {"message": "申请流程已创建", "application_id": app_id}


@router.get("/certificate/application")
async def get_my_applications(current_user: dict = Depends(get_current_user)):
    """
    Get all certificate applications for the current user.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT * FROM cert_applications
           WHERE user_id = ?
           ORDER BY created_at DESC
           LIMIT 20""",
        (current_user["user_id"],)
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "hs_code": r["hs_code"],
            "origin_country": r["origin_country"],
            "cert_type": r["cert_type"],
            "status": r["status"],
            "current_step": r["current_step"],
            "steps_completed": _parse_json_field(r["steps_completed"], {}),
            "ai_doc_generated": bool(r["ai_doc_generated"]),
            "submitted_at": r["submitted_at"],
            "cert_number": r["cert_number"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@router.post("/certificate/document/generate")
async def generate_cert_document(
    body: CertDocGenerateInput,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate Certificate of Origin documents using AI.
    Creates an Exporter's Declaration and Processing Description document.
    This is a Pro+ feature.
    """
    # Check user tier
    from app.routers.auth import get_user_tier_from_db
    tier, _, _, _ = get_user_tier_from_db(current_user["user_id"], DB_PATH)
    if tier == "free":
        raise HTTPException(
            status_code=403,
            detail="AI证书文件生成是 Pro 版专属功能，请先升级"
        )

    api_key = os.getenv("DEEPSEEK_API_KEY")

    # Build document content
    now_str = datetime.now().strftime("%Y年%m月%d日")
    processing_desc = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(body.processing_steps)) if body.processing_steps else "  （由出口商填写具体加工工序）"
    materials_desc = "\n".join(f"  - {s}" for s in body.material_sources) if body.material_sources else "  全部原料产自原产国（本国原料）"

    exporter = body.exporter_name or "【出口商名称】"
    importer = body.importer_name or "【进口商名称】"
    product = body.product_description or f"HS编码 {body.hs_code} 商品"
    hs_code = body.hs_code
    origin = body.origin_country.upper()

    # Get country name
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name_zh FROM africa_countries WHERE code = ?", (origin,))
    row = cursor.fetchone()
    conn.close()
    origin_name = row["name_zh"] if row else origin

    # Get fee info
    conn2 = get_db(DB_PATH)
    cursor2 = conn2.cursor()
    cursor2.execute(
        "SELECT fee_usd_min, fee_usd_max, days_min, days_max, issuing_authority_zh FROM cert_guides WHERE country_code = ? AND is_active = 1 LIMIT 1",
        (origin,)
    )
    guide_row = cursor2.fetchone()
    conn2.close()
    fee_info = f"约 ${guide_row['fee_usd_min']}-${guide_row['fee_usd_max']} USD" if guide_row else "约 $30-100 USD"
    days_info = f"{guide_row['days_min']}-{guide_row['days_max']}个工作日" if guide_row else "3-7个工作日"
    authority = guide_row["issuing_authority_zh"] if guide_row and guide_row["issuing_authority_zh"] else "当地商会"

    # Build the full document
    document = f"""
══════════════════════════════════════════════════════════════
          原产地证明申请书 / EXPORTER'S DECLARATION
══════════════════════════════════════════════════════════════
申请日期：{now_str}
──────────────────────────────────────────────────────────────

【出口商信息 / EXPORTER INFORMATION】
出口商名称：{exporter}
国家：{origin_name}（{origin}）
──────────────────────────────────────────────────────────────

【进口商信息 / IMPORTER INFORMATION】
进口商名称：{importer}
目的国：中华人民共和国（CN）
──────────────────────────────────────────────────────────────

【货物信息 / GOODS INFORMATION】
产品名称：{product}
HS税则号：{hs_code}
原产国：{origin_name}（{origin}）
数量/重量：{body.quantity_kg} kg
FOB货值：USD {body.fob_value_usd:,.2f}
──────────────────────────────────────────────────────────────

【原产地声明 / STATEMENT OF ORIGIN】

我/我们郑重声明，上述货物完全产自或充分加工于 {origin_name}（{origin}），
符合中华人民共和国与 {origin_name} 之间的贸易协定关于原产地的规定。

【加工工序 / PROCESSING STEPS】
{processing_desc}

【原料来源 / MATERIAL SOURCES】
{materials_desc}

──────────────────────────────────────────────────────────────
【办证信息 / CERTIFICATE INFORMATION】
办理机构：{authority}
预计费用：{fee_info}
预计时间：{days_info}
申请流程：联系当地商会 → 准备文件 → 提交申请 → 缴费 → 领取证书
──────────────────────────────────────────────────────────────

【声明 / DECLARATION】
出口商签字/盖章：________________
日    期：{now_str}

本文件由 AfricaZero AI 辅助生成，仅供参考。
最终原产地证书以签发机构正式文件为准。
══════════════════════════════════════════════════════════════
"""

    # If AI is available, use it to polish the document
    if api_key and api_key.startswith("sk-"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

            prompt = f"""你是一名非洲原产地证书合规专家。请为以下货物生成一份专业的英文版出口商声明（Exporter's Declaration）。

货物信息：
- HS编码：{hs_code}
- 原产国：{origin_name}（{origin}）
- 出口商：{exporter}
- 进口商：{importer}
- 数量：{body.quantity_kg}kg
- FOB价值：USD {body.fob_value_usd:,.2f}

加工工序：
{processing_desc}

请生成一份专业格式的英文出口商声明（Exporter's Declaration），用于申请原产地证书（Certificate of Origin）。
格式要正式，包含：出口商信息、货物描述、HS编码、原产地声明、出口商签字栏位。
"""

            response = client.chat.completions.create(
                model="deepseek-chat",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            ai_content = response.choices[0].message.content.strip()
            document += f"\n\n{'═'*60}\n【AI英文版声明 / AI-GENERATED ENGLISH DECLARATION】\n{'═'*60}\n\n{ai_content}\n"
        except Exception:
            pass  # Fall back to template

    return CertDocGenerateResult(
        document_type="exporter_declaration",
        content=document.strip(),
        format="text",
        generated_at=now_str,
        usage_note="此文件为模板，正式使用前请补充完整信息并加盖出口商公章，然后提交至当地商会办理原产地证书。"
    )


@router.get("/certificate/steps")
async def get_cert_steps(country_code: str):
    """
    Get the step-by-step certificate application process for a country.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM cert_guides WHERE is_active = 1 AND country_code = ? LIMIT 1",
        (country_code.upper(),)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="暂无该国家的办证指南")

    steps_raw = _parse_json_field(row["step_sequence"], [])
    docs_raw = _parse_json_field(row["doc_requirements"], [])

    # Parse step sequence into structured steps
    steps = []
    for i, step_raw in enumerate(steps_raw):
        if "│" in step_raw:
            parts = [p.strip() for p in step_raw.split("│")]
            steps.append({"step": i + 1, "title": parts[0] if len(parts) > 0 else f"步骤{i+1}", "description": " | ".join(parts[1:])})
        else:
            steps.append({"step": i + 1, "title": f"步骤{i+1}", "description": step_raw})

    return {
        "country_code": row["country_code"],
        "country_name_zh": row["country_name_zh"],
        "cert_type_zh": row["cert_type_zh"],
        "issuing_authority_zh": row["issuing_authority_zh"],
        "fee_usd_min": row["fee_usd_min"],
        "fee_usd_max": row["fee_usd_max"],
        "fee_cny_note": row["fee_cny_note"],
        "days_min": row["days_min"],
        "days_max": row["days_max"],
        "steps": steps,
        "documents_required": docs_raw,
        "notes": row["notes"],
        "website_url": row["website_url"],
    }
