"""
Shared Pydantic schemas for all API endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ─── Auth ─────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    wechat_id: Optional[str] = Field(default=None, max_length=50)


class UserLogin(BaseModel):
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=1, max_length=100)


class UserResponse(BaseModel):
    id: int
    email: str
    tier: str = "free"
    is_admin: bool = False
    subscribed_at: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: Optional[str] = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    remaining_today: int = 3
    max_free_daily: int = 3


# ─── Sub-accounts ─────────────────────────────────────────────────────────────

class SubAccountCreate(BaseModel):
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    name: Optional[str] = Field(default=None, max_length=50)


class SubAccountResponse(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None


# ─── Tariff ───────────────────────────────────────────────────────────────────

class TariffCalcInput(BaseModel):
    hs_code: str = Field(..., min_length=4, max_length=15, description="HS编码")
    origin_country: str = Field(..., min_length=2, max_length=3, description="原产国 ISO code")
    destination: str = Field(..., description="目的地市场: CN/EU/AFCFTA")
    fob_value: float = Field(..., gt=0, description="FOB货值(USD)")
    currency: str = Field(default="USD", description="币种")
    # Optional advanced params
    quantity_kg: float = Field(default=60.0, gt=0, description="采购量(kg)，用于精确计算运费摊薄")
    freight_override: float | None = Field(default=None, description="手动指定运费(USD)，覆盖默认值")
    exchange_rate: float | None = Field(default=None, gt=0, description="USD→CNY汇率，若不填则用默认值7.25")


class TariffBreakdown(BaseModel):
    fob_value: float
    quantity_kg: float
    freight: float
    insurance: float
    tariff_rate: float
    tariff_amount: float
    vat_rate: float
    vat_amount: float
    total_cost: float
    savings_vs_mfn: float
    exchange_rate: float


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
    is_active: bool = True
    days_remaining: Optional[int] = None
    api_enabled: bool = False
    sub_accounts_remaining: int = 0
    user: Optional[UserResponse] = None


class SubscriptionCreate(BaseModel):
    tier: str = Field(..., description="订阅方案: free/pro/enterprise")
    payment_method: str = Field(default="wechat", description="支付方式: wechat/alipay/transfer")
    payment_channel: str = Field(default="mock", description="支付渠道")


class SubscriptionResponse(BaseModel):
    id: int
    tier: str
    amount: float
    currency: str = "CNY"
    payment_method: Optional[str] = None
    payment_channel: str = "mock"
    status: str = "active"
    started_at: Optional[str] = None
    expires_at: Optional[str] = None
    auto_renew: bool = False


# ─── API Keys ─────────────────────────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    name: str = Field(default="", max_length=100, description="密钥名称")
    rate_limit_day: int = Field(default=100, ge=1, le=10000, description="每日调用限额")


class ApiKeyResponse(BaseModel):
    id: int
    key_prefix: str
    name: Optional[str] = None
    tier: str = "enterprise"
    rate_limit_day: int = 100
    is_active: bool = True
    last_used_at: Optional[str] = None
    created_at: Optional[str] = None


class ApiKeyWithPlain(BaseModel):
    id: int
    plain_key: str
    key_prefix: str
    name: Optional[str] = None
    tier: str = "enterprise"
    rate_limit_day: int = 100
    is_active: bool = True
    last_used_at: Optional[str] = None
    created_at: Optional[str] = None


# ─── Freight ─────────────────────────────────────────────────────────────────────

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
    origin_country: str = Field(..., min_length=2, max_length=3)
    dest_port: str = Field(..., description="目的港代码: SHA/CAN/NGB")
    quantity_kg: float = Field(..., gt=0)
    transport_type: str = Field(default="sea20gp")


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


# ─── Certificate ────────────────────────────────────────────────────────────────

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
    format: str
    generated_at: str
    usage_note: str


# ─── Supplier ────────────────────────────────────────────────────────────────────

class SupplierListItem(BaseModel):
    id: int
    name_zh: str
    country: str
    region: Optional[str]
    main_products: list[str]
    main_hs_codes: list[str]
    export_years: int
    verified_chamber: bool
    rating_avg: float
    review_count: int
    status: str
    min_order_kg: Optional[float]


class SupplierSearchResult(BaseModel):
    suppliers: list[SupplierListItem]
    total: int
    page: int
    page_size: int


class SupplierReviewCreate(BaseModel):
    supplier_id: int
    quality_score: float = Field(..., ge=1, le=5)
    delivery_score: float = Field(..., ge=1, le=5)
    communication_score: float = Field(..., ge=1, le=5)
    comment: str = ""
    is_verified_deal: bool = False
