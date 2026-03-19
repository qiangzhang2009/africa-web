"""Tariff and cost calculation service."""
import os
import re
from pathlib import Path
from typing import Optional

from app.models.database import get_db
from app.schemas import TariffBreakdown, ImportCostBreakdown

# ─── Constants ──────────────────────────────────────────────────────────────────

DEFAULT_USD_CNY = 7.25  # fallback exchange rate

# Shipping rate: USD/kg (海运散货, Africa -> China)
AFRICA_SHIPPING_RATES: dict[str, float] = {
    "ET": 5.0,  # Ethiopia via Djibouti
    "KE": 4.5,  # Kenya via Mombasa
    "TZ": 4.0,  # Tanzania
    "GH": 4.5,  # Ghana
    "CI": 5.5,  # Côte d'Ivoire
    "CM": 5.0,  # Cameroon
    "ZA": 3.5,  # South Africa
    "NG": 5.0,  # Nigeria
    "RW": 5.5,  # Rwanda
    "UG": 5.0,  # Uganda
    "MZ": 4.5,  # Mozambique
    "DEFAULT": 5.5,
}

CUSTOMS_CLEARANCE_BASE = 2000.0   # RMB per shipment (LCL)
CUSTOMS_CLEARANCE_PER_KG = 2.0   # RMB/kg

ROASTING_LOSS_RATE = 0.15         # 生豆→熟豆损耗率
DOMESTIC_LOGISTICS = 30.0        # RMB per domestic order
PACKAGING_PER_BAG = 0.5          # RMB per 227g bag
RETAIL_PRICE_MULTIPLIER = 2.5     # cost × 2.5 = suggested retail

RETAIL_REFERENCE: dict[str, float] = {
    "0901": 89.0,   # Specialty coffee 227g
    "1801": 45.0,   # Cocoa beans
    "0801": 38.0,   # Cashews
    "0802": 35.0,   # Other nuts
    "1207": 28.0,   # Sesame
    "default": 50.0,
}

CN_ZERO_TARIFF_COUNTRIES = {
    "ET", "ZA", "KE", "GH", "CI", "CM", "TZ", "RW", "UG", "MZ", "NG", "EG", "MA", "DZ", "TN",
    "SD", "AO", "BJ", "BW", "BF", "BI", "CV", "CF", "TD", "CD", "CG", "DJ", "GQ", "ER", "SZ",
    "GA", "GM", "GN", "GW", "LS", "LR", "LY", "MG", "MW", "ML", "MR", "MU", "NA", "NE", "SN",
    "SC", "SL", "SO", "SS", "TG", "ZM", "ZW",
}

EU_EPA_COUNTRIES = {"GH", "CI", "CM", "EG", "MZ", "MA", "TN"}


# ─── Helper functions ──────────────────────────────────────────────────────────

def get_shipping_rate(origin_country: str) -> float:
    code = origin_country.upper()
    return AFRICA_SHIPPING_RATES.get(code, AFRICA_SHIPPING_RATES["DEFAULT"])


def get_usd_cny_rate() -> float:
    """Get USD→CNY rate. Falls back to DEFAULT_USD_CNY if no API key."""
    return DEFAULT_USD_CNY


def _normalize_hs(code: str) -> str:
    """Remove dots/spaces for DB lookup."""
    return code.replace(".", "").replace(" ", "").replace("-", "")


