"""
Freight routes and cost estimation API.
"""
import json
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.models.database import get_db, get_db_path

router = APIRouter()
DB_PATH = get_db_path()


# ─── Schemas ────────────────────────────────────────────────────────────────────

class FreightRoute(BaseModel):
    id: int
    origin_country: str
    origin_port: str
    origin_port_zh: str
    dest_country: str
    dest_port: str
    dest_port_zh: str
    transport_type: str
    cost_min_usd: float
    cost_max_usd: float
    transit_days_min: int
    transit_days_max: int
    notes: Optional[str] = None


class FreightEstimateInput(BaseModel):
    origin_country: str = Field(..., min_length=2, max_length=3, description="原产国 ISO code")
    dest_port: str = Field(..., description="目的港代码: SHA/CAN/NGB/TJN/XMN")
    quantity_kg: float = Field(..., gt=0, description="货物总重量 kg")
    transport_type: str = Field(default="sea20gp", description="运输类型: sea20gp/sea40hp/air")


class FreightEstimateResult(BaseModel):
    origin_country: str
    origin_port: str
    origin_port_zh: str
    dest_port: str
    dest_port_zh: str
    transport_type: str
    quantity_kg: float
    container_suggestion: str
    sea_freight_usd: float
    sea_freight_cny: float
    port_charges_usd: float
    insurance_usd: float
    clearance_agent_fee_cny: float
    domestic_logistics_cny: float
    total_freight_cny: float
    total_freight_usd: float
    transit_days: str
    notes: Optional[str] = None
    breakdown: dict


# ─── Routes ────────────────────────────────────────────────────────────────────

