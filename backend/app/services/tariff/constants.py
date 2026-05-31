"""Tariff calculation constants — all hardcoded values centralized here."""
from typing import Final

# ─── Exchange Rate ─────────────────────────────────────────────────────────────
DEFAULT_USD_CNY: Final[float] = 7.25
EXCHANGE_RATE_API_KEY: Final[str] = ""  # loaded from settings

# ─── Shipping Rates (USD/kg) ──────────────────────────────────────────────────
AFRICA_SHIPPING_RATES: Final[dict[str, float]] = {
    "ET": 5.0,  # Ethiopia via Djibouti
    "KE": 4.5,  # Kenya via Mombasa
    "TZ": 4.0,  # Tanzania via Dar es Salaam
    "GH": 4.5,  # Ghana via Tema
    "CI": 5.5,  # Côte d'Ivoire via Abidjan
    "CM": 5.0,  # Cameroon via Douala
    "ZA": 3.5,  # South Africa via Durban/Cape Town
    "NG": 5.0,  # Nigeria via Lagos/Port Harcourt
    "RW": 5.5,  # Rwanda (landlocked, via Mombasa/Dar)
    "UG": 5.0,  # Uganda (landlocked, via Mombasa)
    "MZ": 4.5,  # Mozambique via Beira/Maputo
    "DJ": 5.5,  # Djibouti
    "DEFAULT": 5.5,
}

# ─── Customs & Clearance ──────────────────────────────────────────────────────
CUSTOMS_CLEARANCE_BASE: Final[float] = 2000.0   # RMB per LCL shipment
CUSTOMS_CLEARANCE_PER_KG: Final[float] = 2.0     # RMB/kg

# ─── Domestic Processing ──────────────────────────────────────────────────────
ROASTING_LOSS_RATE: Final[float] = 0.15          # 生豆→熟豆损耗率
DOMESTIC_LOGISTICS: Final[float] = 30.0          # RMB per domestic order
PACKAGING_PER_BAG: Final[float] = 0.5             # RMB per 227g bag
RETAIL_PRICE_MULTIPLIER: Final[float] = 2.5       # cost × 2.5 = suggested retail

# ─── Reference Retail Prices (CNY per 227g) ──────────────────────────────────
RETAIL_REFERENCE: Final[dict[str, float]] = {
    "0901": 89.0,   # Specialty coffee 227g
    "1801": 45.0,   # Cocoa beans
    "0801": 38.0,   # Cashews
    "0802": 35.0,   # Other nuts
    "1207": 28.0,   # Sesame
    "default": 50.0,
}

# ─── Zero-Tariff Countries ─────────────────────────────────────────────────────
CN_ZERO_TARIFF_COUNTRIES: Final[set[str]] = {
    "ET", "ZA", "KE", "GH", "CI", "CM", "TZ", "RW", "UG", "MZ", "NG", "EG", "MA", "DZ", "TN",
    "SD", "AO", "BJ", "BW", "BF", "BI", "CV", "CF", "TD", "CD", "CG", "DJ", "GQ", "ER",
    "GA", "GM", "GN", "GW", "LS", "LR", "LY", "MG", "MW", "ML", "MR", "MU", "NA", "NE", "SN",
    "SC", "SL", "SO", "SS", "TG", "ZM", "ZW", "KM", "ST",
}  # 53个与中国建交的非洲国家（不含斯威士兰）

EU_EPA_COUNTRIES: Final[set[str]] = {"GH", "CI", "CM", "KE", "MZ"}

# ─── Business Constants ────────────────────────────────────────────────────────
FREE_DAILY_LIMIT: Final[int] = 3
TIER_PRICES: Final[dict[str, float]] = {"free": 0, "pro": 99, "enterprise": 298}
TIER_DURATION_DAYS: Final[dict[str, int]] = {"pro": 365, "enterprise": 365}
CONTACT_VIEW_DAILY_QUOTA: Final[dict[str, int]] = {"free": 3, "pro": 20, "enterprise": 999999}
MAX_SUB_ACCOUNTS: Final[int] = 5