def _format_hs(code: str) -> str:
    """Add dots to normalized HS code for display."""
    c = _normalize_hs(code)
    if len(c) <= 4:
        return c
    return ".".join(c[i*2:i*2+2] for i in range((len(c)+1)//2))


def get_hs_record(hs_code: str, db_path: str) -> Optional[dict]:
    """Query HS code from DB. Tries exact match first, then prefix match."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    normalized = _normalize_hs(hs_code)

    for length in [10, 8, 6, 4]:
        if len(normalized) < length:
            continue
        code = normalized[:length]
        display = _format_hs(code)
        cursor.execute(
            "SELECT * FROM hs_codes WHERE hs_10 = ? OR hs_8 = ? OR hs_6 = ? OR hs_4 = ? LIMIT 1",
            (display, display, display, display)
        )
        row = cursor.fetchone()
        if row:
            conn.close()
            return dict(row)

    conn.close()
    return None


def get_hs_record_from_name(name: str, db_path: str) -> Optional[dict]:
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM hs_codes WHERE name_zh LIKE ? LIMIT 1",
        (f"%{name}%",)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_category_from_name(name: str) -> str:
    n = name.lower()
    if "咖啡" in name or "coffee" in n:
        return "0901"
    if "可可" in name or "cocoa" in n:
        return "1801"
    if "腰果" in name or "cashew" in n:
        return "0801"
    if "坚果" in name or "nut" in n:
        return "0802"
    if "芝麻" in name or "sesame" in n:
        return "1207"
    return "default"


def is_africa_zero_tariff_country(code: str) -> bool:
    return code.upper() in CN_ZERO_TARIFF_COUNTRIES


def is_eu_epa_country(code: str) -> bool:
    return code.upper() in EU_EPA_COUNTRIES


# ─── Tariff calculation ──────────────────────────────────────────────────────

def calculate_tariff(
    hs_code: str,
    origin_country: str,
    destination: str,
    fob_value: float,
    db_path: str,
) -> dict:
    hs_record = get_hs_record(hs_code, db_path)

    if not hs_record:
        return {
            "success": False,
            "message": f"未找到HS编码: {hs_code}，请检查输入或使用HS查询功能",
            "origin_qualified": False,
            "origin_rule": None,
            "breakdown": None,
        }

    mfn_rate = hs_record["mfn_rate"]
    vat_rate = hs_record["vat_rate"]
    origin_upper = origin_country.upper()

    shipping_rate_usd = get_shipping_rate(origin_upper)
    freight_usd = shipping_rate_usd * max(fob_value / 10, 1)   # scale by approximate qty
    insurance_usd = fob_value * 0.005
    usd_cny = get_usd_cny_rate()

    # Determine tariff rate
    if destination == "CN":
        if is_africa_zero_tariff_country(origin_upper):
            tariff_rate = 0.0
            origin_qualified = True
            origin_rule = "中国对非洲53个建交国零关税政策（2026年5月1日起）"
            message = "符合零关税条件"
        else:
            tariff_rate = mfn_rate
            origin_qualified = False
            origin_rule = None
            message = f"{origin_upper} 不在中国零关税白名单内（仅建交国适用）"

    elif destination == "EU":
        if is_eu_epa_country(origin_upper):
            tariff_rate = 0.0
            origin_qualified = True
            origin_rule = "EU-EPA零关税（增值≥40%估算）"
            message = "可能符合EPA零关税条件（需验证增值比例≥40%）"
        else:
            tariff_rate = mfn_rate
            origin_qualified = False
            origin_rule = None
            message = f"{origin_upper} 未与欧盟签署EPA协议"

    elif destination == "AFCFTA":
        tariff_rate = 0.0
        origin_qualified = True
        origin_rule = "AfCFTA区内优惠税率（增值≥40%）"
        message = "可能符合AfCFTA优惠条件"

    else:
        tariff_rate = mfn_rate
        origin_qualified = False
        origin_rule = None
        message = f"未知目的地市场: {destination}"

    # Calculate in CNY
    fob_cny = fob_value * usd_cny
    freight_cny = freight_usd * usd_cny
    insurance_cny = insurance_usd * usd_cny
    tariff_cny = fob_cny * tariff_rate
    taxable_value = fob_cny + freight_cny + insurance_cny + tariff_cny
    vat_cny = taxable_value * vat_rate
    total_cost_cny = taxable_value + vat_cny
    savings_vs_mfn = fob_cny * mfn_rate

    breakdown = TariffBreakdown(
        fob_value=round(fob_value, 2),
        freight=round(freight_usd, 2),
        insurance=round(insurance_usd, 2),
        tariff_rate=tariff_rate,
        tariff_amount=round(tariff_cny, 2),
        vat_rate=vat_rate,
        vat_amount=round(vat_cny, 2),
        total_cost=round(total_cost_cny, 2),
        savings_vs_mfn=round(savings_vs_mfn, 2),
    )

    return {
        "success": True,
        "message": message,
        "origin_qualified": origin_qualified,
        "origin_rule": origin_rule,
        "breakdown": breakdown,
    }


# ─── Import cost calculation ─────────────────────────────────────────────────

def calculate_import_cost(
    product_name: str,
    quantity_kg: float,
    fob_per_kg: float,
    origin: str,
    db_path: str,
) -> dict:
    origin_upper = origin.upper()
    fob_value = quantity_kg * fob_per_kg
    shipping_rate = get_shipping_rate(origin_upper)
    effective_qty = max(quantity_kg, 10)
    freight_usd = effective_qty * shipping_rate
    insurance_usd = fob_value * 0.005
    usd_cny = get_usd_cny_rate()
    customs_clearance = CUSTOMS_CLEARANCE_BASE + quantity_kg * CUSTOMS_CLEARANCE_PER_KG

    # Tariff
    if is_africa_zero_tariff_country(origin_upper):
        tariff = 0.0
    else:
        hs_rec = get_hs_record_from_name(product_name, db_path)
        tariff = fob_value * usd_cny * (hs_rec["mfn_rate"] if hs_rec else 0.08)

    # VAT
    taxable = fob_value * usd_cny + freight_usd * usd_cny + insurance_usd * usd_cny + tariff
    vat = taxable * 0.13
    total_import = taxable + vat

    # Domestic processing
    roasting_loss = quantity_kg * ROASTING_LOSS_RATE
    roasted_yield = quantity_kg - roasting_loss
    domestic_logistics = DOMESTIC_LOGISTICS
    package_count = int(roasted_yield / 0.227) if roasted_yield >= 0.227 else 1
    packaging = package_count * PACKAGING_PER_BAG
    total_cost = total_import + domestic_logistics + packaging
    cost_per_package = total_cost / package_count if package_count > 0 else 0

    # Suggested retail price
    category = get_category_from_name(product_name)
    ref_price = RETAIL_REFERENCE.get(category, RETAIL_REFERENCE["default"])
    suggested_retail = max(ref_price * 0.8, cost_per_package * RETAIL_PRICE_MULTIPLIER)
    payback = int(total_cost / suggested_retail) if suggested_retail > 0 else 999

    breakdown = ImportCostBreakdown(
        fob_value=round(fob_value * usd_cny, 2),
        international_freight=round(freight_usd * usd_cny, 2),
        customs_clearance=round(customs_clearance, 2),
        tariff=round(tariff, 2),
        vat=round(vat, 2),
        total_import_cost=round(total_import, 2),
        roasting_loss_rate=ROASTING_LOSS_RATE,
        roasted_yield_kg=round(roasted_yield, 3),
        domestic_logistics=round(domestic_logistics, 2),
        packaging_cost_per_unit=round(packaging, 2),
        total_domestic_cost=round(domestic_logistics + packaging, 2),
        total_cost=round(total_cost, 2),
        cost_per_package=round(cost_per_package, 2),
        suggested_retail_price=round(suggested_retail, 2),
        payback_packages=payback,
    )

    guide = [
        "准备合同、发票、装箱单（由出口方提供）",
        "联系产地证的办理机构或代理报关行",
        "向出口国商检机构申请原产地证书（Form A或相应优惠证书）",
        "货物发运后，将证书随货寄送中国",
        "货物到港后，报关时提交原产地证书申请零关税待遇",
        "海关审核通过后，零关税放行",
        "预计办理周期：出口国办理3-5个工作日 + 快递2-3天",
    ]

    return {
        "success": True,
        "message": "计算完成",
        "breakdown": breakdown,
        "origin_certificate_guide": guide,
    }