@router.get("/freight/routes")
async def list_freight_routes(
    origin_country: Optional[str] = Query(None, description="原产国 ISO code"),
    dest_port: Optional[str] = Query(None, description="目的港代码"),
    transport_type: Optional[str] = Query(None, description="运输类型"),
):
    """
    List all available freight routes with optional filtering.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    sql = "SELECT * FROM freight_routes WHERE is_active = 1"
    params = []
    if origin_country:
        sql += " AND origin_country = ?"
        params.append(origin_country.upper())
    if dest_port:
        sql += " AND dest_port = ?"
        params.append(dest_port.upper())
    if transport_type:
        sql += " AND transport_type = ?"
        params.append(transport_type)

    sql += " ORDER BY origin_country, dest_port, transport_type"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "origin_country": r["origin_country"],
            "origin_port": r["origin_port"],
            "origin_port_zh": r["origin_port_zh"],
            "dest_country": r["dest_country"],
            "dest_port": r["dest_port"],
            "dest_port_zh": r["dest_port_zh"],
            "transport_type": r["transport_type"],
            "cost_min_usd": r["cost_min_usd"],
            "cost_max_usd": r["cost_max_usd"],
            "transit_days_min": r["transit_days_min"],
            "transit_days_max": r["transit_days_max"],
            "notes": r["notes"],
        }
        for r in rows
    ]


@router.get("/freight/routes/countries")
async def list_freight_countries():
    """
    List all countries that have freight route data.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT DISTINCT fr.origin_country, ac.name_zh, ac.name_en
           FROM freight_routes fr
           LEFT JOIN africa_countries ac ON ac.code = fr.origin_country
           WHERE fr.is_active = 1
           ORDER BY ac.name_zh"""
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"code": r["origin_country"], "name_zh": r["name_zh"], "name_en": r["name_en"]} for r in rows]


@router.get("/freight/routes/ports")
async def list_dest_ports():
    """
    List all available destination ports.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT DISTINCT dest_port, dest_port_zh
           FROM freight_routes
           WHERE is_active = 1 AND dest_country = 'CN'
           ORDER BY dest_port_zh"""
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"code": r["dest_port"], "name_zh": r["dest_port_zh"]} for r in rows]


@router.post("/freight/estimate")
async def estimate_freight_cost(input: FreightEstimateInput):
    """
    Estimate total freight and logistics cost for importing goods from Africa to China.
    """
    conn = get_db(DB_PATH)
    cursor = conn.cursor()

    # Find matching route
    cursor.execute(
        """SELECT * FROM freight_routes
           WHERE is_active = 1
             AND origin_country = ?
             AND dest_port = ?
             AND transport_type = ?
           LIMIT 1""",
        (input.origin_country.upper(), input.dest_port.upper(), input.transport_type)
    )
    route = cursor.fetchone()
    conn.close()

    if not route:
        # Try any transport type
        cursor2 = get_db(DB_PATH)
        cur2 = cursor2.cursor()
        cur2.execute(
            """SELECT * FROM freight_routes
               WHERE is_active = 1
                 AND origin_country = ?
                 AND dest_port = ?
               ORDER BY
                 CASE transport_type
                   WHEN 'sea20gp' THEN 1
                   WHEN 'sea40hp' THEN 2
                   WHEN 'air' THEN 3
                   ELSE 4
                 END
               LIMIT 1""",
            (input.origin_country.upper(), input.dest_port.upper())
        )
        route = cur2.fetchone()
        cursor2.close()
        if not route:
            raise HTTPException(
                status_code=404,
                detail=f"暂无 {input.origin_country.upper()} → {input.dest_port.upper()} 的运费数据，请联系客服添加"
            )

    # Get exchange rate
    exchange_rate = 7.25  # fallback

    qty = input.quantity_kg

    # ── Container recommendation ──────────────────────────────────────────────
    if input.transport_type == "air":
        container_suggestion = f"空运：约 {qty}kg，建议分批空运"
        sea_freight_usd = (route["cost_min_usd"] + route["cost_max_usd"]) / 2
        port_charges_usd = 0
        insurance_rate = 0.005  # 0.5% of CIF
    elif input.transport_type == "sea40hp":
        if qty <= 15000:
            container_suggestion = f"货物约 {qty}kg，建议使用 20GP（装{_max_20gp(qty)}kg），剩余可下次发"
        else:
            container_suggestion = f"货物约 {qty}kg，建议使用 40GP（装{_max_40hp(qty)}kg）"
        sea_freight_usd = (route["cost_min_usd"] + route["cost_max_usd"]) / 2
        port_charges_usd = sea_freight_usd * 0.12
        insurance_rate = 0.005
    else:  # sea20gp
        max_kg_20gp = 18000  # 20GP standard max
        if qty <= max_kg_20gp:
            container_suggestion = f"20GP集装箱（最大约{max_kg_20gp}kg），您约 {qty}kg，刚好装满"
        else:
            n = int(qty / max_kg_20gp) + 1
            container_suggestion = f"建议 {n} 个 20GP 集装箱（共约 {n * max_kg_20gp}kg 容量）"
        sea_freight_usd = (route["cost_min_usd"] + route["cost_max_usd"]) / 2
        port_charges_usd = sea_freight_usd * 0.12
        insurance_rate = 0.005

    # Insurance
    insurance_usd = sea_freight_usd * insurance_rate

    # Conversion
    sea_freight_cny = sea_freight_usd * exchange_rate
    insurance_cny = insurance_usd * exchange_rate

    # Clearance + domestic logistics
    clearance_agent_fee_cny = 800 + (qty / 1000) * 100  # 基础800元 + 按吨加100元
    domestic_logistics_cny = 500  # 港口到仓库基础费用

    total_freight_cny = sea_freight_cny + port_charges_usd * exchange_rate + insurance_cny + clearance_agent_fee_cny + domestic_logistics_cny
    total_freight_usd = sea_freight_usd + port_charges_usd + insurance_usd + clearance_agent_fee_cny / exchange_rate + domestic_logistics_cny / exchange_rate

    transit_days = f"{route['transit_days_min']}-{route['transit_days_max']}天"

    return FreightEstimateResult(
        origin_country=route["origin_country"],
        origin_port=route["origin_port"],
        origin_port_zh=route["origin_port_zh"],
        dest_port=route["dest_port"],
        dest_port_zh=route["dest_port_zh"],
        transport_type=route["transport_type"],
        quantity_kg=qty,
        container_suggestion=container_suggestion,
        sea_freight_usd=round(sea_freight_usd, 2),
        sea_freight_cny=round(sea_freight_cny, 2),
        port_charges_usd=round(port_charges_usd, 2),
        insurance_usd=round(insurance_usd, 2),
        clearance_agent_fee_cny=round(clearance_agent_fee_cny, 2),
        domestic_logistics_cny=round(domestic_logistics_cny, 2),
        total_freight_cny=round(total_freight_cny, 2),
        total_freight_usd=round(total_freight_usd, 2),
        transit_days=transit_days,
        notes=route["notes"],
        breakdown={
            "sea_freight": {"usd": round(sea_freight_usd, 2), "cny": round(sea_freight_cny, 2)},
            "port_charges": {"usd": round(port_charges_usd, 2)},
            "insurance": {"usd": round(insurance_usd, 2), "cny": round(insurance_cny, 2)},
            "clearance_agent": {"cny": round(clearance_agent_fee_cny, 2)},
            "domestic_logistics": {"cny": round(domestic_logistics_cny, 2)},
            "exchange_rate_used": exchange_rate,
            "currency_note": "海运费估算范围基于市场参考价，实际价格以货代报价为准"
        }
    )


def _max_20gp(kg: float) -> int:
    return min(int(kg / 0.9), 18000)

def _max_40hp(kg: float) -> int:
    return min(int(kg / 0.9), 26000)
