"""
Shared Pydantic schemas for all API endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional


# ─── Tariff ───────────────────────────────────────────────────────────────────

class TariffCalcInput(BaseModel):
    hs_code: str = Field(..., min_length=4, max_length=15, description="HS编码")
    origin_country: str = Field(..., min_length=2, max_length=3, description="原产国 ISO code")
    destination: str = Field(..., description="目的地市场: CN/EU/AFCFTA")
    fob_value: float = Field(..., gt=0, description="FOB货值")
    currency: str = Field(default="USD", description="币种")


class TariffBreakdown(BaseModel):
    fob_value: float
    freight: float
    insurance: float
    tariff_rate: float
    tariff_amount: float
    vat_rate: float
    vat_amount: float
    total_cost: float
    savings_vs_mfn: float


class TariffCalcResult(BaseModel):
    success: bool
    input: TariffCalcInput
    breakdown: Optional[TariffBreakdown]
    origin_qualified: bool
    origin_rule: Optional[str]
    message: str


# ─── Import Cost ──────────────────────────────────────────────────────────────

class ImportCostInput(BaseModel):
    product_name: str = Field(..., min_length=1, description="商品名称")
    quantity_kg: float = Field(..., gt=0, description="采购量(kg)")
    fob_per_kg: float = Field(..., gt=0, description="FOB单价(USD/kg)")
    origin: str = Field(default="ET", max_length=3, description="原产国ISO code")
    destination: str = Field(default="CN", description="目的地市场")


class ImportCostBreakdown(BaseModel):
    fob_value: float
    international_freight: float
    customs_clearance: float
    tariff: float
    vat: float
    total_import_cost: float
    roasting_loss_rate: float
    roasted_yield_kg: float
    domestic_logistics: float
    packaging_cost_per_unit: float
    total_domestic_cost: float
    total_cost: float
    cost_per_package: float
    suggested_retail_price: float
    payback_packages: float


class ImportCostResult(BaseModel):
    success: bool
    input: ImportCostInput
    breakdown: Optional[ImportCostBreakdown]
    origin_certificate_guide: Optional[list[str]]
    message: str


# ─── HS Search ────────────────────────────────────────────────────────────────

class HSSearchResult(BaseModel):
    hs_10: Optional[str]
    name_zh: str
    mfn_rate: float
    category: Optional[str]
    match_score: float = 1.0


# ─── Origin Check ─────────────────────────────────────────────────────────────

class OriginCheckInput(BaseModel):
    product_name: str = Field(default="", description="商品名称")
    hs_code: str = Field(..., min_length=4, description="HS编码")
    origin: str = Field(..., max_length=3, description="原产国ISO code")
    processing_steps: list[str] = Field(default_factory=list, description="加工工序列表")
    material_sources: list[str] = Field(default_factory=list, description="原料来源列表")


class OriginCheckResult(BaseModel):
    qualifies: bool
    rule_applied: Optional[str]
    confidence: float = Field(..., ge=0, le=1)
    reasons: list[str]
    suggestions: list[str]


# ─── Countries ────────────────────────────────────────────────────────────────

class Country(BaseModel):
    id: int
    code: str
    name_zh: str
    name_en: str
    in_afcfta: bool
    has_epa: bool


# ─── Subscription ─────────────────────────────────────────────────────────────

class SubscriptionCheck(BaseModel):
    email: Optional[str] = None
    wechat_id: Optional[str] = None


class SubscriptionStatus(BaseModel):
    tier: str
    expires_at: Optional[str]
    remaining_queries: Optional[int]
