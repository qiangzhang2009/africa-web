"""
Database models using SQLite or PostgreSQL (Neon).
Automatically detects DATABASE_URL to choose the right driver.
Schema: africa_countries, hs_codes, policy_rules, users, calculations,
        subscriptions, api_keys, sub_accounts, usage_logs
"""
import os
import sqlite3
import json
import hashlib
import secrets
from pathlib import Path
from datetime import datetime
from typing import Any, Optional


# ─── Password hashing ─────────────────────────────────────────────────────────

try:
    from passlib.context import CryptContext
    _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    def hash_password(password: str) -> str:
        return _pwd_ctx.hash(password)
    def verify_password(plain: str, hashed: str) -> bool:
        return _pwd_ctx.verify(plain, hashed)
except ImportError:
    import bcrypt as _bc
    def hash_password(password: str) -> str:
        return _bc.hashpw(password.encode(), _bc.gensalt()).decode()
    def verify_password(plain: str, hashed: str) -> bool:
        return _bc.checkpw(plain.encode(), hashed.encode())


# ─── API Key helpers ─────────────────────────────────────────────────────────

def generate_api_key() -> tuple[str, str]:
    """Generate a random API key. Returns (plain_key, hash_for_db)."""
    plain = f"az_{secrets.token_urlsafe(32)}"
    h = hashlib.sha256(plain.encode()).hexdigest()
    return plain, h


def mask_api_key(plain: str) -> str:
    """Return a masked display version of an API key."""
    if len(plain) < 12:
        return plain[:4] + "***"
    return plain[:10] + "***" + plain[-4:]


# ─── PostgreSQL parameter style adapter ────────────────────────────────────────
# psycopg2 uses %s, sqlite uses ?.  We normalise to %s everywhere and adapt here.

_sql_placeholder = "?"   # SQLite style (default)

def _adapt_sql(sql: str) -> str:
    """Convert ? placeholders to the driver's native style."""
    if _is_postgres():
        return sql.replace("?", "%s")
    return sql  # SQLite: already uses ?


def _adapt_insert(sql: str) -> str:
    """
    Convert INSERT SQL so it returns the inserted row id.
    - PostgreSQL: appends RETURNING id
    - SQLite: uses cursor.lastrowid (no change needed)
    """
    if _is_postgres():
        return sql.rstrip().rstrip(";") + " RETURNING id"
    return sql


def _adapt_params(params: tuple) -> tuple:
    """Pass params through unchanged (both drivers accept tuples)."""
    return params


# ─── Date function helpers (compatible with both SQLite and PostgreSQL) ─────────

def sql_now() -> str:
    """Return the SQL expression for 'current date' in the active driver's syntax."""
    return "CURRENT_DATE" if _is_postgres() else "DATE('now')"


def sql_now_datetime() -> str:
    """Return the SQL expression for current timestamp as TEXT (for TEXT columns)."""
    return "NOW()::text" if _is_postgres() else "datetime('now')"


def sql_cast_date(col: str) -> str:
    """
    Cast a TEXT date column to DATE for safe comparisons.
    PostgreSQL: expires_at is TEXT, must cast to compare with CURRENT_DATE.
    SQLite: text columns compare correctly with date strings.
    """
    return f"DATE({col})" if _is_postgres() else col


def sql_date_sub_days(days: int) -> str:
    """Return SQL for 'today minus N days' in the active driver's syntax."""
    if _is_postgres():
        return f"CURRENT_DATE - INTERVAL '{days} days'"
    return f"DATE('now', '-{days} days')"


def sql_date_add_days(days: int) -> str:
    """Return SQL for 'today plus N days' in the active driver's syntax."""
    if _is_postgres():
        return f"CURRENT_DATE + INTERVAL '{days} days'"
    return f"DATE('now', '+{days} days')"


# ─── Database driver detection ────────────────────────────────────────────────

def _is_postgres() -> bool:
    url = os.getenv("DATABASE_URL", "")
    return url.startswith("postgres://") or url.startswith("postgresql://")


# ─── PostgreSQL compatibility layer ─────────────────────────────────────────

def _pg_connect(url: str):
    """Create a fresh psycopg2 connection. Returns (raw_conn, wrapped_cursor)."""
    import psycopg2
    raw = url.replace("postgresql://", "postgres://")
    conn = psycopg2.connect(raw, connect_timeout=10)

    class _DictCursor:
        def __init__(self, conn):
            self._conn = conn
            self._cursor = conn.cursor()

        def execute(self, sql: str, params: tuple = ()):
            adapted = sql.replace("?", "%s") if _is_postgres() else sql
            try:
                return self._cursor.execute(adapted, params)
            except Exception:
                self._conn.rollback()
                raise

        def executemany(self, sql: str, seq_of_params):
            adapted = sql.replace("?", "%s") if _is_postgres() else sql
            try:
                return self._cursor.executemany(adapted, seq_of_params)
            except Exception:
                self._conn.rollback()
                raise

        def fetchone(self):
            row = self._cursor.fetchone()
            if row is None:
                return None
            return _DictRow(self._cursor.description, row)

        def fetchall(self):
            return [_DictRow(self._cursor.description, r) for r in self._cursor.fetchall()]

        @property
        def description(self):
            return self._cursor.description

    class _DictRow:
        """Row that supports both row[i] and row['colname'] access."""
        def __init__(self, description, values):
            self._desc = description
            self._vals = values
            self._map = {col[0]: i for i, col in enumerate(description)}

        def __getitem__(self, key):
            if isinstance(key, int):
                return self._vals[key]
            return self._vals[self._map[key]]

        def keys(self):
            return [col[0] for col in self._desc]

        def values(self):
            return self._vals

        def __contains__(self, key):
            return key in self._map

    return conn, _DictCursor(conn)


class _PgConnection:
    """
    PostgreSQL connection wrapper that creates a fresh connection per request.
    Each get_db() call → new connection → avoids stale/aborted transactions.
    """
    def __init__(self, pg_url: str):
        self._url = pg_url
        self._conn, self._cursor = _pg_connect(pg_url)

    def cursor(self):
        return self._cursor

    def commit(self):
        try:
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


# ─── get_db / get_db_path ────────────────────────────────────────────────────

def get_db(path: str):
    """
    Return a database connection (SQLite or PostgreSQL based on DATABASE_URL).
    Interface: get_db(path) -> connection
              conn.cursor() -> cursor with dict-like rows
              conn.commit() / conn.close()
    """
    if _is_postgres():
        return _PgConnection(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_db_path() -> str:
    """
    Returns the canonical DATABASE_URL or path used by all modules.
    For SQLite: resolves relative paths, creates parent dir.
    For PostgreSQL: returns the connection URL as-is.
    """
    raw = os.getenv("DATABASE_URL", "data/africa_zero.db")
    if raw.startswith("postgres://") or raw.startswith("postgresql://"):
        return raw
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path.resolve())


# ─── Schema ──────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
-- Africa 53 countries whitelist
CREATE TABLE IF NOT EXISTS africa_countries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT UNIQUE NOT NULL,
    name_zh     TEXT NOT NULL,
    name_en     TEXT NOT NULL,
    in_afcfta  INTEGER DEFAULT 1,
    has_epa     INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- HS codes (focus on Africa-import热门品类)
CREATE TABLE IF NOT EXISTS hs_codes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    hs_4        TEXT NOT NULL,
    hs_6        TEXT,
    hs_8        TEXT,
    hs_10       TEXT UNIQUE,
    name_zh     TEXT NOT NULL,
    name_en     TEXT,
    mfn_rate    REAL NOT NULL,
    vat_rate    REAL DEFAULT 0.13,
    category    TEXT,
    updated_at  TEXT DEFAULT (datetime('now'))
);

-- Policy rules
CREATE TABLE IF NOT EXISTS policy_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    market          TEXT NOT NULL,
    rule_type       TEXT NOT NULL,
    hs_pattern      TEXT,
    rule_text       TEXT NOT NULL,
    rate            REAL,
    effective_date  TEXT,
    source_url      TEXT,
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- Market Analysis / Product Selection
CREATE TABLE IF NOT EXISTS market_analysis (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    category            TEXT NOT NULL,
    product_name_zh     TEXT NOT NULL,
    product_name_en     TEXT,
    main_hs_codes       TEXT NOT NULL,
    origin_countries     TEXT NOT NULL,
    target_china_market TEXT NOT NULL,
    import_requirements TEXT,
    zero_tariff_china   INTEGER DEFAULT 0,
    tariff_rate         REAL,
    market_size_usd     TEXT,
    growth_rate         TEXT,
    top_importers       TEXT,
    supplier_countries  TEXT,
    key_suppliers       TEXT,
    certification_needs TEXT,
    logistics_notes     TEXT,
    risk_factors        TEXT,
    recommendation      TEXT,
    status              TEXT DEFAULT 'active',
    updated_at          TEXT DEFAULT (datetime('now'))
);

-- Users (extended with auth fields)
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    wechat_id       TEXT,
    tier            TEXT DEFAULT 'free',
    is_admin        INTEGER DEFAULT 0,
    is_active       INTEGER DEFAULT 1,
    subscribed_at   TEXT,
    expires_at      TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Calculation history
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
);

-- Subscriptions
CREATE TABLE IF NOT EXISTS subscriptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    tier            TEXT NOT NULL,
    amount          REAL DEFAULT 0,
    currency        TEXT DEFAULT 'CNY',
    payment_method  TEXT,
    payment_channel TEXT DEFAULT 'mock',
    status          TEXT DEFAULT 'active',
    started_at      TEXT,
    expires_at      TEXT,
    auto_renew      INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- API Keys
CREATE TABLE IF NOT EXISTS api_keys (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    key_hash        TEXT NOT NULL,
    key_prefix      TEXT NOT NULL,
    name            TEXT,
    tier            TEXT DEFAULT 'enterprise',
    rate_limit_day  INTEGER DEFAULT 100,
    is_active       INTEGER DEFAULT 1,
    last_used_at    TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Sub-accounts
CREATE TABLE IF NOT EXISTS sub_accounts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_user_id      INTEGER NOT NULL,
    email               TEXT NOT NULL,
    password_hash       TEXT NOT NULL,
    name                TEXT,
    is_active           INTEGER DEFAULT 1,
    created_at          TEXT DEFAULT (datetime('now'))
);

-- API usage logs
CREATE TABLE IF NOT EXISTS usage_logs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER,
    api_key_id          INTEGER,
    endpoint            TEXT,
    ip_address          TEXT,
    user_agent          TEXT,
    response_time_ms    INTEGER,
    status_code         INTEGER,
    created_at          TEXT DEFAULT (datetime('now'))
);

-- Freight shipping routes
CREATE TABLE IF NOT EXISTS freight_routes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    origin_country      TEXT NOT NULL,
    origin_port         TEXT,
    origin_port_zh      TEXT,
    dest_country        TEXT DEFAULT 'CN',
    dest_port           TEXT NOT NULL,
    dest_port_zh       TEXT NOT NULL,
    transport_type      TEXT DEFAULT 'sea20gp',
    cost_min_usd       REAL NOT NULL,
    cost_max_usd       REAL NOT NULL,
    transit_days_min    INTEGER,
    transit_days_max   INTEGER,
    notes               TEXT,
    is_active           INTEGER DEFAULT 1,
    updated_at          TEXT DEFAULT (datetime('now'))
);

-- Certificate of Origin guide by country
CREATE TABLE IF NOT EXISTS cert_guides (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code        TEXT NOT NULL,
    country_name_zh    TEXT NOT NULL,
    cert_type           TEXT DEFAULT 'CO',
    cert_type_zh       TEXT DEFAULT '原产地证书',
    issuing_authority   TEXT,
    issuing_authority_zh TEXT,
    website_url         TEXT,
    fee_usd_min         REAL,
    fee_usd_max        REAL,
    fee_cny_note        TEXT,
    days_min           INTEGER,
    days_max           INTEGER,
    doc_requirements    TEXT,
    step_sequence       TEXT,
    api_available       INTEGER DEFAULT 0,
    notes               TEXT,
    is_active           INTEGER DEFAULT 1,
    updated_at          TEXT DEFAULT (datetime('now'))
);

-- Supplier database
CREATE TABLE IF NOT EXISTS suppliers (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name_zh            TEXT NOT NULL,
    name_en            TEXT,
    country             TEXT NOT NULL,
    region             TEXT,
    main_products       TEXT,
    main_hs_codes       TEXT,
    contact_name        TEXT,
    contact_email       TEXT,
    contact_phone       TEXT,
    website             TEXT,
    min_order_kg        REAL,
    payment_terms       TEXT,
    export_years        INTEGER DEFAULT 0,
    annual_export_tons REAL,
    verified_chamber    INTEGER DEFAULT 0,
    verified_实地拜访   INTEGER DEFAULT 0,
    verified_sgs        INTEGER DEFAULT 0,
    rating_avg          REAL DEFAULT 0,
    review_count        INTEGER DEFAULT 0,
    status              TEXT DEFAULT 'verified',
    intro               TEXT,
    certifications      TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now')),
    UNIQUE(name_zh, country)
);

-- Supplier reviews
CREATE TABLE IF NOT EXISTS supplier_reviews (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id         INTEGER NOT NULL,
    user_id             INTEGER,
    user_email          TEXT,
    quality_score       REAL,
    delivery_score      REAL,
    communication_score REAL,
    comment             TEXT,
    is_verified_deal    INTEGER DEFAULT 0,
    created_at          TEXT DEFAULT (datetime('now'))
);

-- Certificate application records (user workflow tracking)
CREATE TABLE IF NOT EXISTS cert_applications (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL,
    hs_code             TEXT,
    origin_country       TEXT,
    cert_type           TEXT DEFAULT 'CO',
    status              TEXT DEFAULT 'in_progress',
    current_step        INTEGER DEFAULT 1,
    steps_completed      TEXT DEFAULT '{}',
    ai_doc_generated    INTEGER DEFAULT 0,
    submitted_at        TEXT,
    cert_number         TEXT,
    notes               TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_hs_codes_hs4     ON hs_codes(hs_4);
CREATE INDEX IF NOT EXISTS idx_hs_codes_name    ON hs_codes(name_zh);
CREATE INDEX IF NOT EXISTS idx_policy_market    ON policy_rules(market);
CREATE INDEX IF NOT EXISTS idx_calc_user        ON calculations(user_id);
CREATE INDEX IF NOT EXISTS idx_subs_user       ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_user   ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_sub_accounts_parent ON sub_accounts(parent_user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_key  ON usage_logs(api_key_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_day  ON usage_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_freight_origin   ON freight_routes(origin_country);
CREATE INDEX IF NOT EXISTS idx_cert_guides_country ON cert_guides(country_code);
CREATE INDEX IF NOT EXISTS idx_suppliers_country ON suppliers(country);
CREATE INDEX IF NOT EXISTS idx_supplier_reviews_sid ON supplier_reviews(supplier_id);
"""


# ─── PostgreSQL Schema (SERIAL, CURRENT_TIMESTAMP, ON CONFLICT) ─────────────────

SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS africa_countries (
    id          SERIAL PRIMARY KEY,
    code        TEXT UNIQUE NOT NULL,
    name_zh     TEXT NOT NULL,
    name_en     TEXT NOT NULL,
    in_afcfta  INTEGER DEFAULT 1,
    has_epa     INTEGER DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hs_codes (
    id          SERIAL PRIMARY KEY,
    hs_4        TEXT NOT NULL,
    hs_6        TEXT,
    hs_8        TEXT,
    hs_10       TEXT UNIQUE,
    name_zh     TEXT NOT NULL,
    name_en     TEXT,
    mfn_rate    REAL NOT NULL,
    vat_rate    REAL DEFAULT 0.13,
    category    TEXT,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS policy_rules (
    id              SERIAL PRIMARY KEY,
    market          TEXT NOT NULL,
    rule_type       TEXT NOT NULL,
    hs_pattern      TEXT,
    rule_text       TEXT NOT NULL,
    rate            REAL,
    effective_date  TEXT,
    source_url      TEXT,
    updated_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    wechat_id       TEXT,
    tier            TEXT DEFAULT 'free',
    is_admin        INTEGER DEFAULT 0,
    is_active       INTEGER DEFAULT 1,
    subscribed_at   TEXT,
    expires_at      TEXT,
    created_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS calculations (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER,
    product_name    TEXT,
    hs_code         TEXT,
    origin          TEXT,
    destination     TEXT,
    fob_value       REAL,
    result_json     TEXT,
    total           REAL,
    created_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    tier            TEXT NOT NULL,
    amount          REAL DEFAULT 0,
    currency        TEXT DEFAULT 'CNY',
    payment_method  TEXT,
    payment_channel TEXT DEFAULT 'mock',
    status          TEXT DEFAULT 'active',
    started_at      TEXT,
    expires_at      TEXT,
    auto_renew      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_keys (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    key_hash        TEXT NOT NULL,
    key_prefix      TEXT NOT NULL,
    name            TEXT,
    tier            TEXT DEFAULT 'enterprise',
    rate_limit_day  INTEGER DEFAULT 100,
    is_active       INTEGER DEFAULT 1,
    last_used_at    TEXT,
    created_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sub_accounts (
    id                  SERIAL PRIMARY KEY,
    parent_user_id      INTEGER NOT NULL,
    email               TEXT NOT NULL,
    password_hash       TEXT NOT NULL,
    name                TEXT,
    is_active           INTEGER DEFAULT 1,
    created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usage_logs (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER,
    api_key_id          INTEGER,
    endpoint            TEXT,
    ip_address          TEXT,
    user_agent          TEXT,
    response_time_ms    INTEGER,
    status_code         INTEGER,
    created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS freight_routes (
    id                  SERIAL PRIMARY KEY,
    origin_country      TEXT NOT NULL,
    origin_port         TEXT,
    origin_port_zh      TEXT,
    dest_country        TEXT DEFAULT 'CN',
    dest_port           TEXT NOT NULL,
    dest_port_zh        TEXT NOT NULL,
    transport_type      TEXT DEFAULT 'sea20gp',
    cost_min_usd        REAL NOT NULL,
    cost_max_usd        REAL NOT NULL,
    transit_days_min    INTEGER,
    transit_days_max   INTEGER,
    notes               TEXT,
    is_active           INTEGER DEFAULT 1,
    updated_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

# ─── Product Selection / Market Analysis ──────────────────────────────────────
# 非洲选品清单：按品类、国家、目标市场、进口要求等维度建立选品决策数据库
CREATE TABLE IF NOT EXISTS market_analysis (
    id                  SERIAL PRIMARY KEY,
    category            TEXT NOT NULL,          # 品类大类，如"咖啡"、"可可"、"坚果"
    product_name_zh     TEXT NOT NULL,          # 产品中文名
    product_name_en     TEXT,                   # 产品英文名
    main_hs_codes       TEXT NOT NULL,         # 主要HS编码（竖线分隔）
    origin_countries     TEXT NOT NULL,          # 主要原产国（竖线分隔，如"ET|KE|TZ"）
    target_china_market TEXT NOT NULL,          # 中国市场定位，如"精品电商"、"大宗贸易"、"食品加工"
    import_requirements  TEXT,                  # 进口要求：检验检疫/许可证等
    zero_tariff_china   INTEGER DEFAULT 0,      # 中国是否零关税
    tariff_rate         REAL,                  # 中国MFN税率
    market_size_usd     TEXT,                  # 全球市场规模估算（如"$120亿美元"）
    growth_rate         TEXT,                   # 年增长率
    top_importers       TEXT,                   # 主要进口国
    supplier_countries  TEXT,                   # 主要供应商国家
    key_suppliers       TEXT,                  # 知名供应商
    certification_needs TEXT,                   # 需要的认证（如有机/Fairtrade/雨林联盟）
    logistics_notes     TEXT,                   # 物流注意事项
    risk_factors        TEXT,                   # 风险因素
    recommendation      TEXT,                   # 综合推荐理由
    status              TEXT DEFAULT 'active',  # active / hidden / featured
    updated_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cert_guides (
    id                  SERIAL PRIMARY KEY,
    country_code        TEXT NOT NULL,
    country_name_zh     TEXT NOT NULL,
    cert_type           TEXT DEFAULT 'CO',
    cert_type_zh        TEXT DEFAULT '原产地证书',
    issuing_authority   TEXT,
    issuing_authority_zh TEXT,
    website_url         TEXT,
    fee_usd_min         REAL,
    fee_usd_max         REAL,
    fee_cny_note        TEXT,
    days_min            INTEGER,
    days_max            INTEGER,
    doc_requirements    TEXT,
    step_sequence       TEXT,
    api_available       INTEGER DEFAULT 0,
    notes               TEXT,
    is_active           INTEGER DEFAULT 1,
    updated_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS suppliers (
    id                  SERIAL PRIMARY KEY,
    name_zh             TEXT NOT NULL,
    name_en             TEXT,
    country             TEXT NOT NULL,
    region              TEXT,
    main_products       TEXT,
    main_hs_codes       TEXT,
    contact_name        TEXT,
    contact_email       TEXT,
    contact_phone       TEXT,
    website             TEXT,
    min_order_kg       REAL,
    payment_terms       TEXT,
    export_years        INTEGER DEFAULT 0,
    annual_export_tons  REAL,
    verified_chamber     INTEGER DEFAULT 0,
    verified_实地拜访    INTEGER DEFAULT 0,
    verified_sgs         INTEGER DEFAULT 0,
    rating_avg           REAL DEFAULT 0,
    review_count         INTEGER DEFAULT 0,
    status               TEXT DEFAULT 'verified',
    intro                TEXT,
    certifications       TEXT,
    created_at           TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name_zh, country)
);

CREATE TABLE IF NOT EXISTS supplier_reviews (
    id                  SERIAL PRIMARY KEY,
    supplier_id         INTEGER NOT NULL,
    user_id             INTEGER,
    user_email          TEXT,
    quality_score       REAL,
    delivery_score      REAL,
    communication_score REAL,
    comment             TEXT,
    is_verified_deal    INTEGER DEFAULT 0,
    created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_calc_user     ON calculations(user_id);
CREATE INDEX IF NOT EXISTS idx_calc_day      ON calculations(created_at);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_sub_accounts_parent ON sub_accounts(parent_user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_key ON usage_logs(api_key_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_day ON usage_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_freight_origin ON freight_routes(origin_country);
CREATE INDEX IF NOT EXISTS idx_cert_guides_country ON cert_guides(country_code);
CREATE INDEX IF NOT EXISTS idx_suppliers_country ON suppliers(country);
CREATE INDEX IF NOT EXISTS idx_supplier_reviews_sid ON supplier_reviews(supplier_id);
"""


# ─── Seed data ────────────────────────────────────────────────────────────────

AFRICA_COUNTRIES = [
    ("ET", "埃塞俄比亚", "Ethiopia", 1, 0),
    ("ZA", "南非", "South Africa", 1, 1),
    ("KE", "肯尼亚", "Kenya", 1, 0),
    ("GH", "加纳", "Ghana", 1, 1),
    ("CI", "科特迪瓦", "Côte d'Ivoire", 1, 1),
    ("CM", "喀麦隆", "Cameroon", 1, 1),
    ("TZ", "坦桑尼亚", "Tanzania", 1, 0),
    ("RW", "卢旺达", "Rwanda", 1, 0),
    ("UG", "乌干达", "Uganda", 1, 0),
    ("MZ", "莫桑比克", "Mozambique", 1, 1),
    ("NG", "尼日利亚", "Nigeria", 1, 0),
    ("EG", "埃及", "Egypt", 1, 1),
    ("MA", "摩洛哥", "Morocco", 1, 1),
    ("DZ", "阿尔及利亚", "Algeria", 1, 0),
    ("TN", "突尼斯", "Tunisia", 1, 1),
    ("SD", "苏丹", "Sudan", 1, 0),
    ("AO", "安哥拉", "Angola", 1, 0),
    ("BJ", "贝宁", "Benin", 1, 0),
    ("BW", "博茨瓦纳", "Botswana", 1, 0),
    ("BF", "布基纳法索", "Burkina Faso", 1, 0),
    ("BI", "布隆迪", "Burundi", 1, 0),
    ("CV", "佛得角", "Cape Verde", 1, 0),
    ("CF", "中非", "Central African Republic", 1, 0),
    ("TD", "乍得", "Chad", 1, 0),
    ("CD", "刚果（金）", "DR Congo", 1, 0),
    ("CG", "刚果（布）", "Republic of the Congo", 1, 0),
    ("DJ", "吉布提", "Djibouti", 1, 0),
    ("GQ", "赤道几内亚", "Equatorial Guinea", 1, 0),
    ("ER", "厄立特里亚", "Eritrea", 1, 0),
    ("KM", "科摩罗", "Comoros", 1, 0),
    ("GA", "加蓬", "Gabon", 1, 0),
    ("GM", "冈比亚", "Gambia", 1, 0),
    ("GN", "几内亚", "Guinea", 1, 0),
    ("GW", "几内亚比绍", "Guinea-Bissau", 1, 0),
    ("LS", "莱索托", "Lesotho", 1, 0),
    ("LR", "利比里亚", "Liberia", 1, 0),
    ("LY", "利比亚", "Libya", 1, 0),
    ("MG", "马达加斯加", "Madagascar", 1, 0),
    ("MW", "马拉维", "Malawi", 1, 0),
    ("ML", "马里", "Mali", 1, 0),
    ("MR", "毛里塔尼亚", "Mauritania", 1, 0),
    ("MU", "毛里求斯", "Mauritius", 1, 0),
    ("NA", "纳米比亚", "Namibia", 1, 0),
    ("NE", "尼日尔", "Niger", 1, 0),
    ("SN", "塞内加尔", "Senegal", 1, 0),
    ("ST", "圣多美和普林西比", "Sao Tome and Principe", 1, 0),
    ("SC", "塞舌尔", "Seychelles", 1, 0),
    ("SL", "塞拉利昂", "Sierra Leone", 1, 0),
    ("SO", "索马里", "Somalia", 1, 0),
    ("SS", "南苏丹", "South Sudan", 1, 0),
    ("TG", "多哥", "Togo", 1, 0),
    ("ZM", "赞比亚", "Zambia", 1, 0),
    ("ZW", "津巴布韦", "Zimbabwe", 1, 0),
]

HS_CODES_SEED = [
    # ============================================================
    # 一、咖啡与茶 (0901-0903)
    # ============================================================
    # 0901.11.00 MFN=8%, VAT=9% (生豆属农产品，2026增值税法9%档)
    ("0901", "0901.11", "0901.11.00", "0901.11.00.10", "咖啡豆，未焙炒，非速溶用，生豆", "Coffee, not roasted, not instant, raw", 0.08, 0.09, "咖啡"),
    ("0901", "0901.11", "0901.11.00", "0901.11.00.90", "咖啡豆，未焙炒，速溶用，生豆", "Coffee, not roasted, for instant", 0.08, 0.09, "咖啡"),
    ("0901", "0901.12", "0901.12.00", "0901.12.00.00", "咖啡豆，未焙炒，已浸除咖啡碱", "Coffee, not roasted, decaffeinated", 0.08, 0.09, "咖啡"),
    ("0901", "0901.21", "0901.21.00", "0901.21.00.00", "咖啡豆，已焙炒，未浸除咖啡碱", "Coffee, roasted, not decaffeinated", 0.15, 0.13, "咖啡"),
    ("0901", "0901.22", "0901.22.00", "0901.22.00.00", "咖啡豆，已焙炒，已浸除咖啡碱", "Coffee, roasted, decaffeinated", 0.15, 0.13, "咖啡"),
    ("0901", "0901.90", "0901.90.00", "0901.90.00.00", "咖啡壳；咖啡代用品", "Coffee husks; coffee substitutes", 0.08, 0.09, "咖啡"),
    # 茶 0902
    ("0902", "0902.10", "0902.10.00", "0902.10.00.00", "绿茶（未发酵），包装量≤3kg", "Green tea (not fermented), in immediate packings <=3kg", 0.15, 0.13, "茶叶"),
    ("0902", "0902.20", "0902.20.00", "0902.20.00.00", "绿茶（未发酵），包装量>3kg", "Green tea (not fermented), in immediate packings >3kg", 0.15, 0.13, "茶叶"),
    ("0902", "0902.30", "0902.30.00", "0902.30.00.00", "红茶（发酵）及部分发酵茶，内包装≤3kg", "Black tea & partly fermented, <=3kg", 0.15, 0.13, "茶叶"),
    ("0902", "0902.40", "0902.40.00", "0902.40.00.00", "红茶（发酵）及部分发酵茶，内包装>3kg", "Black tea & partly fermented, >3kg", 0.15, 0.13, "茶叶"),
    ("0902", "0902.40", "0902.40.10", "0902.40.10.00", "普洱熟茶，渥堆发酵", "Pu-erh fermented tea, post-fermented", 0.15, 0.13, "茶叶"),
    # ============================================================
    # 二、可可 (1801-1806)
    # ============================================================
    ("1801", "1801.00", "1801.00.00", "1801.00.00.00", "可可豆，生或焙炒", "Cocoa beans, raw or roasted", 0.08, 0.13, "可可"),
    ("1802", "1802.00", "1802.00.00", "1802.00.00.00", "可可荚、壳、皮及废料", "Cocoa shells, husks, skins & waste", 0.08, 0.09, "可可"),
    ("1803", "1803.10", "1803.10.00", "1803.10.00.00", "可可膏，未脱脂", "Cocoa paste, not defatted", 0.10, 0.13, "可可"),
    ("1803", "1803.20", "1803.20.00", "1803.20.00.00", "可可膏，全部或部分脱脂", "Cocoa paste, wholly or partly defatted", 0.10, 0.13, "可可"),
    ("1804", "1804.00", "1804.00.00", "1804.00.00.00", "可可脂、油", "Cocoa butter, fat and oil", 0.20, 0.13, "可可"),
    ("1805", "1805.00", "1805.00.00", "1805.00.00.00", "可可粉，不含甜味剂", "Cocoa powder, not containing added sweetening matter", 0.15, 0.13, "可可"),
    ("1806", "1806.10", "1806.10.00", "1806.10.00.00", "可可粉，含甜味剂", "Cocoa powder, sweetened", 0.10, 0.13, "可可"),
    ("1806", "1806.20", "1806.20.00", "1806.20.00.00", "其他含可可固体块状食品，≥2kg", "Other food preparations containing cocoa, >=2kg", 0.10, 0.13, "可可"),
    ("1806", "1806.31", "1806.31.00", "1806.31.00.00", "夹心巧克力及含可可食品，块状或条状", "Chocolate, filled, in blocks or bars", 0.08, 0.13, "可可"),
    ("1806", "1806.32", "1806.32.00", "1806.32.00.00", "不夹心巧克力及含可可食品，块状或条状", "Chocolate, not filled, in blocks or bars", 0.08, 0.13, "可可"),
    # ============================================================
    # 三、坚果与果仁 (0801-0814)
    # ============================================================
    # 椰子 0801
    ("0801", "0801.11", "0801.11.00", "0801.11.00.00", "椰子，干的，未去壳", "Coconuts, dried, in shell", 0.12, 0.09, "坚果"),
    ("0801", "0801.12", "0801.12.00", "0801.12.00.00", "椰子，干的，去壳", "Coconuts, dried, shelled", 0.12, 0.09, "坚果"),
    ("0801", "0801.13", "0801.13.00", "0801.13.00.00", "鲜椰子，未去壳", "Coconuts, fresh, in shell", 0.12, 0.09, "坚果"),
    # 腰果 0801.32
    ("0801", "0801.31", "0801.31.00", "0801.31.00.00", "腰果，未去壳", "Cashew nuts, in shell", 0.10, 0.09, "坚果"),
    ("0801", "0801.32", "0801.32.00", "0801.32.00.10", "腰果，去壳，RW500级（优质）", "Cashew nuts, shelled, RW500 grade premium", 0.10, 0.09, "坚果"),
    ("0801", "0801.32", "0801.32.00", "0801.32.00.20", "腰果，去壳，W240级（特级）", "Cashew nuts, shelled, W240 grade", 0.10, 0.09, "坚果"),
    ("0801", "0801.32", "0801.32.00", "0801.32.00.90", "腰果，去壳，其他等级", "Cashew nuts, shelled, other grades", 0.10, 0.09, "坚果"),
    # 巴西坚果 0801.19
    ("0801", "0801.19", "0801.19.00", "0801.19.00.00", "巴西坚果，未去壳", "Brazil nuts, in shell", 0.10, 0.09, "坚果"),
    ("0801", "0801.21", "0801.21.00", "0801.21.00.00", "巴西坚果，去壳", "Brazil nuts, shelled", 0.10, 0.09, "坚果"),
    # 坚果（榛子/杏仁/开心果/夏威夷果） 0802
    ("0802", "0802.11", "0802.11.00", "0802.11.00.00", "杏仁，未去壳", "Almonds, in shell", 0.10, 0.09, "坚果"),
    ("0802", "0802.12", "0802.12.00", "0802.12.00.00", "杏仁，去壳", "Almonds, shelled", 0.10, 0.09, "坚果"),
    ("0802", "0802.21", "0802.21.00", "0802.21.00.00", "榛子，未去壳", "Hazelnuts, in shell", 0.12, 0.09, "坚果"),
    ("0802", "0802.22", "0802.22.00", "0802.22.00.00", "榛子，去壳", "Hazelnuts, shelled", 0.12, 0.09, "坚果"),
    ("0802", "0802.31", "0802.31.00", "0802.31.00.00", "核桃，未去壳", "Walnuts, in shell", 0.12, 0.09, "坚果"),
    ("0802", "0802.32", "0802.32.00", "0802.32.00.00", "核桃，去壳", "Walnuts, shelled", 0.12, 0.09, "坚果"),
    ("0802", "0802.41", "0802.41.00", "0802.41.00.00", "栗子，未去壳", "Chestnuts, in shell", 0.12, 0.09, "坚果"),
    ("0802", "0802.42", "0802.42.00", "0802.42.00.00", "栗子，去壳", "Chestnuts, shelled", 0.12, 0.09, "坚果"),
    ("0802", "0802.51", "0802.51.00", "0802.51.00.00", "阿月浑子果（开心果），未去壳", "Pistachios, in shell", 0.12, 0.09, "坚果"),
    ("0802", "0802.52", "0802.52.00", "0802.52.00.00", "阿月浑子果（开心果），去壳", "Pistachios, shelled", 0.12, 0.09, "坚果"),
    ("0802", "0802.61", "0802.61.00", "0802.61.00.00", "夏威夷果（Macadamia），未去壳", "Macadamia nuts, in shell", 0.12, 0.09, "坚果"),
    ("0802", "0802.62", "0802.62.00", "0802.62.00.00", "夏威夷果（Macadamia），去壳", "Macadamia nuts, shelled", 0.12, 0.09, "坚果"),
    ("0802", "0802.70", "0802.70.00", "0802.70.00.00", "可乐果（Cola nuts）", "Kola nuts", 0.12, 0.09, "坚果"),
    ("0802", "0802.80", "0802.80.00", "0802.80.00.00", "槟榔果（Betel nuts）", "Betel nuts (Areca nuts)", 0.12, 0.09, "坚果"),
    # 花生 1202
    ("1202", "1202.30", "1202.30.00", "1202.30.00.00", "花生果（带壳），种子用除外", "Groundnuts in shell, not for sowing", 0.09, 0.09, "坚果"),
    ("1202", "1202.41", "1202.41.00", "1202.41.00.00", "花生仁（去壳），种子用除外", "Groundnuts, shelled, not for sowing", 0.09, 0.09, "坚果"),
    ("1202", "1202.42", "1202.42.00", "1202.42.00.00", "花生仁，去壳，未焙炒或未烹煮", "Groundnuts, shelled, not roasted or cooked", 0.09, 0.09, "坚果"),
    # ============================================================
    # 四、油籽与植物油 (1201-1518)
    # ============================================================
    # 芝麻 1207
    ("1207", "1207.40", "1207.40.00", "1207.40.00.00", "芝麻种子，种用除外", "Sesame seeds, not for sowing", 0.10, 0.09, "油籽"),
    ("1207", "1207.50", "1207.50.00", "1207.50.00.00", "芥子种子，种用除外", "Rape or colza seeds, not for sowing", 0.09, 0.09, "油籽"),
    ("1207", "1207.60", "1207.60.00", "1207.60.00.00", "红花种子，种用除外", "Safflower seeds, not for sowing", 0.09, 0.09, "油籽"),
    ("1207", "1207.91", "1207.91.00", "1207.91.00.00", "罂粟种子", "Poppy seeds", 0.09, 0.09, "油籽"),
    ("1207", "1207.99", "1207.99.00", "1207.99.00.00", "其他含油子仁及果实", "Other oil seeds and oleaginous fruits", 0.09, 0.09, "油籽"),
    # 葵花籽 1206
    ("1206", "1206.00", "1206.00.00", "1206.00.00.00", "葵花子，种用除外", "Sunflower seeds, not for sowing", 0.09, 0.09, "油籽"),
    # 大豆 1201
    ("1201", "1201.10", "1201.10.00", "1201.10.00.00", "大豆，种子用", "Soya beans, for sowing", 0.09, 0.09, "油籽"),
    ("1201", "1201.90", "1201.90.00", "1201.90.00.00", "大豆，种用除外，非转基因", "Soya beans, not for sowing, non-GM", 0.09, 0.09, "油籽"),
    # 棉籽 1207.20
    ("1207", "1207.20", "1207.20.00", "1207.20.00.00", "棉籽，种用除外", "Cotton seeds, not for sowing", 0.09, 0.09, "油籽"),
    # 亚麻籽 1204
    ("1204", "1204.00", "1204.00.00", "1204.00.00.00", "亚麻籽，种用除外", "Linseed, not for sowing", 0.09, 0.09, "油籽"),
    # 植物油 1507-1518
    ("1507", "1507.10", "1507.10.00", "1507.10.00.00", "粗豆油，未经化学改性", "Soya-bean oil, crude, not chemically modified", 0.09, 0.09, "油脂"),
    ("1507", "1507.90", "1507.90.00", "1507.90.00.00", "豆油及其分离品，精制除外", "Soya-bean oil, refined, not chemically modified", 0.09, 0.09, "油脂"),
    ("1508", "1508.10", "1508.10.00", "1508.10.00.00", "花生油，粗的", "Groundnut oil, crude", 0.10, 0.09, "油脂"),
    ("1508", "1508.90", "1508.90.00", "1508.90.00.00", "花生油，精制", "Groundnut oil, refined", 0.10, 0.09, "油脂"),
    ("1509", "1509.10", "1509.10.00", "1509.10.00.00", "初榨橄榄油", "Virgin olive oil", 0.10, 0.09, "油脂"),
    ("1509", "1509.90", "1509.90.00", "1509.90.00.00", "精制橄榄油及其分离品", "Refined olive oil and its fractions", 0.10, 0.09, "油脂"),
    ("1511", "1511.10", "1511.10.00", "1511.10.00.00", "粗棕榈油", "Palm oil, crude", 0.09, 0.09, "油脂"),
    ("1511", "1511.90", "1511.90.00", "1511.90.00.00", "棕榈油及其分离品，精制", "Palm oil, refined", 0.09, 0.09, "油脂"),
    ("1512", "1512.11", "1512.11.00", "1512.11.00.00", "粗葵花籽油或红花油", "Sunflower-seed or safflower oil, crude", 0.09, 0.09, "油脂"),
    ("1512", "1512.19", "1512.19.00", "1512.19.00.00", "葵花籽油或红花油，精制", "Sunflower-seed or safflower oil, refined", 0.09, 0.09, "油脂"),
    ("1513", "1513.11", "1513.11.00", "1513.11.00.00", "粗椰子油（复制油脂）", "Coconut (copra) oil, crude", 0.09, 0.09, "油脂"),
    ("1513", "1513.21", "1513.21.00", "1513.21.00.00", "粗棕榈仁油或巴巴苏棕榈油", "Palm kernel or babassu oil, crude", 0.09, 0.09, "油脂"),
    ("1514", "1514.11", "1514.11.00", "1514.11.00.00", "低芥酸菜子油，粗的", "Low erucic acid rape or colza oil, crude", 0.09, 0.09, "油脂"),
    ("1515", "1515.19", "1515.19.00", "1515.19.00.00", "亚麻子油，粗的", "Linseed oil, crude", 0.09, 0.09, "油脂"),
    ("1515", "1515.29", "1515.29.00", "1515.29.00.00", "亚麻子油，精制", "Linseed oil, refined", 0.09, 0.09, "油脂"),
    ("1515", "1515.50", "1515.50.00", "1515.50.00.00", "芝麻油及其分离品", "Sesame oil and its fractions", 0.10, 0.09, "油脂"),
    ("1516", "1516.10", "1516.10.00", "1516.10.00.00", "动物油脂，精制或分馏", "Animal fats and oils, refined", 0.08, 0.09, "油脂"),
    ("1516", "1516.20", "1516.20.00", "1516.20.00.00", "植物油脂，精制或分馏，氢化处理", "Vegetable fats and oils, refined, hydrogenated", 0.10, 0.09, "油脂"),
    # ============================================================
    # 五、香料 (0904-0911)
    # ============================================================
    ("0904", "0904.11", "0904.11.00", "0904.11.00.00", "胡椒，已磨碎或已研磨，黑胡椒", "Pepper, crushed or ground, black", 0.20, 0.13, "香料"),
    ("0904", "0904.12", "0904.12.00", "0904.12.00.00", "胡椒，已磨碎或已研磨，白胡椒", "Pepper, crushed or ground, white", 0.20, 0.13, "香料"),
    ("0904", "0904.21", "0904.21.00", "0904.21.00.00", "辣椒干及辣椒粉，甜椒除外", "Dried fruits of genus Capsicum, sweet peppers excluded", 0.20, 0.13, "香料"),
    ("0904", "0904.22", "0904.22.00", "0904.22.00.00", "辣椒，已磨碎或已研磨", "Fruits of genus Capsicum, crushed or ground", 0.20, 0.13, "香料"),
    ("0905", "0905.00", "0905.00.00", "0905.00.00.00", "香草（Vanilla，香荚兰）", "Vanilla", 0.15, 0.13, "香料"),
    ("0906", "0906.11", "0906.11.00", "0906.11.00.00", "锡兰桂皮，未磨碎", "Cinnamon (Cinnamomum zeylanicum Blume), neither crushed nor ground", 0.15, 0.13, "香料"),
    ("0906", "0906.19", "0906.19.00", "0906.19.00.00", "其他桂皮，未磨碎", "Cinnamon, neither crushed nor ground, other", 0.15, 0.13, "香料"),
    ("0906", "0906.20", "0906.20.00", "0906.20.00.00", "桂皮，已磨碎或已研磨", "Cinnamon, crushed or ground", 0.15, 0.13, "香料"),
    ("0907", "0907.00", "0907.00.00", "0907.00.00.00", "丁香（whole fruit, clavus）", "Cloves (whole fruit, cloves and stems)", 0.08, 0.13, "香料"),
    ("0908", "0908.10", "0908.10.00", "0908.10.00.00", "肉豆蔻", "Nutmeg", 0.08, 0.13, "香料"),
    ("0908", "0908.20", "0908.20.00", "0908.20.00.00", "肉豆蔻衣", "Mace", 0.08, 0.13, "香料"),
    ("0908", "0908.30", "0908.30.00", "0908.30.00.00", "豆蔻", "Cardamoms", 0.08, 0.13, "香料"),
    ("0909", "0909.21", "0909.21.00", "0909.21.00.00", "芫荽种子，未磨碎", "Coriander seeds, neither crushed nor ground", 0.15, 0.13, "香料"),
    ("0909", "0909.22", "0909.22.00", "0909.22.00.00", "芫荽种子，已磨碎", "Coriander seeds, crushed or ground", 0.15, 0.13, "香料"),
    ("0909", "0909.31", "0909.31.00", "0909.31.00.00", "枯茗种子（孜然），未磨碎", "Cumin seeds, neither crushed nor ground", 0.15, 0.13, "香料"),
    ("0909", "0909.32", "0909.32.00", "0909.32.00.00", "枯茗种子（孜然），已磨碎", "Cumin seeds, crushed or ground", 0.15, 0.13, "香料"),
    ("0910", "0910.10", "0910.10.00", "0910.10.00.00", "姜，未磨碎或已磨碎", "Ginger, neither crushed nor ground", 0.15, 0.09, "香料"),
    ("0910", "0910.20", "0910.20.00", "0910.20.00.00", "藏红花（番红花）", "Saffron", 0.02, 0.13, "香料"),
    ("0910", "0910.30", "0910.30.00", "0910.30.00.00", "姜黄（turmeric）", "Turmeric (curcuma)", 0.15, 0.09, "香料"),
    ("0910", "0910.91", "0910.91.00", "0910.91.00.00", "混合香料", "Mixtures of two or more of the products of different headings", 0.15, 0.13, "香料"),
    # ============================================================
    # 六、矿产与矿砂 (2601-2839)
    # ============================================================
    ("2601", "2601.11", "2601.11.00", "2601.11.00.00", "铁矿砂及其精矿，焙烧黄铁矿除外，Fe≥62%", "Iron ores and concentrates, roasted iron pyrites excluded, Fe>=62%", 0.02, 0.13, "矿产"),
    ("2601", "2601.12", "2601.12.00", "2601.12.00.00", "铁矿砂及其精矿，焙烧黄铁矿，Fe≥62%", "Iron ores and concentrates, roasted iron pyrites", 0.02, 0.13, "矿产"),
    ("2601", "2601.20", "2601.20.00", "2601.20.00.00", "焙烧黄铁矿", "Roasted iron pyrites", 0.02, 0.13, "矿产"),
    ("2602", "2602.00", "2602.00.00", "2602.00.00.00", "锰矿砂及其精矿，含锰量≥44%", "Manganese ores and concentrates, Mn>=44%", 0.02, 0.13, "矿产"),
    ("2603", "2603.00", "2603.00.00", "2603.00.00.00", "铜矿砂及其精矿，Cu≥20%", "Copper ores and concentrates, Cu>=20%", 0.02, 0.13, "矿产"),
    ("2604", "2604.00", "2604.00.00", "2604.00.00.00", "镍矿砂及其精矿", "Nickel ores and concentrates", 0.02, 0.13, "矿产"),
    ("2605", "2605.00", "2605.00.00", "2605.00.00.00", "钴矿砂及其精矿", "Cobalt ores and concentrates", 0.02, 0.13, "矿产"),
    ("2606", "2606.00", "2606.00.00", "2606.00.00.00", "铝矿砂及其精矿（铝土矿）", "Aluminium ores and concentrates (bauxite)", 0.02, 0.13, "矿产"),
    ("2607", "2607.00", "2607.00.00", "2607.00.00.00", "铅矿砂及其精矿", "Lead ores and concentrates", 0.02, 0.13, "矿产"),
    ("2608", "2608.00", "2608.00.00", "2608.00.00.00", "锌矿砂及其精矿", "Zinc ores and concentrates", 0.02, 0.13, "矿产"),
    ("2609", "2609.00", "2609.00.00", "2609.00.00.00", "锡矿砂及其精矿", "Tin ores and concentrates", 0.02, 0.13, "矿产"),
    ("2610", "2610.00", "2610.00.00", "2610.00.00.00", "铬矿砂及其精矿", "Chromium ores and concentrates", 0.02, 0.13, "矿产"),
    ("2611", "2611.00", "2611.00.00", "2611.00.00.00", "钨矿砂及其精矿", "Tungsten ores and concentrates", 0.02, 0.13, "矿产"),
    ("2612", "2612.10", "2612.10.00", "2612.10.00.00", "铀矿砂及其精矿", "Uranium ores and concentrates", 0.02, 0.13, "矿产"),
    ("2612", "2612.20", "2612.20.00", "2612.20.00.00", "钍矿砂及其精矿", "Thorium ores and concentrates", 0.02, 0.13, "矿产"),
    ("2613", "2613.10", "2613.10.00", "2613.10.00.00", "钼矿砂及其精矿，焙烧", "Molybdenum ores and concentrates, roasted", 0.02, 0.13, "矿产"),
    ("2613", "2613.90", "2613.90.00", "2613.90.00.00", "钼矿砂及其精矿，未焙烧", "Molybdenum ores and concentrates, not roasted", 0.02, 0.13, "矿产"),
    ("2614", "2614.00", "2614.00.00", "2614.00.00.00", "钛矿砂及其精矿", "Titanium ores and concentrates", 0.02, 0.13, "矿产"),
    ("2615", "2615.10", "2615.10.00", "2615.10.00.00", "锆矿砂及其精矿", "Zirconium ores and concentrates", 0.02, 0.13, "矿产"),
    ("2615", "2615.90", "2615.90.00", "2615.90.00.00", "钽铌矿砂及其精矿", "Tantalum/niobium ores and concentrates", 0.02, 0.13, "矿产"),
    ("2616", "2616.10", "2616.10.00", "2616.10.00.00", "贵金属矿砂及其精矿，金", "Precious metal ores and concentrates, gold", 0.02, 0.13, "矿产"),
    ("2617", "2617.10", "2617.10.00", "2617.10.00.00", "锑矿砂及其精矿", "Antimony ores and concentrates", 0.02, 0.13, "矿产"),
    ("2618", "2618.00", "2618.00.00", "2618.00.00.00", "锰铁归低品位矿渣粒化", "Granulated slag from the manufacture of iron or steel", 0.02, 0.13, "矿产"),
    ("2619", "2619.00", "2619.00.00", "2619.00.00.00", "钢铁归低品位矿渣", "Slag, dross from manufacture of iron or steel", 0.02, 0.13, "矿产"),
    ("2620", "2620.11", "2620.11.00", "2620.11.00.00", "含硬锌渣，含锌≥55%", "Ash and residues, containing mainly zinc, Zn>=55%", 0.02, 0.13, "矿产"),
    ("2620", "2620.19", "2620.19.00", "2620.19.00.00", "其他含锌残渣", "Ash and residues, containing mainly zinc, other", 0.02, 0.13, "矿产"),
    ("2621", "2621.10", "2621.10.00", "2621.10.00.00", "焚化的城市垃圾残渣", "Ash and residues from the incineration of municipal waste", 0.02, 0.13, "矿产"),
    ("2621", "2621.90", "2621.90.00", "2621.90.00.00", "其他矿残渣及灰渣", "Other ash and residues; seaweit ash", 0.02, 0.13, "矿产"),
    # 贱金属 2801-2839
    ("2801", "2801.10", "2801.10.00", "2801.10.00.00", "氯", "Chlorine", 0.05, 0.13, "化工"),
    ("2802", "2802.00", "2802.00.00", "2802.00.00.00", "硫磺，升华的、沉淀的、胶态的", "Sulphur, sublimed, precipitated, colloidal", 0.05, 0.13, "化工"),
    ("2803", "2803.00", "2803.00.00", "2803.00.00.00", "碳（炭黑及其他碳）", "Carbon (carbon blacks and other forms of carbon)", 0.02, 0.13, "化工"),
    ("2804", "2804.10", "2804.10.00", "2804.10.00.00", "氢", "Hydrogen", 0.05, 0.13, "化工"),
    ("2805", "2805.11", "2805.11.00", "2805.11.00.00", "碱金属，钠", "Alkali metals, sodium", 0.05, 0.13, "化工"),
    ("2806", "2806.10", "2806.10.00", "2806.10.00.00", "氯化氢（盐酸）", "Hydrogen chloride (hydrochloric acid)", 0.05, 0.13, "化工"),
    ("2807", "2807.00", "2807.00.00", "2807.00.00.00", "硫酸；发烟硫酸", "Sulphuric acid; oleum", 0.05, 0.13, "化工"),
    ("2808", "2808.00", "2808.00.00", "2808.00.00.00", "硝酸；磺硝酸", "Nitric acid; sulphonitric acids", 0.05, 0.13, "化工"),
    ("2809", "2809.10", "2809.10.00", "2809.10.00.00", "五氧化二磷", "Diphosphorus pentoxide", 0.05, 0.13, "化工"),
    ("2810", "2810.00", "2810.00.00", "2810.00.00.00", "硼的氧化物；硼酸", "Oxides of boron; boric acid", 0.05, 0.13, "化工"),
    ("2811", "2811.11", "2811.11.00", "2811.11.00.00", "氟化氢（氢氟酸）", "Hydrogen fluoride (hydrofluoric acid)", 0.05, 0.13, "化工"),
    ("2811", "2811.19", "2811.19.00", "2811.19.00.00", "其他无机酸", "Other inorganic acids", 0.05, 0.13, "化工"),
    ("2812", "2812.10", "2812.1000", "2812.1000.00", "非金属卤化物", "Halides and halide oxides of non-metals", 0.05, 0.13, "化工"),
    ("2814", "2814.10", "2814.10.00", "2814.10.00.00", "氨，无水的", "Ammonia, anhydrous", 0.05, 0.13, "化工"),
    ("2814", "2814.20", "2814.20.00", "2814.20.00.00", "氨，水溶液（氨水）", "Ammonia in aqueous solution", 0.05, 0.13, "化工"),
    ("2815", "2815.11", "2815.11.00", "2815.1100.00", "氢氧化钠（烧碱），固体", "Sodium hydroxide (caustic soda), solid", 0.08, 0.13, "化工"),
    ("2815", "2815.12", "2815.12.00", "2815.1200.00", "氢氧化钠（烧碱），水溶液（液碱）", "Sodium hydroxide in aqueous solution (lye)", 0.08, 0.13, "化工"),
    ("2816", "2816.10", "2816.10.00", "2816.1000.00", "氢氧化镁及过氧化镁", "Hydroxide and peroxide of magnesium", 0.05, 0.13, "化工"),
    ("2818", "2818.10", "2818.10.00", "2818.1000.00", "人造刚玉，氧化铝含量≥98.5%", "Artificial corundum, Al2O3>=98.5%", 0.08, 0.13, "化工"),
    ("2820", "2820.00", "2820.00.00", "2820.0000.00", "氢氧化锰", "Manganese dioxide", 0.05, 0.13, "化工"),
    ("2821", "2821.10", "2821.10.00", "2821.1000.00", "氧化铁及氧化铁氢氧化物", "Iron oxides and hydroxides", 0.05, 0.13, "化工"),
    ("2822", "2822.00", "2822.00.00", "2822.0000.00", "氧化钴及氢氧化钴", "Cobalt oxides and hydroxides", 0.05, 0.13, "化工"),
    ("2825", "2825.50", "2825.50.00", "2825.5000.00", "氧化铜及氢氧化铜", "Copper oxides and hydroxides", 0.05, 0.13, "化工"),
    ("2825", "2825.60", "2825.60.00", "2825.6000.00", "氧化锗及氧化锆", "Germanium oxides and zirconium dioxide", 0.05, 0.13, "化工"),
    ("2827", "2827.10", "2827.10.00", "2827.1000.00", "氯化铵（磷肥原料）", "Ammonium chloride", 0.05, 0.13, "化工"),
    ("2827", "2827.35", "2827.35.00", "2827.3500.00", "氯化镍", "Nickel chloride", 0.05, 0.13, "化工"),
    ("2828", "2828.10", "2828.10.00", "2828.1000.00", "次氯酸钙（漂粉）", "Calcium hypochlorite", 0.05, 0.13, "化工"),
    ("2829", "2829.11", "2829.11.00", "2829.1100.00", "氯酸钠", "Sodium chlorate", 0.05, 0.13, "化工"),
    ("2830", "2830.10", "2830.10.00", "2830.1000.00", "硫化钠", "Sodium sulphides", 0.05, 0.13, "化工"),
    ("2831", "2831.10", "2831.10.00", "2831.1000.00", "连二亚硫酸钠（保险粉）", "Sodium dithionite; sodium sulphoxylate", 0.05, 0.13, "化工"),
    ("2832", "2832.10", "2832.2100", "2832.2100.00", "亚硫酸钠", "Sodium sulphite", 0.05, 0.13, "化工"),
    ("2832", "2832.20", "2832.2200", "2832.2200.00", "其他亚硫酸盐", "Other sulphites", 0.05, 0.13, "化工"),
    ("2833", "2833.11", "2833.1100", "2833.1100.00", "硫酸钠（元明粉）", "Sodium sulphate", 0.05, 0.13, "化工"),
    ("2833", "2833.21", "2833.2100", "2833.2100.00", "硫酸镁（泻盐）", "Magnesium sulphate", 0.05, 0.13, "化工"),
    ("2834", "2834.21", "2834.2100", "2834.2100.00", "硝酸钾（钾肥）", "Potassium nitrate", 0.05, 0.13, "化工"),
    ("2835", "2835.10", "2835.1000", "2835.1000.00", "次磷酸盐及亚磷酸盐", "Phosphinates and phosphonates", 0.05, 0.13, "化工"),
    ("2836", "2836.50", "2836.5000", "2836.5000.00", "碳酸钙（轻质）", "Calcium carbonate, light", 0.05, 0.13, "化工"),
    ("2836", "2836.60", "2836.6000", "2836.6000.00", "碳酸镁（菱镁矿）", "Magnesium carbonate (magnesite)", 0.05, 0.13, "化工"),
    ("2837", "2837.11", "2837.1100", "2837.1100.00", "氰化钠", "Sodium cyanide", 0.05, 0.13, "化工"),
    ("2839", "2839.11", "2839.1100", "2839.1100.00", "偏硅酸钠", "Sodium metasilicates", 0.05, 0.13, "化工"),
    # ============================================================
    # 七、天然橡胶 (4001-4017)
    # ============================================================
    ("4001", "4001.10", "4001.10.00", "4001.10.00.00", "天然胶乳，不论是否预硫化", "Natural rubber latex, whether or not pre-vulcanised", 0.10, 0.09, "橡胶"),
    ("4001", "4001.21", "4001.21.00", "4001.21.00.00", "烟胶片（RSS1-5级）", "Smoked sheets, grade RSS1-5", 0.10, 0.09, "橡胶"),
    ("4001", "4001.22", "4001.22.00", "4001.22.00.00", "技术分类天然橡胶（TSNR）", "Technically specified natural rubber (TSNR)", 0.10, 0.09, "橡胶"),
    ("4001", "4001.29", "4001.29.00", "4001.29.00.00", "其他形状的天然橡胶", "Natural rubber in other forms", 0.10, 0.09, "橡胶"),
    ("4002", "4002.11", "4002.11.00", "4002.11.00.00", "丁苯橡胶胶乳", "Styrene-butadiene rubber latex (SBR)", 0.07, 0.13, "橡胶"),
    ("4002", "4002.19", "4002.19.00", "4002.19.00.00", "丁苯橡胶，非胶乳", "Styrene-butadiene rubber, non-latex", 0.07, 0.13, "橡胶"),
    ("4002", "4002.20", "4002.20.00", "4002.2000.00", "丁基橡胶", "Butyl rubber", 0.07, 0.13, "橡胶"),
    # ============================================================
    # 八、皮革与生皮 (4101-4113)
    # ============================================================
    ("4101", "4101.20", "4101.20.00", "4101.20.00.00", "生牛皮（整张），每张≤8kg", "Raw hides and skin of bovine, whole, <=8kg", 0.05, 0.09, "皮革"),
    ("4101", "4101.50", "4101.50.00", "4101.50.00.00", "生牛皮（整张），每张>16kg", "Raw hides and skin of bovine, whole, >16kg", 0.05, 0.09, "皮革"),
    ("4101", "4101.90", "4101.90.00", "4101.90.00.00", "其他生牛皮，包括整张", "Other raw hides and skin of bovine", 0.05, 0.09, "皮革"),
    ("4103", "4103.20", "4103.20.00", "4103.2000.00", "爬行动物生皮", "Raw hides and skin of reptiles", 0.10, 0.09, "皮革"),
    ("4103", "4103.30", "4103.3000.00", "4103.3000.00.00", "生马皮", "Raw hides and skin of horses", 0.10, 0.09, "皮革"),
    ("4104", "4104.11", "4104.1100", "4104.1100.00", "皮革（牛），全粒面未剖层，湿态", "Leather of bovine, full grain, unsplit, wet state", 0.08, 0.13, "皮革"),
    ("4104", "4104.19", "4104.1900", "4104.1900.00", "皮革（牛），其他，湿态", "Leather of bovine, other, wet state", 0.08, 0.13, "皮革"),
    ("4104", "4104.41", "4104.4100", "4104.4100.00", "皮革（牛），全粒面未剖层，干态", "Leather of bovine, full grain, unsplit, dry state", 0.08, 0.13, "皮革"),
    ("4104", "4104.49", "4104.4900", "4104.4900.00", "皮革（牛），其他，干态", "Leather of bovine, other, dry state", 0.08, 0.13, "皮革"),
    ("4105", "4105.10", "4105.1000", "4105.1000.00", "绵羊皮革，已预鞣，未除毛", "Leather of sheep, pre-tanned, not depilated", 0.08, 0.13, "皮革"),
    ("4106", "4106.20", "4106.2000", "4106.2000.00", "山羊或小山羊皮革，已预鞣", "Leather of goat or kid, pre-tanned", 0.08, 0.13, "皮革"),
    ("4107", "4107.11", "4107.1100", "4107.1100.00", "皮革，已鞣制，半成品，整张，全粒面", "Leather, tanned, whole, full grain", 0.08, 0.13, "皮革"),
    # ============================================================
    # 九、纺织纤维与纱线 (5001-5212)
    # ============================================================
    ("5001", "5001.00", "5001.00.00", "5001.00.00.00", "桑蚕茧", "Silk-worm cocoons suitable for reeling", 0.06, 0.09, "棉麻"),
    ("5002", "5002.00", "5002.00.00", "5002.00.00.00", "生丝（未加捻）", "Raw silk (not thrown)", 0.06, 0.09, "棉麻"),
    ("5003", "5003.00", "5003.00.00", "5003.00.00.00", "废丝（不适合缫丝的蚕茧及废丝）", "Silk waste (including cocoons unsuitable for reeling)", 0.06, 0.09, "棉麻"),
    ("5004", "5004.00", "5004.00.00", "5004.00.00.00", "丝纱线，非供零售用", "Silk yarn (not for retail)", 0.06, 0.13, "棉麻"),
    ("5005", "5005.00", "5005.00.00", "5005.00.00.00", "绢丝纱线，非供零售用", "Yarn spun from silk waste (noil silk), not for retail", 0.06, 0.13, "棉麻"),
    ("5006", "5006.00", "5006.00.00", "5006.00.00.00", "丝纱线及绢丝纱线，供零售用", "Silk yarn and noil silk yarn, for retail", 0.06, 0.13, "棉麻"),
    ("5201", "5201.00", "5201.00.00", "5201.00.00.00", "棉花，未梳化，包括已梳棉花", "Cotton, not carded or combed", 0.01, 0.09, "棉麻"),
    ("5202", "5202.10", "5202.10.00", "5202.1000.00", "棉花废料，未梳", "Cotton waste, not carded or combed", 0.01, 0.09, "棉麻"),
    ("5203", "5203.00", "5203.00.00", "5203.00.00.00", "棉花，已梳化", "Cotton, carded or combed", 0.01, 0.09, "棉麻"),
    ("5204", "5204.11", "5204.1100", "5204.1100.00", "棉制缝纫线，非供零售用，棉≥85%", "Cotton sewing thread, not for retail, >=85% cotton", 0.05, 0.13, "棉麻"),
    ("5205", "5205.21", "5205.2100", "5205.2100.00", "棉纱线，非供零售用，精梳，单纱，棉≥85%", "Cotton yarn, not retail, combed, single, >=85% cotton", 0.05, 0.13, "棉麻"),
    ("5206", "5206.11", "5206.1100", "5206.1100.00", "棉纱线，非供零售用，粗梳，单纱，棉<85%", "Cotton yarn, not retail, carded, single, <85% cotton", 0.05, 0.13, "棉麻"),
    # 麻纤维 5301
    ("5301", "5301.10", "5301.10.00", "5301.1000.00", "亚麻，长纤维，未加工", "Flax, raw or retted, long fibres", 0.05, 0.09, "棉麻"),
    ("5301", "5301.21", "5301.2100", "5301.2100.00", "亚麻，短纤，加工但未纺纱", "Flax, processed but not spun; long fibres", 0.05, 0.09, "棉麻"),
    ("5301", "5301.29", "5301.2900", "5301.2900.00", "亚麻，短纤，其他加工", "Flax, hackled or otherwise processed", 0.05, 0.09, "棉麻"),
    ("5303", "5303.10", "5303.1000", "5303.1000.00", "黄麻及纺织用韧皮纤维，生的或水浸", "Jute and other textile bast fibres, raw or retted", 0.05, 0.09, "棉麻"),
    ("5303", "5303.90", "5303.9000", "5303.9000.00", "黄麻及其他韧皮纤维，已加工", "Jute and other textile bast fibres, processed", 0.05, 0.09, "棉麻"),
    ("5305", "5305.00", "5305.0000", "5305.0000.00", "椰壳纤维、苎麻及废麻纱线", "Coconut, abaca and other vegetable fibres", 0.05, 0.09, "棉麻"),
    # ============================================================
    # 十、原木与木材 (4403-4421)
    # ============================================================
    ("4401", "4401.10", "4401.10.00", "4401.1000.00", "薪柴（圆木段、块、枝、成捆），针叶木", "Fuel wood, in logs, in billets, in twigs, faggots, coniferous", 0.01, 0.13, "木材"),
    ("4401", "4401.22", "4401.22.00", "4401.2200.00", "薪柴，非针叶木", "Fuel wood, non-coniferous", 0.01, 0.13, "木材"),
    ("4403", "4403.11", "4403.1100", "4403.1100.00", "针叶原木，旋切用，刨切用，去皮", "Coniferous wood in the rough, veneer logs", 0.01, 0.13, "木材"),
    ("4403", "4403.41", "4403.4100", "4403.4100.00", "热带红木原木（深红色），大果西非栋等", "Tropical wood logs, dark red meranti, light red meranti", 0.01, 0.13, "木材"),
    ("4403", "4403.49", "4403.4900", "4403.4900.00", "其他热带木原木", "Other tropical wood logs", 0.01, 0.13, "木材"),
    ("4403", "4403.91", "4403.9100", "4403.9100.00", "栎木（橡木）原木", "Oak wood in the rough", 0.01, 0.13, "木材"),
    ("4403", "4403.93", "4403.9300", "4403.9300.00", "水青冈木（榉木）原木", "Beech wood in the rough", 0.01, 0.13, "木材"),
    ("4403", "4403.94", "4403.9400", "4403.9400.00", "水青冈木（榉木）原木，带树皮", "Beech wood in the rough, bark-on", 0.01, 0.13, "木材"),
    ("4403", "4403.95", "4403.9500", "4403.9500.00", "杨木原木", "Poplar wood in the rough", 0.01, 0.13, "木材"),
    ("4403", "4403.96", "4403.9600", "4403.9600.00", "杨木原木，带树皮", "Poplar wood in the rough, bark-on", 0.01, 0.13, "木材"),
    ("4403", "4403.97", "4403.9700", "4403.9700.00", "辐射松原木", "Radiata pine wood in the rough", 0.01, 0.13, "木材"),
    ("4404", "4404.10", "4404.1000", "4404.1000.00", "针叶木劈木杆", "Coniferous hoopwood", 0.01, 0.13, "木材"),
    ("4407", "4407.10", "4407.1000", "4407.1000.00", "经纵锯或纵切的木材，针叶，厚度>6mm", "Wood sawn or chipped lengthwise, coniferous, >6mm", 0.01, 0.13, "木材"),
    ("4407", "4407.91", "4407.9100", "4407.9100.00", "经纵锯或纵切的木材，栎木（橡木），厚度>6mm", "Wood sawn or chipped lengthwise, oak, >6mm", 0.01, 0.13, "木材"),
    ("4407", "4407.92", "4407.9200", "4407.9200.00", "经纵锯或纵切的木材，水青冈木，厚度>6mm", "Wood sawn or chipped lengthwise, beech, >6mm", 0.01, 0.13, "木材"),
    ("4407", "4407.93", "4407.9300", "4407.9300.00", "经纵锯或纵切的木材，枫木，厚度>6mm", "Wood sawn or chipped lengthwise, maple, >6mm", 0.01, 0.13, "木材"),
    ("4407", "4407.94", "4407.9400", "4407.9400.00", "经纵锯或纵切的木材，樱桃木，厚度>6mm", "Wood sawn or chipped lengthwise, cherry, >6mm", 0.01, 0.13, "木材"),
    ("4408", "4408.10", "4408.1000", "4408.1000.00", "旋切薄木（单板），针叶木，厚度≤6mm", "Veneer sheets, coniferous, <=6mm", 0.04, 0.13, "木材"),
    ("4409", "4409.10", "4409.1000", "4409.1000.00", "任一侧面与木纹平行的木材，针叶，未加工", "Coniferous wood continuously shaped along any edges", 0.04, 0.13, "木材"),
    ("4410", "4410.11", "4410.1100", "4410.1100.00", "木制碎料板（刨花板），未饰面", "Particle board, unworked or not further worked", 0.07, 0.13, "木材"),
    ("4410", "4410.12", "4410.1200", "4410.1200.00", "定向刨花板（OSB板）", "Oriented strand board (OSB)", 0.07, 0.13, "木材"),
    ("4411", "4411.12", "4411.1200", "4411.1200.00", "中密度纤维板（MDF），厚度≤5mm", "Fibreboard of wood, MDF, <=5mm", 0.07, 0.13, "木材"),
    ("4411", "4411.13", "4411.1300", "4411.1300.00", "中密度纤维板（MDF），5mm<厚度≤9mm", "Fibreboard of wood, MDF, 5mm<thickness<=9mm", 0.07, 0.13, "木材"),
    ("4411", "4411.14", "4411.1400", "4411.1400.00", "中密度纤维板（MDF），厚度>9mm", "Fibreboard of wood, MDF, >9mm", 0.07, 0.13, "木材"),
    ("4412", "4412.10", "4412.1000", "4412.1000.00", "胶合板，竹制，至少有一层热带木", "Plywood, bamboo, with at least one layer of tropical wood", 0.08, 0.13, "木材"),
    ("4412", "4412.31", "4412.3100", "4412.3100.00", "胶合板，至少有一层热带木，每层厚≤6mm", "Plywood, with at least one tropical wood layer, each <=6mm", 0.08, 0.13, "木材"),
    ("4412", "4412.33", "4412.3300", "4412.3300.00", "胶合板，其他，仅有针叶木表板", "Plywood, other, with only coniferous outer veneers", 0.08, 0.13, "木材"),
    ("4412", "4412.34", "4412.3400", "4412.3400.00", "胶合板，其他，非针叶木表板", "Plywood, other, non-coniferous outer veneers", 0.08, 0.13, "木材"),
    # ============================================================
    # 十一、食品与农产品
    # ============================================================
    # 水果 0801-0814
    ("0803", "0803.10", "0803.1000", "0803.1000.00", "鲜或干大蕉", "Plantains, fresh or dried", 0.10, 0.09, "水果"),
    ("0804", "0804.10", "0804.1000", "0804.1000.00", "鲜椰枣", "Dates, fresh", 0.10, 0.09, "水果"),
    ("0804", "0804.20", "0804.2000", "0804.2000.00", "无花果，鲜或干", "Figs, fresh or dried", 0.10, 0.09, "水果"),
    ("0804", "0804.30", "0804.3000", "0804.3000.00", "鲜或干菠萝", "Pineapples, fresh or dried", 0.10, 0.09, "水果"),
    ("0804", "0804.40", "0804.4000", "0804.4000.00", "鲜或干鳄梨（牛油果）", "Avocados, fresh or dried", 0.10, 0.09, "水果"),
    ("0804", "0804.50", "0804.5000", "0804.5000.00", "鲜或干番石榴、芒果及山竹", "Guavas, mangoes and mangosteens, fresh or dried", 0.10, 0.09, "水果"),
    ("0805", "0805.10", "0805.1000", "0805.1000.00", "鲜或干橙", "Oranges, fresh or dried", 0.10, 0.09, "水果"),
    ("0805", "0805.20", "0805.2000", "0805.2000.00", "鲜或干柑橘（包括杂交柑橘）", "Mandarins, clementines and similar citrus hybrids, fresh or dried", 0.10, 0.09, "水果"),
    ("0805", "0805.40", "0805.4000", "0805.4000.00", "鲜或干葡萄柚，包括柚子", "Grapefruit, including pomelos, fresh or dried", 0.10, 0.09, "水果"),
    ("0805", "0805.50", "0805.5000", "0805.5000.00", "鲜或干柠檬及酸橙", "Lemons and limes, fresh or dried", 0.10, 0.09, "水果"),
    ("0806", "0806.10", "0806.1000", "0806.1000.00", "鲜葡萄", "Grapes, fresh", 0.10, 0.09, "水果"),
    ("0806", "0806.20", "0806.2000", "0806.2000.00", "干葡萄（葡萄干）", "Grapes, dried", 0.10, 0.09, "水果"),
    ("0808", "0808.10", "0808.1000", "0808.1000.00", "鲜苹果", "Apples, fresh", 0.10, 0.09, "水果"),
    ("0808", "0808.30", "0808.3000", "0808.3000.00", "鲜梨及榅桲", "Pears and quinces, fresh", 0.10, 0.09, "水果"),
    ("0809", "0809.10", "0809.1000", "0809.1000.00", "鲜杏", "Apricots, fresh", 0.10, 0.09, "水果"),
    ("0809", "0809.20", "0809.2000", "0809.2000.00", "鲜樱桃", "Cherries, fresh", 0.10, 0.09, "水果"),
    ("0809", "0809.30", "0809.3000", "0809.3000.00", "鲜桃，包括鲜油桃", "Peaches, including nectarines, fresh", 0.10, 0.09, "水果"),
    ("0809", "0809.40", "0809.4000", "0809.4000.00", "鲜李子及黑刺李", "Plums and sloes, fresh", 0.10, 0.09, "水果"),
    ("0810", "0810.10", "0810.1000", "0810.1000.00", "鲜草莓", "Strawberries, fresh", 00.10, 0.09, "水果"),
    ("0810", "0810.20", "0810.2000", "0810.2000.00", "鲜木莓、黑莓、桑葚及罗甘莓", "Raspberries, blackberries, mulberries and loganberries, fresh", 0.10, 0.09, "水果"),
    ("0810", "0810.30", "0810.3000", "0810.3000.00", "鲜黑醋栗及红醋栗", "Blackcurrants and redcurrants, fresh", 0.10, 0.09, "水果"),
    ("0810", "0810.40", "0810.4000", "0810.4000.00", "鲜蔓越莓（越橘）及杜鹄莓", "Cranberries, bilberries and other fruits of genus Vaccinium, fresh", 0.10, 0.09, "水果"),
    ("0810", "0810.50", "0810.5000", "0810.5000.00", "鲜猕猴桃", "Kiwifruit, fresh", 0.10, 0.09, "水果"),
    ("0810", "0810.60", "0810.6000", "0810.6000.00", "鲜榴莲", "Durians, fresh", 0.10, 0.09, "水果"),
    ("0810", "0810.70", "0810.7000", "0810.7000.00", "鲜柿子", "Persimmons, fresh", 0.10, 0.09, "水果"),
    ("0810", "0810.90", "0810.9000", "0810.9000.00", "其他鲜果", "Other fresh fruit", 0.10, 0.09, "水果"),
    # 蔬菜 0701-0714
    ("0701", "0701.90", "0701.9000", "0701.9000.00", "鲜马铃薯，种用除外", "Potatoes, fresh or chilled, not for planting", 0.13, 0.09, "蔬菜"),
    ("0703", "0703.10", "0703.1000", "0703.1000.00", "鲜或冷藏洋葱及青葱", "Onions and shallots, fresh or chilled", 0.13, 0.09, "蔬菜"),
    ("0703", "0703.20", "0703.2000", "0703.2000.00", "鲜或冷藏大蒜", "Garlic, fresh or chilled", 0.13, 0.09, "蔬菜"),
    ("0703", "0703.90", "0703.9000", "0703.9000.00", "鲜或冷藏葱及其他鳞茎类蔬菜", "Leeks and other alliaceous vegetables, fresh or chilled", 0.13, 0.09, "蔬菜"),
    ("0704", "0704.10", "0704.1000", "0704.1000.00", "鲜或冷藏菜花及硬花甘蓝", "Cauliflowers and headed broccoli, fresh or chilled", 0.13, 0.09, "蔬菜"),
    ("0704", "0704.90", "0704.9000", "0704.9000.00", "其他鲜或冷藏食用芥菜类蔬菜", "Other edible brassicas, fresh or chilled", 0.13, 0.09, "蔬菜"),
    ("0705", "0705.11", "0705.1100", "0705.1100.00", "鲜或冷藏结球莴苣（卷心莴苣）", "Cabbage lettuce (head lettuce), fresh or chilled", 0.13, 0.09, "蔬菜"),
    ("0706", "0706.10", "0706.1000", "0706.1000.00", "鲜或冷藏胡萝卜及萝卜", "Carrots and turnips, fresh or chilled", 0.13, 0.09, "蔬菜"),
    ("0707", "0707.00", "0707.0000", "0707.0000.00", "鲜或冷藏黄瓜及小黄瓜", "Cucumbers and gherkins, fresh or chilled", 0.13, 0.09, "蔬菜"),
    ("0708", "0708.10", "0708.1000", "0708.1000.00", "鲜或冷藏豌豆", "Peas (Pisum sativum), fresh or chilled", 0.13, 0.09, "蔬菜"),
    ("0708", "0708.20", "0708.2000", "0708.2000.00", "鲜或冷藏虹豆及菜豆", "Beans (Vigna spp., Phaseolus spp.), fresh or chilled", 0.13, 0.09, "蔬菜"),
    ("0709", "0709.20", "0709.2000", "0709.2000.00", "鲜或冷藏芦笋", "Asparagus, fresh or chilled", 0.13, 0.09, "蔬菜"),
    ("0709", "0709.30", "0709.3000", "0709.3000.00", "鲜或冷藏茄子", "Aubergines (eggplants), fresh or chilled", 0.13, 0.09, "蔬菜"),
    ("0709", "0709.40", "0709.4000", "0709.4000.00", "鲜或冷藏芹菜（块根芹除外）", "Celery, except celeriac, fresh or chilled", 0.13, 0.09, "蔬菜"),
    ("0709", "0709.51", "0709.5100", "0709.5100.00", "鲜或冷藏香菇（新鲜草菇）", "Mushrooms of the genus Agaricus (fresh meadow mushrooms), fresh or chilled", 0.13, 0.09, "蔬菜"),
    ("0709", "0709.59", "0709.5900", "0709.5900.00", "其他鲜或冷藏蘑菇及块菌", "Other mushrooms and truffles, fresh or chilled", 0.13, 0.09, "蔬菜"),
    ("0709", "0709.60", "0709.6000", "0709.6000.00", "鲜或冷藏辣椒属（包括甜椒）", "Fruits of genus Capsicum or Pimenta, fresh or chilled", 0.13, 0.09, "蔬菜"),
    ("0709", "0709.70", "0709.7000", "0709.7000.00", "鲜或冷藏菠菜及甜菜叶（恭菜叶）", "Spinach, beet greens (chard), fresh or chilled", 0.13, 0.09, "蔬菜"),
    ("0709", "0709.90", "0709.9000", "0709.9000.00", "其他鲜或冷藏食用植物", "Other edible plants, fresh or chilled", 0.13, 0.09, "蔬菜"),
    # 水产 0301-1605
    ("0301", "0301.10", "0301.1000", "0301.1000.00", "活观赏鱼", "Ornamental fish, live", 0.12, 0.09, "水产"),
    ("0302", "0302.11", "0302.1100", "0302.1100.00", "鲜或冷藏鳟鱼（养殖）", "Trout (Salmo trutta etc.), fresh or chilled, farmed", 0.12, 0.09, "水产"),
    ("0302", "0302.12", "0302.1200", "0302.1200.00", "鲜或冷藏大西洋及多瑙白鲑", "Atlantic and Danube salmon, fresh or chilled", 0.12, 0.09, "水产"),
    ("0302", "0302.19", "0302.1900", "0302.1900.00", "其他鲜或冷藏鲑鱼", "Other salmon, fresh or chilled", 0.12, 0.09, "水产"),
    ("0303", "0303.11", "0303.1100", "0303.1100.00", "冻大西洋鲑鱼", "Pacific salmon, frozen", 0.10, 0.09, "水产"),
    ("0303", "0303.19", "0303.1900", "0303.1900.00", "其他冻鲑鱼", "Other salmon, frozen", 0.10, 0.09, "水产"),
    ("0303", "0303.21", "0303.2100", "0303.2100.00", "冻鳟鱼", "Trout, frozen", 0.12, 0.09, "水产"),
    ("0303", "0303.31", "0303.3100", "0303.3100.00", "冻大菱鲆（多宝鱼）", "Atlantic halibut, frozen", 0.12, 0.09, "水产"),
    ("0303", "0303.32", "0303.3200", "0303.3200.00", "冻鲽鱼", "Plaice, frozen", 0.12, 0.09, "水产"),
    ("0303", "0303.41", "0303.4100", "0303.4100.00", "冻长鳍金枪鱼（鲔）", "Albacore or longfinned tunas, frozen", 0.12, 0.09, "水产"),
    ("0303", "0303.42", "0303.4200", "0303.4200.00", "冻黄鳍金枪鱼", "Yellowfin tunas, frozen", 0.12, 0.09, "水产"),
    ("0303", "0303.43", "0303.4300", "0303.4300.00", "冻鲣鱼（正鲣）", "Skipjack tuna (stripe-bellied bonito), frozen", 0.12, 0.09, "水产"),
    ("0303", "0303.44", "0303.4400", "0303.4400.00", "冻大眼金枪鱼", "Bigeye tunas, frozen", 0.12, 0.09, "水产"),
    ("0303", "0303.45", "0303.4500", "0303.4500.00", "冻大西洋蓝鳍金枪鱼", "Atlantic and Pacific bluefin tunas, frozen", 0.12, 0.09, "水产"),
    ("0303", "0303.49", "0303.4900", "0303.4900.00", "其他冻金枪鱼", "Other tunas, frozen", 0.12, 0.09, "水产"),
    ("0303", "0303.51", "0303.5100", "0303.5100.00", "冻北大西洋及南极鳕鱼", "Cod (Gadus morhua etc.), frozen", 0.10, 0.09, "水产"),
    ("0303", "0303.61", "0303.6100", "0303.6100.00", "冻马舌鲽（大比目鱼）", "Greater lanternfish, frozen", 0.12, 0.09, "水产"),
    ("0303", "0303.71", "0303.7100", "0303.7100.00", "冻凤尾鱼（鳀鱼）", "Anchovies (Engraulis spp.), frozen", 0.12, 0.09, "水产"),
    ("0303", "0303.74", "0303.7400", "0303.7400.00", "冻鲭鱼（花鳛）", "Mackerel, frozen", 0.12, 0.09, "水产"),
    ("0303", "0303.75", "0303.7500", "0303.7500.00", "冻黑线鳕（青鳕）", "Haddock, frozen", 0.12, 0.09, "水产"),
    ("0303", "0303.76", "0303.7600", "0303.7600.00", "冻狗鱼及鳕鱼", "Coalfish, frozen", 0.12, 0.09, "水产"),
    ("0303", "0303.77", "0303.7700", "0303.7700.00", "冻绿青鳕", "Alaska Pollack, frozen", 0.12, 0.09, "水产"),
    ("0303", "0303.78", "0303.7800", "0303.7800.00", "冻蓝鲭（青花鱼）", "Blue whiting, frozen", 0.12, 0.09, "水产"),
    ("0303", "0303.79", "0303.7900", "0303.7900.00", "其他冻鱼", "Other fish, frozen", 0.12, 0.09, "水产"),
    ("0303", "0303.80", "0303.8000", "0303.8000.00", "冻鱼肝、鱼籽及鱼精", "Fish livers, roes and milt, frozen", 0.12, 0.09, "水产"),
    ("0304", "0304.11", "0304.1100", "0304.1100.00", "鲜或冷藏剑鱼片及鱼肉", "Swordfish fillets and meat, fresh or chilled", 0.12, 0.09, "水产"),
    ("0304", "0304.12", "0304.1200", "0304.1200.00", "鲜或冷藏其他鱼片及鱼肉", "Other fish fillets and meat, fresh or chilled", 0.12, 0.09, "水产"),
    ("0304", "0304.21", "0304.2100", "0304.2100.00", "冻剑鱼片及鱼肉", "Swordfish fillets and meat, frozen", 0.12, 0.09, "水产"),
    ("0304", "0304.22", "0304.2200", "0304.2200.00", "冻其他鱼片及鱼肉", "Other fish fillets and meat, frozen", 0.12, 0.09, "水产"),
    ("0305", "0305.10", "0305.1000", "0305.1000.00", "供人食用的鱼粉及团粒", "Flours, meals and pellets of fish, fit for human consumption", 0.10, 0.09, "水产"),
    ("0305", "0305.20", "0305.2000", "0305.2000.00", "干、熏、盐腌或盐渍鱼肝、鱼籽及鱼精", "Fish livers, roes and milt, dried, smoked, salted or in brine", 0.10, 0.09, "水产"),
    ("0305", "0305.30", "0305.3000", "0305.3000.00", "干或盐腌鱼片（熏鱼除外）", "Fish fillets, dried, salted or in brine, not smoked", 0.10, 0.09, "水产"),
    ("0305", "0305.41", "0305.4100", "0305.4100.00", "熏大西洋及多瑙白鲑鱼，包括鱼片", "Atlantic salmon and Danube salmon, smoked, including fillets", 0.12, 0.09, "水产"),
    ("0305", "0305.42", "0305.4200", "0305.4200.00", "熏鳀鱼（鳀科）", "Herrings (Clupea harengus, Clupea pallasii), smoked", 0.12, 0.09, "水产"),
    ("0305", "0305.49", "0305.4900", "0305.4900.00", "其他熏鱼", "Other fish, smoked", 0.12, 0.09, "水产"),
    ("0306", "0306.11", "0306.1100", "0306.1100.00", "冻龙虾（海螯虾）", "Rock lobster and other sea crawfish, frozen", 0.07, 0.09, "水产"),
    ("0306", "0306.12", "0306.1200", "0306.1200.00", "冻大螯虾", "Lobsters (Homarus spp.), frozen", 0.07, 0.09, "水产"),
    ("0306", "0306.14", "0306.1400", "0306.1400.00", "冻蟹", "Crabs, frozen", 0.07, 0.09, "水产"),
    ("0306", "0306.15", "0306.1500", "0306.1500.00", "冻挪威海螯虾", "Norway lobsters, frozen", 0.07, 0.09, "水产"),
    ("0306", "0306.16", "0306.1600", "0306.1600.00", "冻淡水螯虾", "Freshwater crawfish, frozen", 0.07, 0.09, "水产"),
    ("0306", "0306.17", "0306.1700", "0306.1700.00", "冻其他虾及对虾", "Other shrimps and prawns, frozen", 0.05, 0.09, "水产"),
    ("0306", "0306.19", "0306.1900", "0306.1900.00", "其他冻甲壳动物", "Other crustaceans, frozen", 0.07, 0.09, "水产"),
    ("0307", "0307.10", "0307.1000", "0307.1000.00", "鲜或冷藏牡蛎（生蚝）", "Oysters, fresh or chilled", 0.07, 0.09, "水产"),
    ("0307", "0307.21", "0307.2100", "0307.2100.00", "鲜或冷藏扇贝（扇贝属），包括海扇贝", "Scallops, fresh or chilled", 0.07, 0.09, "水产"),
    ("0307", "0307.29", "0307.2900", "0307.2900.00", "冻或干扇贝，包括海扇贝", "Scallops, frozen, dried or in brine", 0.07, 0.09, "水产"),
    ("0307", "0307.31", "0307.3100", "0307.3100.00", "鲜或冷藏蛤蚌（帘蛤属）", "Clams ( Carpet shell, Ruditapes), fresh or chilled", 0.07, 0.09, "水产"),
    ("0307", "0307.41", "0307.4100", "0307.4100.00", "鲜或冷藏墨鱼及章鱼", "Cuttle fish and squid, fresh or chilled", 0.07, 0.09, "水产"),
    ("0307", "0307.51", "0307.5100", "0307.5100.00", "鲜或冷藏鲍鱼", "Abalone, fresh or chilled", 0.07, 0.09, "水产"),
    ("0308", "0308.11", "0308.1100", "0308.1100.00", "鲜或冷藏海参（海瓜参科）", "Sea cucumbers (Stichopus japonicus etc.), fresh or chilled", 0.07, 0.09, "水产"),
    ("0308", "0308.19", "0308.1900", "0308.1900.00", "干、盐腌或盐渍海参", "Sea cucumbers, dried, salted or in brine", 0.07, 0.09, "水产"),
    ("1604", "1604.11", "1604.1100", "1604.1100.00", "制作或保藏的整条或切块鲑鱼", "Prepared or preserved salmon, whole or in pieces", 0.05, 0.09, "水产"),
    ("1604", "1604.12", "1604.1200", "1604.1200.00", "制作或保藏的整条或切块鲱鱼", "Prepared or preserved herring, whole or in pieces", 0.05, 0.09, "水产"),
    ("1604", "1604.13", "1604.1300", "1604.1300.00", "制作或保藏的整条或切块沙丁鱼、黍鲱", "Prepared or preserved sardines, brisling and sprats", 0.05, 0.09, "水产"),
    ("1604", "1604.14", "1604.1400", "1604.1400.00", "制作或保藏的金枪鱼、鲣鱼及狐鲣", "Prepared or preserved tuna, skipjack and bonito", 0.05, 0.09, "水产"),
    ("1604", "1604.15", "1604.1500", "1604.1500.00", "制作或保藏的鲭鱼", "Prepared or preserved mackerel", 0.05, 0.09, "水产"),
    ("1604", "1604.16", "1604.1600", "1604.1600.00", "制作或保藏的鳀鱼", "Prepared or preserved anchovies", 0.05, 0.09, "水产"),
    ("1604", "1604.20", "1604.2000", "1604.2000.00", "其他制作或保藏的鱼", "Other prepared or preserved fish", 0.05, 0.09, "水产"),
    ("1605", "1605.10", "1605.1000", "1605.1000.00", "制作或保藏的蟹", "Crab, prepared or preserved", 0.05, 0.09, "水产"),
    ("1605", "1605.21", "1605.2100", "1605.2100.00", "制作或保藏的非醋保藏虾及对虾", "Shrimps and prawns, not in airtight containers", 0.05, 0.09, "水产"),
    ("1605", "1605.29", "1605.2900", "1605.2900.00", "其他制作或保藏的虾及对虾", "Other shrimps and prawns, prepared or preserved", 0.05, 0.09, "水产"),
    ("1605", "1605.30", "1605.3000", "1605.3000.00", "制作或保藏的龙虾", "Lobster, prepared or preserved", 0.05, 0.09, "水产"),
    ("2301", "2301.10", "2301.1000", "2301.1000.00", "肉渣粉及不适合供人食用的猪肉渣", "Flours, meals and pellets of meat or meat offal, unfit for human consumption", 0.05, 0.09, "水产"),
    ("2301", "2301.20", "2301.2000", "2301.2000.00", "鱼粉及团粒（非供人食用）", "Flours, meals and pellets of fish or crustaceans, unfit for human consumption", 0.05, 0.09, "水产"),
    # 粮食 1001-1104
    ("1001", "1001.10", "1001.1000", "1001.1000.00", "硬粒小麦，种用", "Durum wheat, for sowing", 0.03, 0.09, "粮食"),
    ("1001", "1001.90", "1001.9000", "1001.9000.00", "其他小麦及混合麦，种用除外", "Other wheat and meslin, not for sowing", 0.03, 0.09, "粮食"),
    ("1003", "1003.00", "1003.0000", "1003.0000.00", "大麦，种用除外", "Barley, not for sowing", 0.03, 0.09, "粮食"),
    ("1004", "1004.00", "1004.0000", "1004.0000.00", "燕麦，种用除外", "Oats, not for sowing", 0.03, 0.09, "粮食"),
    ("1005", "1005.10", "1005.1000", "1005.1000.00", "玉米（玉蜀黍），种用", "Maize (corn), for sowing", 0.03, 0.09, "粮食"),
    ("1005", "1005.90", "1005.9000", "1005.9000.00", "玉米（玉蜀黍），种用除外", "Maize (corn), not for sowing", 0.03, 0.09, "粮食"),
    ("1006", "1006.10", "1006.1000", "1006.1000.00", "稻谷，种用除外", "Rice in the husk (paddy or rough)", 0.03, 0.09, "粮食"),
    ("1006", "1006.20", "1006.2000", "1006.2000.00", "糙米（稻谷已剥壳）", "Husked (brown) rice", 0.03, 0.09, "粮食"),
    ("1006", "1006.30", "1006.3000", "1006.3000.00", "精米（白米），不论是否磨光或上光", "Semi-milled or wholly milled rice, whether or not polished or glazed", 0.03, 0.09, "粮食"),
    ("1007", "1007.00", "1007.0000", "1007.0000.00", "食用高粱（蜀黍），种用除外", "Grain sorghum, for human consumption, not for sowing", 0.03, 0.09, "粮食"),
    ("1008", "1008.10", "1008.1000", "1008.1000.00", "荞麦，种用除外", "Buckwheat, not for sowing", 0.03, 0.09, "粮食"),
    ("1008", "1008.20", "1008.2000", "1008.2000.00", "谷子（粟），种用除外", "Millet, not for sowing", 0.03, 0.09, "粮食"),
    ("1008", "1008.30", "1008.3000", "1008.3000.00", "加那利草籽，种用除外", "Canary seeds, not for sowing", 0.03, 0.09, "粮食"),
    ("1008", "1008.90", "1008.9000", "1008.9000.00", "其他谷物，种用除外", "Other cereals, not for sowing", 0.03, 0.09, "粮食"),
    # 面粉及淀粉制品 1101-1109
    ("1101", "1101.00", "1101.0000", "1101.0000.00", "小麦或混合麦的细粉", "Wheat or meslin flour", 0.06, 0.13, "粮食"),
    ("1102", "1102.20", "1102.2000", "1102.2000.00", "玉米细粉及粗粉", "Maize (corn) flour and meal", 0.06, 0.13, "粮食"),
    ("1103", "1103.11", "1103.1100", "1103.1100.00", "小麦粗粒及粗粉", "Groats and meal of wheat", 0.06, 0.13, "粮食"),
    ("1104", "1104.12", "1104.1200", "1104.1200.00", "经碾轧或制成片状的燕麦", "Rolled or flaked oats", 0.06, 0.13, "粮食"),
    # 烟草 2401-2404
    ("2401", "2401.10", "2401.1000", "2401.1000.00", "未去梗的烟草（烤烟型）", "Tobacco, not stemmed/stripped, flue-cured Virginia type", 0.10, 0.09, "烟草"),
    ("2401", "2401.20", "2401.2000", "2401.2000.00", "部分或全部去梗的烟草（烤烟）", "Tobacco, partly or wholly stemmed/stripped, flue-cured", 0.10, 0.09, "烟草"),
    ("2401", "2401.30", "2401.3000", "2401.3000.00", "烟草废料", "Tobacco refuse", 0.10, 0.09, "烟草"),
    ("2402", "2402.10", "2402.1000", "2402.1000.00", "烟草或烟草代用品制成的雪茄", "Cigars, cheroots and cigarillos, containing tobacco", 0.10, 0.13, "烟草"),
    ("2402", "2402.20", "2402.2000", "2402.2000.00", "烟草或烟草代用品制成的卷烟", "Cigarettes containing tobacco", 0.10, 0.13, "烟草"),
    ("2402", "2402.90", "2402.9000", "2402.9000.00", "其他烟草制品及烟草代用品", "Other tobacco products and substitutes", 0.10, 0.13, "烟草"),
    # 咖啡提取物/浓缩物 2101
    ("2101", "2101.11", "2101.1100", "2101.1100.00", "咖啡浓缩精汁，未浸除咖啡碱", "Coffee extracts, essences and concentrates, not decaffeinated", 0.12, 0.13, "咖啡"),
    ("2101", "2101.12", "2101.1200", "2101.1200.00", "咖啡浓缩精汁，已浸除咖啡碱", "Coffee extracts, essences and concentrates, decaffeinated", 0.12, 0.13, "咖啡"),
    ("2101", "2101.20", "2101.2000", "2101.2000.00", "茶、咖啡浓缩精汁及以其为基本成分的制品", "Extracts, essences and concentrates of tea or mate", 0.12, 0.13, "咖啡"),
    ("2101", "2101.30", "2101.3000", "2101.3000.00", "烘焙代咖啡及其浓缩提取物", "Roasted coffee substitutes and extracts thereof", 0.12, 0.13, "咖啡"),
    # ============================================================
    # 十二、塑料原料 (3901-3926)
    # ============================================================
    ("3901", "3901.10", "3901.1000", "3901.1000.00", "初级形态的聚乙烯，比重<0.94", "Polyethylene, primary forms, density <0.94", 0.065, 0.13, "塑料"),
    ("3901", "3901.20", "3901.2000", "3901.2000.00", "初级形态的聚乙烯，比重≥0.94", "Polyethylene, primary forms, density >=0.94", 0.065, 0.13, "塑料"),
    ("3901", "3901.30", "3901.3000", "3901.3000.00", "初级形态的乙烯-乙酸乙烯酯共聚物", "Ethylene-vinyl acetate copolymers, primary forms", 0.065, 0.13, "塑料"),
    ("3901", "3901.40", "3901.4000", "3901.4000.00", "初级形态的乙烯-丙烯共聚物", "Ethylene-propylene copolymers, primary forms", 0.065, 0.13, "塑料"),
    ("3902", "3902.10", "3902.1000", "3902.1000.00", "初级形态的聚丙烯", "Polypropylene, primary forms", 0.065, 0.13, "塑料"),
    ("3902", "3902.20", "3902.2000", "3902.2000.00", "初级形态的聚异丁烯", "Polyisobutylene, primary forms", 0.065, 0.13, "塑料"),
    ("3902", "3902.30", "3902.3000", "3902.3000.00", "初级形态的丙烯共聚物", "Propylene copolymers, primary forms", 0.065, 0.13, "塑料"),
    ("3903", "3903.11", "3903.1100", "3903.1100.00", "初级形态的聚苯乙烯，可发性", "Polystyrene, expandable (EPS), primary forms", 0.065, 0.13, "塑料"),
    ("3903", "3903.19", "3903.1900", "3903.1900.00", "初级形态的聚苯乙烯，其他", "Polystyrene, other, primary forms", 0.065, 0.13, "塑料"),
    ("3904", "3904.10", "3904.1000", "3904.1000.00", "初级形态的聚氯乙烯，未掺其他物质", "Polyvinyl chloride, not mixed with other substances (PVC)", 0.065, 0.13, "塑料"),
    ("3904", "3904.21", "3904.2100", "3904.2100.00", "初级形态的聚氯乙烯，已塑化", "Polyvinyl chloride, plasticized", 0.065, 0.13, "塑料"),
    ("3904", "3904.22", "3904.2200", "3904.2200.00", "初级形态的聚氯乙烯，未塑化", "Polyvinyl chloride, non-plasticized", 0.065, 0.13, "塑料"),
    ("3905", "3905.12", "3905.1200", "3905.1200.00", "聚乙酸乙烯酯水分散体", "Polyvinyl acetate, in aqueous dispersion", 0.065, 0.13, "塑料"),
    ("3906", "3906.10", "3906.1000", "3906.1000.00", "初级形态的聚甲基丙烯酸甲酯", "Polymethyl methacrylate, primary forms", 0.065, 0.13, "塑料"),
    ("3907", "3907.10", "3907.1000", "3907.1000.00", "初级形态的聚甲醛（POM）", "Polyoxymethylene, primary forms", 0.065, 0.13, "塑料"),
    ("3907", "3907.20", "3907.2000", "3907.2000.00", "初级形态的聚醚（聚甲醛除外）", "Polyethers, primary forms (excl. polyoxymethylene)", 0.065, 0.13, "塑料"),
    ("3907", "3907.30", "3907.3000", "3907.3000.00", "初级形态的环氧树脂", "Epoxide resins, primary forms", 0.065, 0.13, "塑料"),
    ("3907", "3907.40", "3907.4000", "3907.4000.00", "初级形态的聚碳酸酯", "Polycarbonates, primary forms", 0.065, 0.13, "塑料"),
    ("3907", "3907.50", "3907.5000", "3907.5000.00", "初级形态的不饱和聚酯树脂", "Unsaturated polyesters, primary forms", 0.065, 0.13, "塑料"),
    ("3908", "3908.10", "3908.1000", "3908.1000.00", "初级形态的聚酰胺-6、-11、-12、-6,6等", "Polyamides-6, -11, -12, -6,6 etc., primary forms", 0.065, 0.13, "塑料"),
    ("3909", "3909.10", "3909.1000", "3909.1000.00", "初级形态的氨基树脂", "Amino-resins, primary forms", 0.065, 0.13, "塑料"),
    ("3910", "3910.00", "3910.0000", "3910.0000.00", "初级形态的聚硅氧烷（硅树脂）", "Silicones in primary forms", 0.065, 0.13, "塑料"),
    ("3911", "3911.10", "3911.1000", "3911.1000.00", "初级形态的石油树脂、苯并呋喃-茚树脂等", "Petroleum resins, coumarone-indene resins, primary forms", 0.065, 0.13, "塑料"),
    ("3912", "3912.11", "3912.1100", "3912.1100.00", "初级形态的醋酸纤维素，未塑化", "Cellulose acetates, non-plasticized, primary forms", 0.065, 0.13, "塑料"),
    ("3912", "3912.12", "3912.1200", "3912.1200.00", "初级形态的醋酸纤维素，已塑化", "Cellulose acetates, plasticized, primary forms", 0.065, 0.13, "塑料"),
    ("3920", "3920.10", "3920.1000", "3920.1000.00", "其他非泡沫塑料薄膜，乙烯聚合物，厚<0.5mm", "Films of ethylene polymers, non-cellular, <0.5mm", 0.06, 0.13, "塑料"),
    ("3920", "3920.20", "3920.2000", "3920.2000.00", "其他非泡沫塑料薄膜，丙烯聚合物，厚<0.5mm", "Films of propylene polymers, non-cellular, <0.5mm", 0.06, 0.13, "塑料"),
    ("3920", "3920.30", "3920.3000", "3920.3000.00", "其他非泡沫塑料薄膜，苯乙烯聚合物", "Films of styrene polymers, non-cellular", 0.06, 0.13, "塑料"),
    ("3921", "3921.11", "3921.1100", "3921.1100.00", "其他塑料薄膜，泡沫苯乙烯聚合物", "Other plates, sheets, film of styrene polymers, cellular", 0.06, 0.13, "塑料"),
    ("3921", "3921.12", "3921.1200", "3921.1200.00", "其他塑料薄膜，泡沫氯乙烯聚合物", "Other plates, sheets, film of PVC, cellular", 0.06, 0.13, "塑料"),
    ("3923", "3923.10", "3923.1000", "3923.1000.00", "塑料包装容器，盒及类似品，供运输或包装用", "Boxes, cases, crates and similar, of plastics", 0.06, 0.13, "塑料"),
    ("3926", "3926.10", "3926.1000", "3926.1000.00", "塑料办公室或学校用品", "Office or school supplies, of plastics", 0.06, 0.13, "塑料"),
    # ============================================================
    # 十三、矿产燃料 (2701-2716)
    # ============================================================
    ("2701", "2701.11", "2701.1100", "2701.1100.00", "无烟煤（煤，炼焦煤），粉状或非粉状", "Anthracite, whether or not pulverised", 0.03, 0.13, "矿产"),
    ("2701", "2701.12", "2701.1200", "2701.1200.00", "烟煤（炼焦煤），粉状或非粉状", "Bituminous coal, whether or not pulverised", 0.03, 0.13, "矿产"),
    ("2701", "2701.19", "2701.1900", "2701.1900.00", "其他煤，粉状或非粉状", "Other coal, whether or not pulverised", 0.03, 0.13, "矿产"),
    ("2702", "2702.10", "2702.1000", "2702.1000.00", "褐煤（褐炭），粉状或非粉状", "Lignite, whether or not pulverised", 0.03, 0.13, "矿产"),
    ("2703", "2703.00", "2703.0000", "2703.0000.00", "泥煤（包括肥料用泥煤），不论是否粉化", "Peat (including peat litter), whether or not agglomerated", 0.03, 0.13, "矿产"),
    ("2704", "2704.00", "2704.0000", "2704.0000.00", "煤、褐煤或泥煤制成的焦炭及半焦炭", "Coke and semi-coke of coal, lignite or peat", 0.05, 0.13, "矿产"),
    ("2705", "2705.00", "2705.0000", "2705.0000.00", "煤气、水煤气、炉煤气及类似气体", "Coal gas, water gas, producer gas and similar gases", 0.05, 0.13, "矿产"),
    ("2706", "2706.00", "2706.0000", "2706.0000.00", "从煤、褐煤或泥煤蒸馏所得的焦油及其他矿物焦油", "Tar distilled from coal, lignite or peat", 0.05, 0.13, "矿产"),
    ("2707", "2707.10", "2707.1000", "2707.1000.00", "粗苯", "Benzole", 0.06, 0.13, "矿产"),
    ("2707", "2707.20", "2707.2000", "2707.2000.00", "粗甲苯", "Toluole", 0.06, 0.13, "矿产"),
    ("2707", "2707.30", "2707.3000", "2707.3000.00", "粗二甲苯", "Xylole", 0.06, 0.13, "矿产"),
    ("2707", "2707.40", "2707.4000", "2707.4000.00", "萘", "Naphthalene", 0.06, 0.13, "矿产"),
    ("2708", "2708.10", "2708.1000", "2708.1000.00", "从煤、褐煤或泥煤蒸馏所得的沥青", "Pitch and pitch coke, obtained from coal, lignite or peat", 0.06, 0.13, "矿产"),
    # ============================================================
    # 十四、宝石与贵金属 (7102-7113)
    # ============================================================
    ("7102", "7102.31", "7102.3100", "7102.3100.00", "未加工或经简单锯开的工业用钻石", "Diamonds, industrial, unworked or simply sawn", 0.03, 0.13, "珠宝"),
    ("7102", "7102.39", "7102.3900", "7102.3900.00", "非工业用钻石，未加工或经简单锯开", "Diamonds, non-industrial, unworked or simply sawn", 0.03, 0.13, "珠宝"),
    ("7103", "7103.91", "7103.9100", "7103.9100.00", "经其他方式加工的红宝石、蓝宝石、绿宝石， 未加工", "Rubies, sapphires and emeralds, unworked, simply sawn", 0.03, 0.13, "珠宝"),
    ("7103", "7103.99", "7103.9900", "7103.9900.00", "其他经加工的宝石及次宝石", "Other precious and semi-precious stones, otherwise worked", 0.03, 0.13, "珠宝"),
    ("7104", "7104.10", "7104.1000", "7104.1000.00", "合成或再造的宝石或半宝石，压电石英", "Piezo-electric quartz", 0.03, 0.13, "珠宝"),
    ("7106", "7106.11", "7106.1100", "7106.1100.00", "银，未锻造，非货币用，粉状", "Silver, unwrought, not monetary, powder", 0.03, 0.13, "珠宝"),
    ("7106", "7106.91", "7106.9100", "7106.9100.00", "银，未锻造，非货币用，非粉状", "Silver, unwrought, not monetary, not powder", 0.03, 0.13, "珠宝"),
    ("7108", "7108.11", "7108.1100", "7108.1100.00", "金（货币用），未锻造，非货币用，粉状", "Gold, unwrought, not monetary, powder", 0.03, 0.13, "珠宝"),
    ("7110", "7110.11", "7110.1100", "7110.1100.00", "铂，未锻造或粉末状", "Platinum, unwrought or in powder form", 0.03, 0.13, "珠宝"),
    ("7110", "7110.21", "7110.2100", "7110.2100.00", "钯，未锻造或粉末状", "Palladium, unwrought or in powder form", 0.03, 0.13, "珠宝"),
    ("7113", "7113.11", "7113.1100", "7113.1100.00", "银首饰及其零件", "Jewellery and parts thereof, of silver", 0.08, 0.13, "珠宝"),
    ("7113", "7113.19", "7113.1900", "7113.1900.00", "其他贵重金属首饰及其零件", "Jewellery and parts thereof, of other precious metal", 0.08, 0.13, "珠宝"),
]


# ─── Init ─────────────────────────────────────────────────────────────────────

SEED_ADMIN_EMAIL = "admin@africa-zero.com"
SEED_ADMIN_PASSWORD = "AfricaZero2026Admin!"

# ─── Seed data: Freight routes ─────────────────────────────────────────────────
# (origin_country, origin_port, origin_port_zh, dest_port, dest_port_zh, type, cost_min, cost_max, days_min, days_max, notes)
FREIGHT_ROUTES_SEED = [
    # ============================================================
    # 一、东非主要港口 (ET/KE/TZ/MU/UG/RW/MW/MZ/MG)
    # ============================================================
    # 埃塞俄比亚 → 中国 (经吉布提港)
    ("ET", "Djibouti", "吉布提港", "SHA", "上海港", "sea20gp", 1800, 2500, 28, 35, "埃塞俄比亚主要出海口，需经亚的斯亚贝巴陆运至吉布提约5-7天"),
    ("ET", "Djibouti", "吉布提港", "CAN", "广州港", "sea20gp", 1900, 2600, 28, 35, "广交会期间货运繁忙，建议提前订舱"),
    ("ET", "Djibouti", "吉布提港", "NGB", "宁波港", "sea20gp", 1850, 2550, 28, 35, "宁波-舟山港，散货为主"),
    ("ET", "Djibouti", "吉布提港", "XMN", "厦门港", "sea20gp", 1950, 2700, 28, 35, "东南亚中转航线较少"),
    ("ET", "Djibouti", "吉布提港", "TJN", "天津港", "sea20gp", 2000, 2800, 28, 38, "北方进口为主"),
    ("ET", "Djibouti", "吉布提港", "QDO", "青岛港", "sea20gp", 2050, 2850, 28, 38, "北方水果进口常用港"),
    # 肯尼亚 → 中国 (蒙巴萨港)
    ("KE", "Mombasa", "蒙巴萨港", "SHA", "上海港", "sea20gp", 1900, 2700, 25, 32, "东非主干航线，船期稳定（每周2-3班）"),
    ("KE", "Mombasa", "蒙巴萨港", "CAN", "广州港", "sea20gp", 1950, 2750, 25, 32, "红海航线，经印度洋马德拉斯港中转"),
    ("KE", "Mombasa", "蒙巴萨港", "NGB", "宁波港", "sea20gp", 1900, 2700, 25, 32, "东非-中国主航线"),
    ("KE", "Mombasa", "蒙巴萨港", "XMN", "厦门港", "sea20gp", 2000, 2800, 25, 32, "肯尼亚鲜花空运为主，海运为辅"),
    ("KE", "Mombasa", "蒙巴萨港", "TJN", "天津港", "sea20gp", 2100, 2950, 28, 38, "北方市场进口路线"),
    ("KE", "Mombasa", "蒙巴萨港", "QDO", "青岛港", "sea20gp", 2050, 2900, 28, 38, "矿石/农产品进口"),
    # 坦桑尼亚 → 中国 (达累斯萨拉姆港)
    ("TZ", "Dar es Salaam", "达累斯萨拉姆港", "SHA", "上海港", "sea20gp", 2000, 2800, 28, 38, "坦赞铁路起点，东非重要枢纽港"),
    ("TZ", "Dar es Salaam", "达累斯萨拉姆港", "CAN", "广州港", "sea20gp", 2050, 2900, 28, 38, "印度洋航线，非洲货物进口主港"),
    ("TZ", "Dar es Salaam", "达累斯萨拉姆港", "NGB", "宁波港", "sea20gp", 2000, 2800, 28, 38, ""),
    ("TZ", "Dar es Salaam", "达累斯萨拉姆港", "TJN", "天津港", "sea20gp", 2150, 3000, 30, 42, ""),
    # 毛里求斯 → 中国
    ("MU", "Port Louis", "路易港", "SHA", "上海港", "sea20gp", 1900, 2700, 20, 28, "印度洋自由港，转口贸易活跃，东非直航"),
    ("MU", "Port Louis", "路易港", "CAN", "广州港", "sea20gp", 1950, 2750, 20, 28, "可中转至中国各主要港口"),
    ("MU", "Port Louis", "路易港", "NGB", "宁波港", "sea20gp", 1900, 2700, 20, 28, ""),
    # 乌干达 → 中国 (经蒙巴萨)
    ("UG", "Mombasa", "蒙巴萨港", "SHA", "上海港", "sea20gp", 2000, 2800, 30, 40, "乌干达货物经肯尼亚蒙巴萨出海，陆运约3-5天"),
    ("UG", "Mombasa", "蒙巴萨港", "CAN", "广州港", "sea20gp", 2050, 2850, 30, 40, ""),
    # 卢旺达 → 中国 (经达港)
    ("RW", "Dar es Salaam", "达累斯萨拉姆港", "SHA", "上海港", "sea20gp", 2100, 2950, 30, 42, "卢旺达货物经坦桑达港或肯尼亚蒙巴萨，陆运较复杂"),
    ("RW", "Dar es Salaam", "达累斯萨拉姆港", "CAN", "广州港", "sea20gp", 2150, 3000, 30, 42, ""),
    # 马拉维 → 中国 (经贝拉或达港)
    ("MW", "Beira", "贝拉港", "SHA", "上海港", "sea20gp", 2150, 3100, 32, 48, "马拉维经莫桑比克贝拉港出海"),
    ("MW", "Beira", "贝拉港", "CAN", "广州港", "sea20gp", 2200, 3150, 32, 48, ""),
    # 莫桑比克 → 中国
    ("MZ", "Beira", "贝拉港", "SHA", "上海港", "sea20gp", 2100, 3000, 30, 42, "东非航线，煤/矿/木材为主，港口设施较好"),
    ("MZ", "Beira", "贝拉港", "CAN", "广州港", "sea20gp", 2150, 3050, 30, 42, ""),
    ("MZ", "Beira", "贝拉港", "NGB", "宁波港", "sea20gp", 2100, 3000, 30, 42, ""),
    ("MZ", "Maputo", "马普托港", "SHA", "上海港", "sea20gp", 2150, 3100, 32, 45, "莫桑比克首都港，矿产为主"),
    ("MZ", "Maputo", "马普托港", "CAN", "广州港", "sea20gp", 2200, 3150, 32, 45, ""),
    # 马达加斯加 → 中国
    ("MG", "Toamasina", "图阿马西纳港", "SHA", "上海港", "sea20gp", 2000, 2900, 22, 30, "印度洋航线，香草/矿石为主，马达加斯加最大港"),
    ("MG", "Toamasina", "图阿马西纳港", "CAN", "广州港", "sea20gp", 1950, 2800, 22, 30, "距中国较近，海运费相对合理"),
    ("MG", "Toamasina", "图阿马西纳港", "XMN", "厦门港", "sea20gp", 2050, 2950, 22, 30, "厦门-非洲直航较少"),
    ("MG", "Antsirana", "安塔拉哈港", "SHA", "上海港", "sea20gp", 2100, 3000, 25, 35, "马达加斯加北部深水港，香草/精品农产品"),
    # ============================================================
    # 二、西非主要港口 (GH/CI/NG/SN/BJ/TG/CM/SL/LR/ML/NE/GM)
    # ============================================================
    # 加纳 → 中国
    ("GH", "Tema", "特马港", "SHA", "上海港", "sea20gp", 2100, 3000, 30, 40, "西非重要港口，加纳可可/腰果/铝材出口港"),
    ("GH", "Tema", "特马港", "CAN", "广州港", "sea20gp", 2150, 3100, 30, 40, ""),
    ("GH", "Tema", "特马港", "NGB", "宁波港", "sea20gp", 2100, 3000, 30, 40, ""),
    ("GH", "Tema", "特马港", "TJN", "天津港", "sea20gp", 2200, 3200, 32, 45, ""),
    # 科特迪瓦 → 中国
    ("CI", "Abidjan", "阿比让港", "SHA", "上海港", "sea20gp", 2100, 3000, 30, 40, "法语区西非最大港，科特迪瓦可可/腰果/木材出口"),
    ("CI", "Abidjan", "阿比让港", "CAN", "广州港", "sea20gp", 2150, 3100, 30, 40, "西非法语区货物进口主要港口"),
    ("CI", "Abidjan", "阿比让港", "NGB", "宁波港", "sea20gp", 2100, 3000, 30, 40, ""),
    ("CI", "San-Pédro", "圣佩德罗港", "SHA", "上海港", "sea20gp", 2200, 3150, 32, 45, "科特迪瓦第二大港，可可/木材为主"),
    # 尼日利亚 → 中国 (经拉各斯/阿帕帕)
    ("NG", "Lagos", "拉各斯港", "SHA", "上海港", "sea20gp", 2200, 3200, 32, 45, "西非最大港，货物常经迪拜中转，清关较复杂"),
    ("NG", "Lagos", "拉各斯港", "CAN", "广州港", "sea20gp", 2250, 3250, 32, 45, "尼日利亚是非洲最大经济体，进口需求大"),
    ("NG", "Lagos", "拉各斯港", "NGB", "宁波港", "sea20gp", 2200, 3200, 32, 45, ""),
    ("NG", "Port Harcourt", "哈科特港", "SHA", "上海港", "sea20gp", 2300, 3300, 35, 50, "尼日利亚石油城，原油出口港"),
    # 塞内加尔 → 中国
    ("SN", "Dakar", "达喀尔港", "SHA", "上海港", "sea20gp", 2100, 3000, 30, 42, "西非重要港口，花生/磷酸盐/鱼粉出口"),
    ("SN", "Dakar", "达喀尔港", "CAN", "广州港", "sea20gp", 2150, 3050, 30, 42, ""),
    ("SN", "Dakar", "达喀尔港", "NGB", "宁波港", "sea20gp", 2100, 3000, 30, 42, ""),
    # 贝宁 → 中国
    ("BJ", "Cotonou", "科托努港", "SHA", "上海港", "sea20gp", 2150, 3050, 30, 42, "西非棉花/芝麻出口港，贝宁经济支柱"),
    ("BJ", "Cotonou", "科托努港", "CAN", "广州港", "sea20gp", 2200, 3100, 30, 42, ""),
    # 多哥 → 中国
    ("TG", "Lomé", "洛美港", "SHA", "上海港", "sea20gp", 2150, 3050, 30, 42, "西非天然良港，自由贸易区活跃，转口贸易重要枢纽"),
    ("TG", "Lomé", "洛美港", "CAN", "广州港", "sea20gp", 2200, 3100, 30, 42, ""),
    # 喀麦隆 → 中国
    ("CM", "Douala", "杜阿拉港", "SHA", "上海港", "sea20gp", 2150, 3100, 32, 45, "中非地区主要出海口，木材/可可/咖啡出口"),
    ("CM", "Douala", "杜阿拉港", "CAN", "广州港", "sea20gp", 2200, 3150, 32, 45, ""),
    # 塞拉利昂 → 中国
    ("SL", "Freetown", "弗里敦港", "SHA", "上海港", "sea20gp", 2200, 3150, 32, 48, "西非天然深水港，钻石/可可/咖啡出口"),
    ("SL", "Freetown", "弗里敦港", "CAN", "广州港", "sea20gp", 2250, 3200, 32, 48, ""),
    # 利比里亚 → 中国
    ("LR", "Monrovia", "蒙罗维亚港", "SHA", "上海港", "sea20gp", 2200, 3150, 32, 48, "铁矿砂/橡胶出口，利比里亚是西非最早独立国"),
    ("LR", "Monrovia", "蒙罗维亚港", "CAN", "广州港", "sea20gp", 2250, 3200, 32, 48, ""),
    # 加蓬 → 中国
    ("GA", "Port Gentil", "谦蒂尔港", "SHA", "上海港", "sea20gp", 2250, 3200, 35, 50, "石油/锰矿为主，加蓬主要港口"),
    ("GA", "Port Gentil", "谦蒂尔港", "CAN", "广州港", "sea20gp", 2300, 3300, 35, 50, ""),
    ("GA", "Owendo", "奥文多港", "SHA", "上海港", "sea20gp", 2250, 3200, 35, 50, "加蓬主要木材出口港"),
    # 冈比亚 → 中国
    ("GM", "Banjul", "班珠尔港", "SHA", "上海港", "sea20gp", 2200, 3150, 32, 48, "西非小港，花生/磷酸盐出口"),
    # ============================================================
    # 三、南部非洲 (ZA/AO/NA/BW/ZM/ZW)
    # ============================================================
    # 南非 → 中国 (主要出口港)
    ("ZA", "Durban", "德班港", "SHA", "上海港", "sea20gp", 2200, 3200, 30, 42, "南非最大集装箱港，散货/矿砂/农产品为主"),
    ("ZA", "Durban", "德班港", "CAN", "广州港", "sea20gp", 2300, 3300, 30, 42, "远洋航线，经马六甲，南非主港"),
    ("ZA", "Durban", "德班港", "NGB", "宁波港", "sea20gp", 2200, 3200, 30, 42, ""),
    ("ZA", "Durban", "德班港", "TJN", "天津港", "sea20gp", 2300, 3300, 32, 45, "北方进口"),
    ("ZA", "Cape Town", "开普敦港", "SHA", "上海港", "sea20gp", 2300, 3300, 32, 45, "南非立法首都港，苹果/羊毛/葡萄酒"),
    ("ZA", "Cape Town", "开普敦港", "CAN", "广州港", "sea20gp", 2400, 3400, 32, 45, ""),
    ("ZA", "Port Elizabeth", "伊丽莎白港", "SHA", "上海港", "sea20gp", 2300, 3300, 32, 45, "南非汽车/柑橘出口港"),
    ("ZA", "Port Elizabeth", "伊丽莎白港", "CAN", "广州港", "sea20gp", 2400, 3400, 32, 45, ""),
    ("ZA", "Richards Bay", "理查德湾港", "SHA", "上海港", "sea20gp", 2250, 3250, 32, 48, "南非最大散货港，煤炭/锰矿/铝材出口"),
    ("ZA", "Richards Bay", "理查德湾港", "CAN", "广州港", "sea20gp", 2350, 3350, 32, 48, ""),
    # 安哥拉 → 中国
    ("AO", "Luanda", "罗安达港", "SHA", "上海港", "sea20gp", 2300, 3300, 35, 50, "安哥拉最大港，石油为主，散货矿砂较多"),
    ("AO", "Luanda", "罗安达港", "CAN", "广州港", "sea20gp", 2350, 3350, 35, 50, ""),
    ("AO", "Lobito", "洛比托港", "SHA", "上海港", "sea20gp", 2350, 3350, 35, 50, "安哥拉大西洋深水港，石油/铜矿出口"),
    # 纳米比亚 → 中国
    ("NA", "Walvis Bay", "鲸湾港", "SHA", "上海港", "sea20gp", 2300, 3300, 35, 50, "纳米比亚最大港，渔业/矿业/牛肉出口"),
    ("NA", "Walvis Bay", "鲸湾港", "CAN", "广州港", "sea20gp", 2350, 3350, 35, 50, ""),
    ("NA", "Lüderitz", "吕德里茨港", "SHA", "上海港", "sea20gp", 2350, 3350, 35, 50, "纳米比亚渔业港，捕捞业发达"),
    # 博茨瓦纳 → 中国 (经南非)
    ("BW", " Durban", "（经德班港转陆运）", "SHA", "上海港", "sea20gp", 2400, 3450, 38, 55, "博茨瓦纳为内陆国，经南非德班港出海，矿产品/牛肉"),
    # 赞比亚 → 中国 (经南非/坦桑)
    ("ZM", "Durban", "（经德班港）", "SHA", "上海港", "sea20gp", 2200, 3200, 32, 48, "赞比亚为内陆国，铜带省货物经南非德班出口"),
    ("ZM", "Durban", "（经德班港）", "CAN", "广州港", "sea20gp", 2300, 3300, 32, 48, ""),
    ("ZM", "Dar es Salaam", "（经达累斯萨拉姆）", "SHA", "上海港", "sea20gp", 2300, 3300, 35, 52, "赞比亚亦可经坦桑达港出口，铜/钴矿"),
    # 津巴布韦 → 中国 (经南非)
    ("ZW", "Durban", "（经德班港）", "SHA", "上海港", "sea20gp", 2250, 3250, 32, 48, "津巴布韦为内陆国，烟草/矿砂经南非德班出口"),
    ("ZW", "Durban", "（经德班港）", "CAN", "广州港", "sea20gp", 2350, 3350, 32, 48, ""),
    # ============================================================
    # 四、北非 (EG/TN/MA/DZ/LY/SD)
    # ============================================================
    # 埃及 → 中国 (经苏伊士运河)
    ("EG", "Port Said", "塞得港", "SHA", "上海港", "sea20gp", 1800, 2500, 22, 30, "经苏伊士运河，走亚欧航线，地中海-红海航线枢纽"),
    ("EG", "Port Said", "塞得港", "CAN", "广州港", "sea20gp", 1850, 2600, 22, 30, "地中海航线，船期稳定"),
    ("EG", "Port Said", "塞得港", "NGB", "宁波港", "sea20gp", 1800, 2500, 22, 30, ""),
    ("EG", "Alexandria", "亚历山大港", "SHA", "上海港", "sea20gp", 1850, 2600, 24, 32, "埃及最大港，棉花/化工/食品出口"),
    ("EG", "Alexandria", "亚历山大港", "CAN", "广州港", "sea20gp", 1900, 2700, 24, 32, ""),
    ("EG", "Sokhna", "苏赫奈泉港", "SHA", "上海港", "sea20gp", 1800, 2550, 22, 30, "红海港口，靠近苏伊士运河，效率较高"),
    # 突尼斯 → 中国 (经地中海)
    ("TN", "Tunis", "突尼斯港", "SHA", "上海港", "sea20gp", 1950, 2750, 28, 38, "地中海航线，橄榄油/椰枣/磷酸盐出口"),
    ("TN", "Tunis", "突尼斯港", "CAN", "广州港", "sea20gp", 2000, 2850, 28, 38, ""),
    ("TN", "Sfax", "斯法克斯港", "SHA", "上海港", "sea20gp", 2000, 2850, 28, 38, "突尼斯第二大海港，橄榄油/磷酸盐"),
    # 摩洛哥 → 中国 (经直布罗陀)
    ("MA", "Tanger Med", "丹吉尔港", "SHA", "上海港", "sea20gp", 1900, 2700, 28, 38, "地中海-大西洋枢纽，非洲最大集装箱港之一"),
    ("MA", "Tanger Med", "丹吉尔港", "CAN", "广州港", "sea20gp", 1950, 2800, 28, 38, ""),
    ("MA", "Tanger Med", "丹吉尔港", "NGB", "宁波港", "sea20gp", 1900, 2700, 28, 38, ""),
    ("MA", "Casablanca", "卡萨布兰卡港", "SHA", "上海港", "sea20gp", 1950, 2800, 28, 38, "摩洛哥最大港，磷酸盐/农业/渔业出口"),
    ("MA", "Casablanca", "卡萨布兰卡港", "CAN", "广州港", "sea20gp", 2000, 2850, 28, 38, ""),
    # 阿尔及利亚 → 中国
    ("DZ", "Algiers", "阿尔及尔港", "SHA", "上海港", "sea20gp", 2000, 2850, 28, 40, "地中海南岸最大港，石油/天然气/椰枣出口"),
    ("DZ", "Algiers", "阿尔及尔港", "CAN", "广州港", "sea20gp", 2050, 2900, 28, 40, ""),
    ("DZ", "Oran", "奥兰港", "SHA", "上海港", "sea20gp", 2050, 2900, 28, 40, "阿尔及利亚西部港口，葡萄酒/蔬菜出口"),
    # 利比亚 → 中国
    ("LY", "Tripoli", "的黎波里港", "SHA", "上海港", "sea20gp", 2000, 2850, 28, 40, "地中海航线，石油/化工出口"),
    ("LY", "Benghazi", "班加西港", "SHA", "上海港", "sea20gp", 2050, 2900, 28, 40, "利比亚东部主要港口"),
    # 苏丹 → 中国 (经红海)
    ("SD", "Port Sudan", "苏丹港", "SHA", "上海港", "sea20gp", 1850, 2600, 24, 32, "苏丹唯一对外贸易港，阿拉伯胶/棉花/芝麻出口"),
    ("SD", "Port Sudan", "苏丹港", "CAN", "广州港", "sea20gp", 1900, 2700, 24, 32, "红海航线，距中国较近"),
    ("SD", "Port Sudan", "苏丹港", "NGB", "宁波港", "sea20gp", 1850, 2600, 24, 32, ""),
    # 吉布提 → 中国 (直航)
    ("DJ", "Djibouti", "吉布提港", "SHA", "上海港", "sea20gp", 1750, 2400, 22, 28, "红海入口，中国海军补给港，一带一路重要节点"),
    ("DJ", "Djibouti", "吉布提港", "CAN", "广州港", "sea20gp", 1700, 2350, 22, 28, "距中国近，海运费相对较低"),
    ("DJ", "Djibouti", "吉布提港", "NGB", "宁波港", "sea20gp", 1750, 2400, 22, 28, ""),
    # ============================================================
    # 五、中非 (CD/GA/AO/CM/BI)
    # ============================================================
    # 刚果（金）→ 中国 (经坦桑/南非)
    ("CD", "Dar es Salaam", "（经达累斯萨拉姆）", "SHA", "上海港", "sea20gp", 2200, 3200, 35, 50, "刚果（金）经坦桑达港出海，陆运较复杂，钴/铜矿"),
    ("CD", "Dar es Salaam", "（经达累斯萨拉姆）", "CAN", "广州港", "sea20gp", 2250, 3250, 35, 50, ""),
    ("CD", "Durban", "（经德班港）", "SHA", "上海港", "sea20gp", 2350, 3350, 38, 55, "刚果（金）亦可经南非德班出海"),
    # 布隆迪 → 中国 (经坦桑)
    ("BI", "Dar es Salaam", "（经达累斯萨拉姆）", "SHA", "上海港", "sea20gp", 2300, 3300, 35, 50, "布隆迪为内陆国，经坦桑达港出海，咖啡/茶叶"),
    # ============================================================
    # 六、40GP 集装箱路线 (约20GP的1.8倍价格)
    # ============================================================
    ("ET", "Djibouti", "吉布提港", "SHA", "上海港", "sea40hp", 3200, 4500, 28, 35, "40GP集装箱，大批量货物首选"),
    ("ET", "Djibouti", "吉布提港", "CAN", "广州港", "sea40hp", 3300, 4600, 28, 35, ""),
    ("KE", "Mombasa", "蒙巴萨港", "SHA", "上海港", "sea40hp", 3400, 4800, 25, 32, ""),
    ("KE", "Mombasa", "蒙巴萨港", "CAN", "广州港", "sea40hp", 3450, 4900, 25, 32, ""),
    ("TZ", "Dar es Salaam", "达累斯萨拉姆港", "SHA", "上海港", "sea40hp", 3600, 5000, 28, 38, ""),
    ("ZA", "Durban", "德班港", "SHA", "上海港", "sea40hp", 4000, 5800, 30, 42, ""),
    ("GH", "Tema", "特马港", "SHA", "上海港", "sea40hp", 3800, 5400, 30, 40, ""),
    ("CI", "Abidjan", "阿比让港", "SHA", "上海港", "sea40hp", 3800, 5400, 30, 40, ""),
    ("NG", "Lagos", "拉各斯港", "SHA", "上海港", "sea40hp", 4000, 5800, 32, 45, ""),
    ("EG", "Port Said", "塞得港", "SHA", "上海港", "sea40hp", 3200, 4600, 22, 30, ""),
    ("MA", "Tanger Med", "丹吉尔港", "SHA", "上海港", "sea40hp", 3400, 4900, 28, 38, ""),
    ("SD", "Port Sudan", "苏丹港", "SHA", "上海港", "sea40hp", 3300, 4600, 24, 32, ""),
    # ============================================================
    # 七、空运路线 (按公斤计，适合高价值样品)
    # ============================================================
    ("ET", "ADD", "亚的斯亚贝巴机场", "SHA", "上海浦东机场", "air", 8, 18, 1, 3, "空运按公斤计，适合高价值样品（咖啡/可可样品/宝石）"),
    ("ET", "ADD", "亚的斯亚贝巴机场", "CAN", "广州白云机场", "air", 7, 16, 1, 3, "非洲最大航空枢纽，埃塞航空货运发达"),
    ("KE", "NBO", "内罗毕机场", "SHA", "上海浦东机场", "air", 7, 15, 1, 3, "非洲空运枢纽，鲜花/咖啡豆空运精品线"),
    ("KE", "NBO", "内罗毕机场", "CAN", "广州白云机场", "air", 6, 14, 1, 3, "肯尼亚空运出口以鲜花为主，农产品为辅"),
    ("ZA", "JNB", "约翰内斯堡机场", "SHA", "上海浦东机场", "air", 9, 20, 1, 3, "非洲最大航空港，黄金/宝石/葡萄酒空运"),
    ("ZA", "JNB", "约翰内斯堡机场", "CAN", "广州白云机场", "air", 8, 18, 1, 3, ""),
    ("EG", "CAI", "开罗机场", "SHA", "上海浦东机场", "air", 7, 16, 1, 3, "北非空运枢纽，化工/农产品空运"),
    ("EG", "CAI", "开罗机场", "CAN", "广州白云机场", "air", 6, 15, 1, 3, ""),
    ("MA", "CMN", "卡萨布兰卡机场", "SHA", "上海浦东机场", "air", 8, 17, 1, 3, "摩洛哥空运枢纽，农产品/皮革"),
]

# ─── Seed data: Certificate of Origin guides ──────────────────────────────────
# (country_code, country_name_zh, cert_type, issuing_authority, website, fee_min, fee_max, days_min, days_max, requirements, steps, api, notes)
CERT_GUIDES_SEED = [
    (
        "ET", "埃塞俄比亚", "CO",
        "Ethiopian Chamber of Commerce and Sectoral Associations (ECCSA)",
        "埃塞俄比亚商会", "https://www.eccsa.com", 30, 80, 3, 7,
        '["申请表","发票","装箱单","原产地声明","生产工艺说明"]',
        '["联系供应商准备文件","向ECCSA提交申请","支付证书费","领取证书","快递至中国进口商"]',
        0, "埃塞俄比亚最大商会，可办理一般原产地证CO"
    ),
    (
        "KE", "肯尼亚", "CO",
        "Kenya National Chamber of Commerce and Industry (KNCCI)",
        "肯尼亚国家工商会", "https://www.kenyachamber.org", 40, 100, 3, 5,
        '["申请表","发票","装箱单","出口商声明","货物描述"]',
        '["准备商业发票","联系KNCCI当地分会","提交申请","审核通过后缴费","取证"]',
        0, "肯尼亚贸工部授权机构，需在当地有办公点"
    ),
    (
        "TZ", "坦桑尼亚", "CO",
        "Tanzania Chamber of Commerce, Industry and Agriculture (TCCIA)",
        "坦桑尼亚工商农商会", "http://www.tccia.com", 35, 90, 3, 7,
        '["申请表","发票","出口商声明","货物明细表"]',
        '["出口商向TCCIA提交","审核货物原产资格","缴纳费用","签发证书"]',
        0, "坦桑尼亚官方授权办理机构"
    ),
    (
        "GH", "加纳", "CO",
        "Ghana Export Promotion Authority (GEPA)",
        "加纳出口促进局", "https://www.gepaghana.gov.gh", 30, 70, 2, 5,
        '["申请表","发票","装箱单","出口商声明","产品质量证书"]',
        '["出口商注册","向GEPA提交原产证申请","审核","缴费取证","快递"]',
        0, "加纳贸工部下属机构，专管出口认证"
    ),
    (
        "ZA", "南非", "CO",
        "South African Chamber of Commerce and Industry (Sacci)",
        "南非商会", "https://www.sacci.org.za", 50, 120, 2, 5,
        '["申请表","商业发票","装箱单","出口商声明","原产地证书表格"]',
        '["向Sacci提交","审核文件","缴费","取证或电子签发"]',
        0, "南非是唯一同时与中国和非洲都有EPA的国家，证书体系最完善"
    ),
    (
        "EG", "埃及", "CO",
        "Federation of Egyptian Chambers of Commerce",
        "埃及商会联合会", "https://www.fedex.gov.eg", 40, 100, 3, 7,
        '["申请表","发票","装箱单","出口商声明","产品质量证明"]',
        '["出口商向当地商会申请","提交完整文件","审核","缴费","领取证书"]',
        0, "埃及海关接受贸促会认证的中国版式"
    ),
    (
        "CI", "科特迪瓦", "CO",
        "Confederation Generale des Enterprises de Cote d'Ivoire (CGECI)",
        "科特迪瓦企业总联合会", "https://www.cgeci.org", 35, 85, 3, 6,
        '["申请表","发票","装箱单","出口商声明","加工工序说明"]',
        '["联系CGECI","提交申请文件","审核","缴费","取证"]',
        0, "法语区，需准备法语版文件"
    ),
    (
        "NG", "尼日利亚", "CO",
        "Nigerian Association of Chambers of Commerce, Industry, Mines and Agriculture (NACCIMA)",
        "尼日利亚工商农商会协会", "https://www.naccima.com", 45, 110, 3, 7,
        '["申请表","发票","装箱单","Nexus卡片","出口商声明"]',
        '["出口商NEXUS注册","向NACCIMA申请","提交全部文件","审核","取证"]',
        0, "尼日利亚海关较复杂，建议使用专业清关代理"
    ),
    (
        "MG", "马达加斯加", "CO",
        "Confederation of Malagasy Trade (FTM)",
        "马达加斯加工会联合会", "http://www.ftm.mg", 30, 75, 3, 6,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向FTM提交","审核","缴费","取证"]',
        0, "法语区，香草、丁香等特产出口较多"
    ),
    (
        "UG", "乌干达", "CO",
        "Uganda Chamber of Commerce and Industry (UCCI)",
        "乌干达工商会", "https://www.ucci.org.ug", 30, 80, 2, 5,
        '["申请表","发票","装箱单","出口商声明"]',
        '["联系UCCI","提交文件","审核","缴费取证"]',
        0, ""
    ),
    (
        "RW", "卢旺达", "CO",
        "Private Sector Federation (PSF) Rwanda",
        "卢旺达私营企业联合会", "https://www.psf.gov.rw", 25, 70, 2, 5,
        '["申请表","发票","出口商声明","货物说明"]',
        '["向PSF提交","审核","缴费","取证"]',
        0, "卢旺达政府积极推动出口，流程相对简化"
    ),
    (
        "MU", "毛里求斯", "CO",
        "Mauritius Chamber of Commerce and Industry (MCCI)",
        "毛里求斯工商会", "https://www.mcci.org", 40, 90, 2, 4,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向MCCI提交","审核","缴费","取证","快递"]',
        0, "毛里求斯是自由港，认证体系成熟"
    ),
    # ============================================================
    # 扩展证书办理指南：新增 30+ 非洲国家
    # ============================================================
    # 中非
    (
        "CM", "喀麦隆", "CO",
        "Cameroon Chamber of Commerce, Industry and Mines (CCIMA)",
        "喀麦隆工商会", "https://www.ccima.cm", 40, 100, 3, 7,
        '["申请表","发票","装箱单","出口商声明","品质证书"]',
        '["向CCIMA提交","审核","缴费","取证"]',
        0, "法语区，需法语文件，喀麦隆最大商会"
    ),
    (
        "GA", "加蓬", "CO",
        "Gabon Chamber of Commerce (CPG)",
        "加蓬工商会", "https://www.cpg.ga", 45, 110, 3, 7,
        '["申请表","发票","装箱单","出口商声明"]',
        '["联系CPG","提交文件","审核","缴费取证"]',
        0, "法语区，石油和锰矿出口为主"
    ),
    (
        "AO", "安哥拉", "CO",
        "Câmara de Comércio de Angola (CCA)",
        "安哥拉商会", "https://www.cca.ao", 50, 120, 3, 7,
        '["申请表","发票","装箱单","原产地声明","商业登记证"]',
        '["向CCA提交","审核文件","缴费","取证"]',
        0, "葡萄牙语区，石油/钻石出口，需商业登记证"
    ),
    (
        "CD", "刚果（金）", "CO",
        "Office National du Commercialisation des Produits Miniers (OFED)",
        "刚果（金）矿业销售局", "https://www.ofed.cd", 60, 150, 5, 10,
        '["申请表","发票","装箱单","出口商声明","矿产出口许可证"]',
        '["向OFED申请","提交全部文件","审核","缴费","取证"]',
        0, "法语区，钴/铜矿出口，需特别许可，清关复杂"
    ),
    # 西非法语区
    (
        "SN", "塞内加尔", "CO",
        "Confédération Nationale du Patronat du Sénégal (CNP)",
        "塞内加尔企业主联合会", "https://www.cnp.sn", 35, 85, 2, 5,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向商会提交","审核","缴费","取证"]',
        0, "法语区，花生/磷酸盐/鱼粉出口"
    ),
    (
        "BJ", "贝宁", "CO",
        "Chambre de Commerce et d'Industrie du Bénin (CCIB)",
        "贝宁工商会", "https://www.cci.bj", 30, 75, 2, 5,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向CCIB提交","审核","缴费","取证"]',
        0, "法语区，棉花/芝麻出口，流程相对简化"
    ),
    (
        "TG", "多哥", "CO",
        "Chambre de Commerce et d'Industrie du Togo (CCIT)",
        "多哥工商会", "https://www.ccit.tg", 30, 75, 2, 5,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向CCIT提交","审核","缴费","取证"]',
        0, "法语区，自由贸易区活跃，流程简化"
    ),
    (
        "ML", "马里", "CO",
        "Chambre de Commerce et d'Industrie du Mali (CCIM)",
        "马里工商会", "https://www.ccim.ml", 35, 80, 3, 6,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向CCIM提交","审核","缴费","取证"]',
        0, "法语区，内陆国，棉花/芝麻出口"
    ),
    (
        "NE", "尼日尔", "CO",
        "Chambre de Commerce et d'Industrie du Niger (CCIN)",
        "尼日尔工商会", "https://www.ccin.ne", 30, 70, 2, 5,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向CCIN提交","审核","缴费","取证"]',
        0, "法语区，内陆国，洋葱/农产品出口"
    ),
    (
        "BF", "布基纳法索", "CO",
        "Chambre de Commerce et d'Industrie du Burkina Faso (CCI-BF)",
        "布基纳法索工商会", "https://www.cci.bf", 30, 70, 2, 5,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向CCI-BF提交","审核","缴费","取证"]',
        0, "法语区，内陆国，棉花/芝麻出口"
    ),
    (
        "GW", "几内亚", "CO",
        "Chambre de Commerce et d'Industrie de la République de Guinée (CCI-Guinée)",
        "几内亚工商会", "https://www.cci-guinee.com", 40, 90, 3, 6,
        '["申请表","发票","装箱单","出口商声明","探矿许可证"]',
        '["向CCI提交","审核","缴费","取证"]',
        0, "法语区，铝矾土/金/钻石出口"
    ),
    (
        "GN", "几内亚比绍", "CO",
        "Câmara de Comércio da Guiné-Bissau",
        "几内亚比绍商会", "https://www.ccgb.gw", 35, 80, 3, 6,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向商会提交","审核","缴费","取证"]',
        0, "葡萄牙语区，腰果/木材出口"
    ),
    (
        "GM", "冈比亚", "CO",
        "Gambia Chamber of Commerce (GCC)",
        "冈比亚商会", "https://www.gambia.org.gm", 30, 70, 2, 5,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向GCC提交","审核","缴费","取证"]',
        0, "英语区，花生出口为主"
    ),
    (
        "SL", "塞拉利昂", "CO",
        "Sierra Leone Chamber of Commerce (SLCC)",
        "塞拉利昂商会", "https://www.slcc.sl", 35, 80, 2, 5,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向SLCC提交","审核","缴费","取证"]',
        0, "英语区，可可/咖啡/钻石出口"
    ),
    (
        "LR", "利比里亚", "CO",
        "Liberian Chamber of Commerce (LCC)",
        "利比里亚商会", "https://www.liberianchamber.org", 35, 85, 2, 5,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向LCC提交","审核","缴费","取证"]',
        0, "英语区，橡胶/可可/铁矿出口"
    ),
    # 南部非洲
    (
        "NA", "纳米比亚", "CO",
        "Namibia Chamber of Commerce (NCC)",
        "纳米比亚商会", "https://www.naccuna.com", 40, 95, 2, 5,
        '["申请表","商业发票","装箱单","出口商声明","原产地表格"]',
        '["向NCC提交","审核文件","缴费","取证"]',
        0, "英语区，牛肉/矿产品出口，唯一向中国出口牛肉的非洲国家"
    ),
    (
        "BW", "博茨瓦纳", "CO",
        "Botswana Chamber of Commerce (BCC)",
        "博茨瓦纳商会", "https://www.bcc.org.bw", 45, 100, 3, 6,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向BCC提交","审核","缴费","取证"]',
        0, "英语区，内陆国，牛肉/金刚石出口"
    ),
    (
        "ZM", "赞比亚", "CO",
        "Zambia Chamber of Commerce (ZCC)",
        "赞比亚商会", "https://www.zambiachamber.org", 40, 95, 2, 5,
        '["申请表","发票","装箱单","出口商声明","铜出口证书"]',
        '["向ZCC提交","审核","缴费","取证"]',
        0, "英语区，铜/钴/祖母绿出口，需铜出口特别许可"
    ),
    (
        "MW", "马拉维", "CO",
        "Malawi Confederation of Chambers of Commerce (MCCCI)",
        "马拉维工商会", "https://www.mccci.org", 30, 75, 2, 5,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向MCCCI提交","审核","缴费","取证"]',
        0, "英语区，内陆国，烟草/茶/糖出口"
    ),
    (
        "SZ", "斯威士兰", "CO",
        "Swaziland Chamber of Commerce (SCC)",
        "斯威士兰商会", "https://www.scc.org.sz", 35, 80, 2, 5,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向SCC提交","审核","缴费","取证"]',
        0, "英语区，内陆国，糖/棉花/木材出口"
    ),
    (
        "LS", "莱索托", "CO",
        "Lesotho Chamber of Commerce (LCC)",
        "莱索托商会", "https://www.lcc.org.ls", 30, 75, 2, 5,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向LCC提交","审核","缴费","取证"]',
        0, "英语区，内陆国，羊毛/马海毛出口"
    ),
    (
        "MZ", "莫桑比克", "CO",
        "Associação Moçambicana de Câmaras de Comércio (AMCC)",
        "莫桑比克工商会", "https://www.amcc.mz", 40, 90, 3, 6,
        '["申请表","发票","装箱单","出口商声明","自然资源许可证"]',
        '["向AMCC提交","审核","缴费","取证"]',
        0, "葡萄牙语区，腰果/木材/矿产品出口"
    ),
    # 北非
    (
        "TN", "突尼斯", "CO",
        "Union Tunisienne de l'Industrie, du Commerce et de l'Artisanat (UTICA)",
        "突尼斯工商手工业联合会", "https://www.utica.org.tn", 35, 85, 2, 5,
        '["申请表","发票","装箱单","出口商声明","原产地声明"]',
        '["向UTICA提交","审核","缴费","取证","快递"]',
        0, "法语区，橄榄油/椰枣/磷酸盐出口"
    ),
    (
        "DZ", "阿尔及利亚", "CO",
        "Confédération Algérienne du Patronat (CAP)",
        "阿尔及利亚企业主联合会", "https://www.cng.dz", 45, 100, 3, 7,
        '["申请表","发票","装箱单","出口商声明","商业登记证"]',
        '["向CAP提交","审核","缴费","取证"]',
        0, "法语区，石油/天然气/椰枣出口，流程较复杂"
    ),
    (
        "LY", "利比亚", "CO",
        "Libyan Chamber of Commerce (LCC)",
        "利比亚商会", "https://www.lcc.ly", 50, 120, 3, 7,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向LCC提交","审核","缴费","取证"]',
        0, "阿拉伯语区，石油出口，政局不稳时流程复杂"
    ),
    (
        "SD", "苏丹", "CO",
        "Sudan Chamber of Commerce (SCC)",
        "苏丹商会", "https://www.sudancommerce.gov.sd", 35, 80, 2, 5,
        '["申请表","发票","装箱单","出口商声明","阿拉伯胶出口许可"]',
        '["向SCC提交","审核","缴费","取证"]',
        0, "阿拉伯语区，阿拉伯胶/棉花/芝麻出口"
    ),
    (
        "SS", "南苏丹", "CO",
        "South Sudan Chamber of Commerce (SSCC)",
        "南苏丹商会", "https://www.sscc.org", 50, 120, 5, 10,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向SSCC提交","审核","缴费","取证"]',
        0, "英语区，内陆国，石油/农产品出口，流程复杂"
    ),
    (
        "SO", "索马里", "CO",
        "Somalia Chamber of Commerce (SCC)",
        "索马里商会", "https://www.somaliachamber.so", 50, 120, 5, 10,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向商会提交","审核","缴费","取证"]',
        0, "英语区，香料/牲畜出口，流程复杂，政局不稳"
    ),
    (
        "ET", "厄立特里亚", "CO",
        "Eritrea Chamber of Commerce (ECC)",
        "厄立特里亚商会", "https://www.eritrea-chamber.com", 40, 100, 3, 7,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向ECC提交","审核","缴费","取证"]',
        0, "英语区，内陆国，渔产品/矿产出口"
    ),
    (
        "DJ", "吉布提", "CO",
        "Chambre de Commerce de Djibouti (CCD)",
        "吉布提商会", "https://www.ccd.dj", 30, 70, 2, 4,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向CCD提交","审核","缴费","取证"]',
        0, "法语区，自由港，物流枢纽作用强"
    ),
    # 东非岛国
    (
        "SC", "塞舌尔", "CO",
        "Seychelles Chamber of Commerce (SCC)",
        "塞舌尔商会", "https://www.seychelleschamber.sc", 45, 100, 2, 4,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向SCC提交","审核","缴费","取证","快递"]',
        0, "英语区，印度洋自由港，金枪鱼/香料出口"
    ),
    (
        "KM", "科摩罗", "CO",
        "Chambre de Commerce des Comores (CCC)",
        "科摩罗商会", "https://www.cccomores.km", 35, 80, 3, 6,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向CCC提交","审核","缴费","取证"]',
        0, "法语区，伊兰-伊兰/香草/椰子出口"
    ),
    # 中部非洲
    (
        "CF", "中非共和国", "CO",
        "Chambre de Commerce de la RCA (CCRA)",
        "中非共和国商会", "https://www.ccra.cf", 50, 120, 5, 10,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向CCRA提交","审核","缴费","取证"]',
        0, "法语区，内陆国，钻石/木材出口，流程复杂"
    ),
    (
        "TD", "乍得", "CO",
        "Chambre de Commerce du Tchad (CCT)",
        "乍得商会", "https://www.cct.td", 50, 120, 5, 10,
        '["申请表","发票","装箱单","出口商声明"]',
        '["向CCT提交","审核","缴费","取证"]',
        0, "法语区，内陆国，石油/棉花出口，流程复杂"
    ),
    # 其他重要出口品类证书
    # 埃塞俄比亚 - FORM A (普惠制)
    (
        "ET", "埃塞俄比亚", "FORM_A",
        "Ethiopian Chamber of Commerce and Sectoral Associations (ECCSA)",
        "埃塞俄比亚商会", "https://www.eccsa.com", 50, 120, 3, 7,
        '["FORM A申请表","发票","装箱单","原产地声明","原材料来源说明"]',
        '["向ECCSA提交","审核原产资格","缴费","取证"]',
        0, "普惠制原产地证书，中国从最不发达国家进口适用零关税"
    ),
    # 肯尼亚 - FORM A
    (
        "KE", "肯尼亚", "FORM_A",
        "Kenya National Chamber of Commerce and Industry (KNCCI)",
        "肯尼亚国家工商会", "https://www.kenyachamber.org", 60, 140, 3, 7,
        '["FORM A申请表","商业发票","装箱单","原产地声明","加工说明"]',
        '["联系KNCCI","提交申请","审核","缴费","取证"]',
        0, "肯尼亚属于中等收入国家，FORM A不适用零关税但可享受优惠税率"
    ),
    # 苏丹 - 阿拉伯胶出口特殊证书
    (
        "SD", "苏丹", "GUM_ARABIC_CERT",
        "Sudan Chamber of Commerce (SCC)",
        "苏丹商会", "https://www.sudancommerce.gov.sd", 40, 100, 2, 5,
        '["申请表","发票","装箱单","阿拉伯胶产地证明","质检证书"]',
        '["向商会申请","提交全部文件","审核","取证"]',
        0, "阿拉伯胶是苏丹战略出口品，需额外质量认证"
    ),
]


# ─── Seed data: Africa Product Selection / Market Analysis ─────────────────────
# (category, product_name_zh, product_name_en, main_hs_codes, origin_countries,
#  target_china_market, import_requirements, zero_tariff, tariff_rate,
#  market_size, growth_rate, top_importers, supplier_countries,
#  key_suppliers, certification_needs, logistics_notes, risk_factors, recommendation, status)
MARKET_ANALYSIS_SEED = [
    # ============================================================
    # 一、咖啡 (Coffee) — 非洲最大出口品类
    # ============================================================
    ("咖啡", "生咖啡豆（水洗/日晒）", "Green Coffee Beans (Washed/Natural)",
     "0901.11", "ET|KE|TZ|UG|RW|ZW|MW|BI|CM|ET",
     "精品电商|大型烘焙商|连锁咖啡店|大宗贸易",
     "需进口检验检疫证书；埃塞俄比亚要求商会CO证",
     1, 0.08,
     "全球约$1,200亿美元，中国年进口$50亿美元",
     "年增8-12%", "美国|德国|意大利|中国|日本",
     "埃塞俄比亚|肯尼亚|坦桑尼亚|乌干达|卢旺达",
     "埃塞ECCU|肯尼亚Coffee Board|坦桑TCB|乌干达UCDA",
     "有机认证，雨林联盟认证，Fairtrade",
     "走海运20-40天；肯尼亚蒙巴萨港→中国需冷链存储",
     "价格波动大|汇率风险|生豆保鲜期约2年",
     "非洲咖啡以精品著称，零关税政策下进口利润空间大，建议优先开发埃塞俄比亚水洗豆和肯尼亚AA级",
     "featured"),
    ("咖啡", "烘焙咖啡豆", "Roasted Coffee Beans",
     "0901.21", "ET|KE|ZA|TZ|UG",
     "精品电商|咖啡连锁|零售",
     "需食品标签认证；熏蒸证书",
     1, 0.15,
     "全球约$800亿美元",
     "年增5%", "美国|加拿大|英国|中国|韩国",
     "埃塞俄比亚|肯尼亚|南非|乌干达",
     "埃塞Starbucks供应商|肯尼亚ABeans",
     "HACCP认证",
     "烘焙豆保质期约1年，需真空包装",
     "国内烘焙商竞争激烈|进口烘焙豆关税15%较高",
     "建议进口生豆国内烘焙，避免高关税",
     "active"),
    ("咖啡", "速溶咖啡浓缩精汁", "Instant Coffee Extracts",
     "2101.11", "ET|KE|CI|GH|UG|TZ",
     "食品加工|零售|电商平台",
     "食品添加剂标准|进口检验检疫",
     1, 0.12,
     "全球约$400亿美元",
     "年增4%", "中国|印度尼西亚|菲律宾|越南|美国",
     "埃塞俄比亚|科特迪瓦|肯尼亚|加纳",
     "Nescafé供应商|肯尼亚Coffee Solutions",
     "ISO22000|FDA注册",
     "走海运集装箱，体积大",
     "国际大品牌垄断市场|国内竞争激烈",
     "速溶利润薄，建议做精品冷萃咖啡浓缩液差异化",
     "active"),

    # ============================================================
    # 二、可可 (Cocoa) — 高利润潜力品类
    # ============================================================
    ("可可", "可可豆（生可可）", "Raw Cocoa Beans",
     "1801.00", "CI|GH|NG|CM|GA|TG|LR|SL",
     "巧克力工厂|食品加工|化妆品原料",
     "进口检验检疫；黄曲霉素检测；CI要求CO证",
     1, 0.08,
     "全球约$150亿美元，中国年进口约$10亿美元",
     "年增10-15%", "荷兰|美国|马来西亚|中国|德国",
     "科特迪瓦|加纳|尼日利亚|喀麦隆|加蓬",
     "科特迪瓦CAITDA|加纳Cocobod|尼日利亚NCX",
     "有机认证|Fairtrade认证|雨林联盟",
     "集装箱海运，注意防潮防霉变；温度≤25°C",
     "可可价格波动极大|产地政治风险|气候变化影响",
     "非洲可可豆品质优良，零关税后利润显著提升，建议深耕科特迪瓦和加纳供应商",
     "featured"),
    ("可可", "可可脂", "Cocoa Butter",
     "1804.00", "CI|GH|NG|CM",
     "化妆品原料|食品加工|巧克力工厂",
     "食品添加剂标准；化妆品原料备案",
     1, 0.20,
     "全球约$50亿美元",
     "年增8%", "美国|欧盟|中国|日本|韩国",
     "科特迪瓦|加纳|尼日利亚|喀麦隆",
     "科特迪瓦CICA|加纳Cocoa Processing Company",
     "有机认证|ISO认证",
     "海运，固体状态运输，需避光储存",
     "国际大公司控制定价权",
     "可可脂用途广泛（化妆品+食品），建议捆绑可可豆一起进口",
     "active"),
    ("可可", "可可膏", "Cocoa Paste/Liquor",
     "1803.10", "CI|GH|NG",
     "巧克力工厂|食品加工|烘焙原料",
     "食品添加剂标准",
     1, 0.10,
     "全球约$40亿美元",
     "年增7%", "荷兰|美国|中国|德国|巴西",
     "科特迪瓦|加纳|尼日利亚",
     "科特迪瓦SACO|加纳Fair Trade Cocoa",
     "HACCP认证",
     "液体/糊状，运输需保温集装箱",
     "保质期约2年",
     "巧克力工厂采购量大，薄利多销模式",
     "active"),
    ("可可", "可可粉（无糖）", "Cocoa Powder (Unsweetened)",
     "1805.00", "CI|GH|NG|CM",
     "食品加工|烘焙|饮料原料",
     "食品添加剂标准",
     1, 0.15,
     "全球约$30亿美元",
     "年增6%", "美国|荷兰|中国|德国|巴西",
     "科特迪瓦|加纳|尼日利亚|喀麦隆",
     "科特迪瓦CICA|加纳Cocoa Processing",
     "有机认证|NON-GMO",
     "粉末状，袋装集装箱运输",
     "国内可可粉市场竞争激烈，价格透明",
     "建议进口有机认证可可粉，定位高端食品加工",
     "active"),

    # ============================================================
    # 三、坚果与果仁 (Nuts & Dried Fruits)
    # ============================================================
    ("坚果", "腰果（去壳，RW500/W240）", "Cashew Nuts (Shelled, RW500/W240 Grade)",
     "0801.32", "CI|TZ|MZ|GH|BJ|TG|SN",
     "零食品牌|食品加工|坚果进口商|电商平台",
     "进口检验检疫；坚果类需植检证书",
     1, 0.10,
     "全球约$80亿美元，中国年进口约$5亿美元",
     "年增12%", "印度|美国|越南|中国|荷兰",
     "科特迪瓦|坦桑尼亚|莫桑比克|加纳|贝宁",
     "科特迪瓦TAN-CA|坦桑Tanzania Cashew Board|莫桑比克NACOTI",
     "HACCP认证|有机认证",
     "海运集装箱，注意防潮；保质期约2年",
     "印度是最大加工国，非洲主要出口生果仁|越南竞争激烈|汇率风险",
     "非洲腰果无污染品质优，零关税后竞争力强，建议与坦桑尼亚和莫桑比克供应商建立长期合作",
     "featured"),
    ("坚果", "花生（去壳/带壳）", "Groundnuts (Peanuts, Shelled/In-shell)",
     "1202.30|1202.41", "SN|MZ|ZA|TZ|GH|SD",
     "榨油厂|食品加工|零食品牌|出口贸易",
     "进口检验检疫；黄曲霉素检测",
     1, 0.09,
     "全球约$60亿美元",
     "年增5%", "中国|印度|美国|阿根廷|印尼",
     "塞内加尔|阿根廷|苏丹|坦桑尼亚|中国",
     "塞内加尔FNM|坦桑NIC",
     "有机认证|NON-GMO",
     "榨油用花生走散货船；零食用走集装箱",
     "黄曲霉素超标风险|国内榨油产能过剩",
     "食品级花生适合中国零食市场，建议开发塞内加尔和苏丹的有机认证花生",
     "active"),
    ("坚果", "夏威夷果（Macadamia）", "Macadamia Nuts (In-shell/Shelled)",
     "0802.61|0802.62", "ZA|KW|MZ|KE",
     "高端零食|电商|礼品|烘焙原料",
     "进口检验检疫；坚果植检证书",
     1, 0.12,
     "全球约$20亿美元，中国约$2亿美元",
     "年增20%", "中国|美国|澳大利亚|欧盟",
     "南非|肯尼亚|澳大利亚|危地马拉",
     "南非SA macadamia|肯尼亚KMRC",
     "有机认证|HACCP",
     "空运或海运，注意防潮；保质期1年",
     "中国高端市场增长迅速|澳洲是主要竞争",
     "中国高端消费者对夏威夷果接受度高，建议从南非进口，关注肯尼亚新兴产区",
     "active"),
    ("坚果", "榛子（去壳）", "Hazelnuts (Shelled)",
     "0802.22", "TZ|KE|ET",
     "巧克力工厂|食品加工|烘焙|零食",
     "进口检验检疫",
     1, 0.12,
     "全球约$10亿美元",
     "年增6%", "德国|意大利|中国|美国|法国",
     "土耳其（全球最大）|阿塞拜疆|格鲁吉亚|坦桑尼亚",
     "坦桑尼亚Kilimanjaro Nuts",
     "有机认证",
     "海运集装箱，注意防霉变",
     "土耳其主导市场|非洲产量较小",
     "建议坦桑尼亚榛子作为差异化产品打入欧洲出口链",
     "active"),

    # ============================================================
    # 四、油籽与植物油 (Oilseeds & Vegetable Oils)
    # ============================================================
    ("油籽", "芝麻（白/黑）", "Sesame Seeds (White/Black)",
     "1207.40", "TZ|SN|SD|MZ|ET|GH|NE|BJ",
     "榨油厂|食品加工|出口贸易|电商",
     "进口检验检疫；坦桑尼亚要求CO证",
     1, 0.10,
     "全球约$70亿美元，中国年进口约$10亿美元",
     "年增15%", "中国|印度|缅甸|苏丹|尼日利亚",
     "苏丹|坦桑尼亚|尼日利亚|埃塞俄比亚|塞内加尔",
     "坦桑TSB|苏丹SESROC|尼日利亚NSEA",
     "有机认证|NON-GMO",
     "集装箱海运，注意密封防潮；保质期约1年",
     "中国是最大买家|印度竞争|苏丹产量大但物流复杂",
     "芝麻是中国最大非洲进口农产品之一，零关税政策下利润可观，建议重点开发坦桑尼亚有机芝麻",
     "featured"),
    ("植物油", "初榨橄榄油", "Extra Virgin Olive Oil",
     "1509.10", "MA|TN|ET|ZA",
     "食品进口商|超市|电商|礼品渠道",
     "食品标签认证；营养成分检测",
     1, 0.10,
     "全球约$150亿美元，中国约$5亿美元",
     "年增20%", "欧盟|美国|中国|澳大利亚|智利",
     "西班牙|意大利|希腊|摩洛哥|突尼斯",
     "摩洛哥Moulin Khlal|突尼斯CHO|南非Spier",
     "PDO/PGI原产地保护认证|有机认证",
     "海运集装箱，注意避光避温；保质期约2年",
     "欧洲品牌主导|价格透明|消费者认知度高",
     "非洲橄榄油性价比高于欧洲，适合礼品和电商渠道，建议摩洛哥和突尼斯双线进口",
     "featured"),
    ("植物油", "芝麻油", "Sesame Oil",
     "1515.50", "TZ|SN|MZ|ET|GH",
     "食品加工|餐饮|零售",
     "食品添加剂标准",
     1, 0.10,
     "全球约$15亿美元",
     "年增8%", "中国|缅甸|日本|韩国|美国",
     "缅甸|中国|日本|苏丹|坦桑尼亚",
     "坦桑Kakyt|苏丹Sesaco",
     "有机认证",
     "海运集装箱",
     "中国是最大消费国|非洲产量有限",
     "建议进口芝麻原料国内榨油，而非进口成品油",
     "active"),
    ("油籽", "大豆（非转基因）", "Non-GM Soybeans",
     "1201.90", "ZA|ET|TZ|MG|MW",
     "榨油厂|豆腐加工|酱油|食品加工",
     "进口检验检疫；非转基因证明",
     1, 0.09,
     "全球约$500亿美元",
     "年增3%", "中国|欧盟|墨西哥|阿根廷|巴西",
     "巴西|美国|阿根廷|中国|乌克兰",
     "南非Soylux|马达加斯加Ankazobe Coop",
     "非转基因认证|有机认证",
     "散货船运输，注意防潮",
     "中国大豆进口主要来自巴西/美国|非洲非转基因是差异化",
     "非洲非转基因大豆适合高端食品加工，建议探索南非和埃塞俄比亚供应",
     "active"),

    # ============================================================
    # 五、香料与香草 (Spices & Vanilla)
    # ============================================================
    ("香料", "香草豆（Vanilla）", "Vanilla Beans",
     "0905.00", "MG|MU|UG|KE|TZ|ZW",
     "食品香料|香水原料|化妆品|礼品",
     "进口检验检疫；濒危物种证书（如适用）",
     1, 0.15,
     "全球约$10亿美元（香料之王），中国约$5000万美元",
     "年增15-25%", "美国|法国|德国|中国|印度",
     "马达加斯加（全球80%供应）|印度尼西亚|乌干达|印度",
     "马达加斯加SAVA Cooperative|乌干达UVAN",
     "Fairtrade|有机认证|雨林联盟",
     "空运优先（高价值），海运也行，需避光密封；保质期约2年",
     "价格波动极大（2022年一度涨至$600/kg）|马达加斯加产量主导|气候变化",
     "香草是全球最贵香料之一，零关税后利润空间极大，建议锁定乌干达和毛里求斯替代供应商分散风险",
     "featured"),
    ("香料", "丁香（整粒/粉）", "Cloves (Whole/Ground)",
     "0907.00", "MG|TZ|MU|KE|ZW",
     "食品香料|香水原料|制药|口腔护理",
     "进口检验检疫",
     1, 0.08,
     "全球约$8亿美元",
     "年增5%", "印度尼西亚|印度|中国|美国|阿联酋",
     "马达加斯加|坦桑尼亚|印度尼西亚|肯尼亚",
     "坦桑TCB|马达加斯加FTM",
     "有机认证",
     "集装箱海运，注意防潮；保质期约3年",
     "印尼产量大于马达加斯加|价格波动中等",
     "丁香适合食品和香料行业，坦桑尼亚和肯尼亚可作为替代供应源",
     "active"),
    ("香料", "锡兰桂皮（肉桂）", "Ceylon Cinnamon (Cinnamomum zeylanicum)",
     "0906.11|0906.20", "MG|SL|TZ|MU",
     "食品调味|制药|保健品|化妆品",
     "进口检验检疫",
     1, 0.15,
     "全球约$6亿美元",
     "年增8%", "美国|印度|墨西哥|中国|德国",
     "印度尼西亚（主导）|中国|斯里兰卡|马达加斯加",
     "马达加斯加SNC|斯里兰卡Cinnamon Board",
     "有机认证|HACCP",
     "集装箱运输，注意防虫；保质期约3年",
     "印尼和中国锡兰桂皮（国产）竞争|马达加斯加品质高",
     "马达加斯加锡兰桂皮品质优于印尼，适合高端食品和制药用途",
     "active"),
    ("香料", "姜（鲜/干）", "Fresh and Dried Ginger",
     "0910.10", "NG|ET|GH|SL|LR|TZ",
     "食品加工|中药材|调味料|饮料",
     "进口检验检疫；中药材需资质",
     1, 0.15,
     "全球约$4亿美元",
     "年增6%", "印度|中国|尼日利亚|泰国|秘鲁",
     "印度（全球最大）|中国|尼日利亚|泰国",
     "尼日利亚Ginger Farmers Coop",
     "有机认证|NON-GMO",
     "鲜姜走冷链海运；干姜可集装箱运输",
     "印度和中国主导|非洲品质有特色",
     "非洲生姜适合中药材和食品双渠道，建议开发尼日利亚有机认证干姜",
     "active"),
    ("香料", "黑胡椒（整粒/粉）", "Black Pepper (Whole/Ground)",
     "0904.11|0904.12", "TZ|KE|UG|MG|LR",
     "食品加工|调味料|餐饮|零售",
     "进口检验检疫",
     1, 0.20,
     "全球约$8亿美元",
     "年增4%", "印度|越南|中国|美国|印度尼西亚",
     "越南|印度|巴西|印度尼西亚|斯里兰卡",
     "坦桑TZPFA|肯尼亚KPCU",
     "有机认证|HACCP",
     "集装箱运输，注意防潮；保质期约4年",
     "越南主导市场|非洲胡椒品质独特",
     "非洲胡椒以坦桑尼亚和肯尼亚为主，适合食品加工大批量采购",
     "active"),

    # ============================================================
    # 六、茶叶 (Tea)
    # ============================================================
    ("茶叶", "红茶（CTC/orthodox）", "Black Tea (CTC/Orthodox)",
     "0902.40|0902.30", "KE|UG|RW|TZ|MW|MZ|ZM",
     "茶饮品牌|食品加工|超市|电商平台",
     "进口检验检疫；茶叶需出口国官方检验证书",
     1, 0.15,
     "全球约$250亿美元，中国年进口约$3亿美元",
     "年增5%", "巴基斯坦|俄罗斯|土耳其|英国|美国",
     "肯尼亚（全球最大出口国）|斯里兰卡|印度|中国|越南",
     "肯尼亚KTDA|乌干达UTG|卢旺达OCIBU",
     "Rainforest Alliance|有机认证|Fairtrade",
     "集装箱海运，注意防潮；保质期约3年",
     "肯尼亚主导全球红茶出口|价格透明利润薄",
     "非洲红茶适合茶饮品牌大批量采购，零关税后利润空间提升，建议锁定肯尼亚KTDA供应商",
     "featured"),
    ("茶叶", "紫茶（紫娟等）", "Purple Tea",
     "0902.40", "KE|RW|ZA",
     "高端茶饮|保健品|电商平台|礼品",
     "进口检验检疫",
     1, 0.15,
     "全球约$1亿美元",
     "年增25%", "美国|中国|英国|德国|阿联酋",
     "肯尼亚|卢旺达|南非",
     "肯尼亚Purple Tea Factory|卢旺达NPR",
     "有机认证|雨林联盟",
     "高端包装，空运优先",
     "中国高端市场认知度低|产量有限",
     "紫茶花青素含量高，适合健康产品定位，建议从小批量试销开始",
     "active"),

    # ============================================================
    # 七、矿产与金属矿砂 (Minerals & Ores)
    # ============================================================
    ("矿产", "铜矿砂及其精矿", "Copper Ores and Concentrates",
     "2603.00", "ZM|CD|AO|NG|ZA|CM",
     "冶炼厂|金属加工|电线电缆|建筑",
     "进口检验检疫；矿产品需装运前检验证书（CIQ）；价格按金属含量计价",
     1, 0.02,
     "全球约$500亿美元",
     "年增5%", "中国|日本|韩国|德国|印度",
     "智利|秘鲁|澳大利亚|刚果金|赞比亚",
     "赞比亚Konkola|刚果金Glencore|安哥拉SODIMIC",
     "SGS/INTERTEK检测报告",
     "散货船运输，需干燥；按铜含量（Cu%）计价",
     "价格波动大|政治风险（刚果金）|环境问题",
     "赞比亚铜矿品质稳定，是中国的长期供应商，建议建立长期合同关系",
     "featured"),
    ("矿产", "钴矿砂及其精矿", "Cobalt Ores and Concentrates",
     "2605.00", "CD|ZA|CM|AO",
     "电池制造|新能源|合金材料|航空航天",
     "进口检验检疫；危化品运输证明；钴是战略资源",
     1, 0.02,
     "全球约$150亿美元（中国市场约$50亿）",
     "年增30%", "中国|芬兰|韩国|日本|美国",
     "刚果金（全球约70%）|澳大利亚|古巴|俄罗斯",
     "刚果金Glencore|嘉能可|洛阳钼业",
     "SGS检测报告|ISO认证",
     "散货船+危化品运输，注意安全储存",
     "全球新能源需求爆发|刚果金主导|供应链集中风险",
     "钴是锂电池核心原料，战略价值极高，建议与赞比亚和南非建立多元化供应源",
     "featured"),
    ("矿产", "锰矿砂及其精矿", "Manganese Ores and Concentrates",
     "2602.00", "ZA|GA|BJ|GH|CM|MZ",
     "钢铁冶炼|锰合金|电池|化学品",
     "进口检验检疫；按锰含量（Mn%）计价",
     1, 0.02,
     "全球约$100亿美元",
     "年增5%", "中国|印度|日本|韩国|俄罗斯",
     "南非|澳大利亚|加蓬|巴西|加纳",
     "南非South32|加蓬Comilog|加纳GMD",
     "SGS/INTERTEK检测报告",
     "散货船运输，注意分层分堆",
     "南非主导|钢铁行业周期影响大",
     "南非锰矿品位高（Mn>44%），供应稳定，适合钢铁厂和锰系电池材料双渠道",
     "featured"),
    ("矿产", "铝土矿（氧化铝原料）", "Bauxite (Aluminium Ore)",
     "2606.00", "GA|CM|AO|ZA|GH|CI|MZ",
     "氧化铝厂|电解铝|建材",
     "进口检验检疫；按铝含量计价",
     1, 0.02,
     "全球约$80亿美元",
     "年增4%", "中国|澳大利亚|巴西|几内亚|印度",
     "澳大利亚|几内亚|巴西|中国|印度",
     "加蓬Comilog|喀麦隆ALUCAM|安哥拉FERRAL",
     "SGS检测报告",
     "散货船运输，大批量",
     "澳大利亚主导|几内亚新兴",
     "加蓬铝土矿品质优良，是氧化铝厂的优质原料，建议开发",
     "active"),
    ("矿产", "铁矿砂（Fe≥62%）", "Iron Ore (Fe>=62%)",
     "2601.11", "ZA|BJ|ZA|MZ|UG|TZ",
     "钢铁冶炼|建筑|基础设施",
     "进口检验检疫；按铁含量（Fe%）计价",
     1, 0.02,
     "全球约$2500亿美元",
     "年增3%", "中国（日本最大买家）|印度|韩国|日本|德国",
     "澳大利亚|巴西|中国|印度|俄罗斯",
     "南非Kumba|南非Assmang",
     "SGS/INTERTEK检测报告",
     "散货船运输，大批量（cape级船型）",
     "澳大利亚和巴西主导|南非品位略低但稳定",
     "南非铁矿是澳洲和巴西以外的优质替代来源，适合分散供应风险",
     "active"),
    ("矿产", "祖母绿/彩色宝石", "Emeralds and Colored Gemstones",
     "7103.91|7103.99", "ZM|ZA|KE|TZ|MG|ET",
     "珠宝品牌|奢侈品|收藏投资|电商",
     "进口检验检疫；珠宝鉴定证书；濒危物种证书（如适用）",
     1, 0.03,
     "彩色宝石全球约$500亿美元，中国约$50亿",
     "年增10%", "中国|美国|瑞士|英国|迪拜",
     "哥伦比亚|赞比亚（全球最大祖母绿产国）|巴西|斯里兰卡",
     "赞比亚Kagem|南非BERYLCO|肯尼亚Tysons",
     "GRS/GIA/AGL宝石鉴定证书",
     "空运为主，高价值需投保；小批量",
     "哥伦比亚祖母绿价格远高于赞比亚|赝品风险|鉴定复杂",
     "赞比亚祖母绿是全球最大供应国，零关税后进口成本降低，适合珠宝品牌开发非洲彩宝线",
     "featured"),

    # ============================================================
    # 八、皮革与动物产品 (Leather & Animal Products)
    # ============================================================
    ("皮革", "牛皮（生皮）", "Raw Bovine Hides",
     "4101.20|4101.50", "ET|KE|TZ|ZA|EG|BJ|SD|AO|SN",
     "制革厂|皮革加工|鞋材|箱包皮具",
     "进口检验检疫；冷冻或盐湿保存运输",
     1, 0.05,
     "全球约$50亿美元",
     "年增3%", "中国|意大利|韩国|越南|巴西",
     "美国|巴西|阿根廷|埃塞俄比亚|肯尼亚",
     "埃塞Exposed Hides|肯尼亚KMC|南非RED",
     "TRACEABILITY追溯体系",
     "盐湿皮走冷藏集装箱；干皮可普通集装箱",
     "环保要求提高|美国和巴西竞争",
     "非洲牛皮价格有竞争力，建议从埃塞俄比亚和肯尼亚进口盐湿皮国内制革",
     "active"),
    ("皮革", "爬行动物皮（鳄鱼/蜥蜴）", "Reptile Leathers (Crocodile/Lizard)",
     "4103.20|4106.40", "ZA|TZ|MU|KE|MG",
     "奢侈品|高端箱包|手表表带|皮鞋",
     "进口检验检疫；CITES濒危物种许可证",
     1, 0.10,
     "全球约$20亿美元",
     "年增8%", "法国|意大利|中国|美国|瑞士",
     "泰国|新加坡|澳大利亚|南非|津巴布韦",
     "南非CrocodileKings|毛里求斯MCSA",
     "CITES证书|SGS原产地证明",
     "空运为主，高价值；需特殊包装",
     "CITES许可复杂|泰国和澳大利亚主导",
     "非洲鳄鱼皮品质优良，适合高端定制皮具，建议从南非和毛里求斯进口",
     "active"),

    # ============================================================
    # 九、棉麻纤维 (Cotton & Natural Fibers)
    # ============================================================
    ("棉麻", "长绒棉（吉扎棉等）", "Extra Long Staple Cotton (ELS)",
     "5201.00|5203.00", "EG|SU|ZA|TZ|KE|BJ",
     "纺织厂|棉纱线|高端面料|家纺",
     "进口检验检疫；棉花需品质证书（HVI检测）",
     1, 0.01,
     "全球约$200亿美元",
     "年增3%", "中国|孟加拉|越南|土耳其|印度",
     "印度|美国|巴西|巴基斯坦|埃及",
     "埃及Cotton Egypt|苏丹Sudacot|南非Cotton SA",
     "BCI认证（良好棉花倡议）|有机认证",
     "集装箱海运，注意防潮；按HVI指标定价",
     "中国国内棉花产量下降|印度和美国主导",
     "埃及长绒棉品质全球第一，适合高端纺织，建议开发埃及苏丹供应商",
     "featured"),
    ("棉麻", "亚麻纤维", "Flax Fibers",
     "5301.21|5301.29", "ET|ZA|RW|BJ",
     "纺织厂|亚麻面料|家纺|复合材料",
     "进口检验检疫",
     1, 0.05,
     "全球约$10亿美元",
     "年增4%", "中国|印度|欧盟|美国|孟加拉",
     "法国|比利时|中国|俄罗斯|埃及",
     "埃塞俄比亚EFL|南非Flax SA",
     "有机认证|ISO认证",
     "集装箱运输，注意防火防潮",
     "欧洲主导|非洲产量有限",
     "建议亚麻纤维配合长绒棉一起进口，增加产品多样性",
     "active"),

    # ============================================================
    # 十、食品与特色农产品 (Food & Specialty Products)
    # ============================================================
    ("食品", "干海参（刺参等）", "Dried Sea Cucumber (Holothurian)",
     "0308.19", "TZ|KE|MZ|MU|ZA|DJ|SC|MW",
     "高端餐饮|礼品|保健品|电商平台",
     "进口检验检疫；CITES许可证（如适用）",
     1, 0.07,
     "全球约$10亿美元",
     "年增10%", "中国|香港|台湾|新加坡|马来西亚",
     "马达加斯加|坦桑尼亚|肯尼亚|莫桑比克|毛里求斯",
     "坦桑SeaFarm|肯尼亚KRDC",
     "CITES证书|SGS检测",
     "空运或海运，注意防潮；干品保质期约5年",
     "中国是唯一大市场|非洲是主要供应源|需合法捕捞证",
     "干海参是中国人餐桌顶级食材，非洲沿海国家是主要野生来源，建议坦桑尼亚和肯尼亚双源采购",
     "featured"),
    ("食品", "鱼粉（饲料用）", "Fishmeal (Aquaculture Feed)",
     "2301.20", "MA|MU|TZ|ZA|EG|SN|MZ",
     "水产饲料|畜禽饲料|宠物食品",
     "进口检验检疫；蛋白质含量检测",
     1, 0.05,
     "全球约$80亿美元",
     "年增6%", "中国|越南|印度|印度尼西亚|挪威",
     "秘鲁（全球最大）|智利|泰国|越南|摩洛哥",
     "摩洛哥Fishmeal SA|塞内加尔IFCMD",
     "HACCP认证|NON-GMO",
     "集装箱海运，注意防潮；蛋白质含量≥60%为佳",
     "秘鲁主导|鱼资源减少趋势",
     "摩洛哥鱼粉蛋白质含量高，适合水产饲料，建议作为长期供应源开发",
     "active"),
    ("食品", "蜂蜡", "Beeswax",
     "1521.90|0409.00", "ET|ZA|TZ|KE|MU|GH|BJ|UG",
     "化妆品|蜡烛|食品包装|药品",
     "进口检验检疫；食品级蜂蜡需FDA注册",
     1, 0.08,
     "全球约$6亿美元",
     "年增5%", "中国|美国|德国|法国|日本",
     "埃塞俄比亚|坦桑尼亚|肯尼亚|南非|马达加斯加",
     "埃塞俄比亚EWPA|肯尼亚BKEDA",
     "有机认证|NON-GMO",
     "集装箱运输，注意防熔化（熔点64°C）",
     "天然蜂蜡供不应求|化妆品需求增长快",
     "蜂蜡是化妆品的天然原料，非洲野生蜂蜡无污染，建议从埃塞俄比亚和坦桑尼亚进口",
     "active"),
    ("食品", "阿甘油（Argan Oil）", "Argan Oil",
     "1513.21", "MA",
     "化妆品|护肤品|食品|礼品",
     "进口检验检疫；食品化妆品双重标准",
     1, 0.09,
     "全球约$10亿美元",
     "年增15%",
     "法国|美国|摩洛哥|中国|阿联酋",
     "摩洛哥（全球唯一产地）",
     "摩洛哥合作社Argan-oil.co.ma|Gold Argan MA",
     "摩洛哥ONSSA认证|有机认证|PDO",
     "瓶装空运或海运集装箱，注意避光",
     "摩洛哥垄断|价格高|UNESCO认定非遗|仿冒品多",
     "阿甘油是全球最珍贵植物油，UNESCO认定为非物质文化遗产，建议开发摩洛哥直接供应商，避开中间商",
     "featured"),
    ("食品", "椰子油（初榨）", "Virgin Coconut Oil",
     "1513.11", "MU|TZ|KE|MG|MZ|SL",
     "化妆品|食品加工|保健品|天然清洁剂",
     "进口检验检疫",
     1, 0.09,
     "全球约$5亿美元",
     "年增12%", "美国|菲律宾|中国|印尼|斯里兰卡",
     "菲律宾（全球最大）|印尼|斯里兰卡|印度|马达加斯加",
     "毛里求斯CocoTech|坦桑East Africa Coconut",
     "有机认证|HACCP",
     "桶装集装箱运输，注意避光；保质期约2年",
     "菲律宾主导|非洲品质有特色",
     "毛里求斯椰子油品质优良，适合化妆品和食品双渠道，建议作为差异化产品推广",
     "active"),
    ("食品", "依兰依兰精油", "Ylang-Ylang Essential Oil",
     "3301.29", "MG|MU|RE|SC|KE",
     "香水原料|化妆品|芳疗|芳香疗法",
     "进口检验检疫；植物精油标准",
     1, 0.08,
     "全球约$3亿美元",
     "年增10%", "法国|美国|瑞士|中国|新加坡",
     "科摩罗（全球最大）|马达加斯加|毛里求斯|留尼汪",
     "马达加斯加SAVA Essential|毛里求斯Ylang House",
     "有机认证|ISO 4715",
     "铝桶或玻璃瓶空运，注意密封避光",
     "科摩罗垄断|马达加斯加品质高",
     "依兰依兰是顶级香水原料，建议从马达加斯加进口有机认证产品，定位高端芳疗市场",
     "active"),
    ("食品", "猴面包树果（Baobab）", "Baobab Fruit Powder",
     "1211.90|1302.19", "TZ|KE|ZA|MU|MW|MZ|BJ",
     "保健品|功能性食品|饮料|化妆品",
     "进口检验检疫；食品添加剂标准",
     1, 0.08,
     "全球约$2亿美元",
     "年增20%", "美国|德国|中国|英国|法国",
     "坦桑尼亚|肯尼亚|南非|莫桑比克|加纳",
     "坦桑Baobafam|肯尼亚APAF",
     "有机认证|NON-GMO|Fairtrade",
     "粉末状，袋装集装箱运输；保质期约3年",
     "超超级食物概念|新兴市场|消费者教育成本",
     "猴面包树果被欧美追捧为'超级食物'，维生素C含量极高，建议从坦桑尼亚和肯尼亚进口有机认证猴面包树果粉",
     "featured"),
    ("食品", "芒果干/菠萝干", "Dried Mango/Pineapple",
     "0803.10|0804.20|0812.10", "TZ|ZA|MU|MG|GH|ET|KE",
     "零食品牌|食品加工|超市|电商平台",
     "进口检验检疫；食品添加剂标准",
     1, 0.10,
     "全球约$10亿美元",
     "年增8%", "中国|美国|德国|法国|英国",
     "菲律宾（芒果干主导）|泰国|墨西哥|秘鲁",
     "坦桑Green Valley|南非FruitCo|马达加斯加DriedEx",
     "有机认证|HACCP|NON-GMO",
     "集装箱运输，注意防潮；真空包装可延长保质期",
     "菲律宾芒果干主导|非洲品质有特色",
     "非洲芒果和菠萝无污染、口感独特，适合电商零食渠道，建议开发坦桑尼亚和南非供应商",
     "active"),

    # ============================================================
    # 十一、木材与林产品 (Wood & Forest Products)
    # ============================================================
    ("木材", "热带硬木原木（红木/桃花心木）", "Tropical Hardwood Logs",
     "4403.41|4403.49", "AO|MZ|GA|ZA|CM|CD|GH|TZ|MU",
     "家具制造|地板|建筑|乐器",
     "进口检验检疫；CITES许可证（如珍贵树种）；原木合法性证明",
     1, 0.01,
     "全球约$200亿美元",
     "年增3%", "中国|美国|日本|韩国|德国",
     "马来西亚|加蓬|喀麦隆|印度尼西亚|巴西",
     "加蓬Rougier|安哥拉SODIAM|莫桑比克MADE",
     "FSC森林认证|CITES证书",
     "散货船运输，注意防水防虫",
     "非法采伐风险|环保压力|巴西和印尼竞争",
     "非洲热带硬木适合高端家具，建议选择FSC认证供应商，合规进口",
     "active"),
    ("木材", "奥库姆胶合板（Okoume Plywood）", "Okoume Plywood",
     "4412.31", "GA|CM|MZ|GQ",
     "建材|家具|包装|船舶制造",
     "进口检验检疫；甲醛释放量检测",
     1, 0.08,
     "全球约$50亿美元",
     "年增4%", "中国|美国|欧盟|日本|韩国",
     "加蓬|喀麦隆|刚果共和国",
     "加蓬Setrag|喀麦隆Camsu",
     "CE认证|FSC认证",
     "集装箱运输，注意防潮",
     "中国是最大进口国|欧洲环保标准高",
     "奥库姆木是轻质胶合板材料，适合建材和家具制造，建议加蓬FOB直采",
     "active"),

    # ============================================================
    # 十二、天然橡胶 (Natural Rubber)
    # ============================================================
    ("橡胶", "天然橡胶（烟胶片/RSS）", "Natural Rubber (RSS/TSNR)",
     "4001.21|4001.22", "CI|GH|LR|NG|CM|TG|MZ|ET",
     "轮胎制造|乳胶制品|医疗器械|日用品",
     "进口检验检疫；按橡胶含量（干胶含量DRC计价）",
     1, 0.10,
     "全球约$350亿美元",
     "年增6%", "中国|印度|泰国|马来西亚|印度尼西亚",
     "泰国|印度尼西亚|越南|马来西亚|科特迪瓦",
     "科特迪瓦SIR|加纳GREL|利比里亚Firestone",
     "ISO 2000|可持续橡胶认证",
     "集装箱或散货运输，注意防氧化；保质期约5年",
     "泰国主导|价格波动大|气候变化影响",
     "科特迪瓦已成为全球第四大橡胶生产国，天然橡胶是轮胎和乳胶制品的核心原料，建议锁定长期供应合同",
     "featured"),
    ("橡胶", "天然乳胶（橡胶树汁）", "Natural Rubber Latex",
     "4001.10", "CI|GH|LR|NG|MZ|TG|SL",
     "乳胶手套|避孕套|床垫|医疗用品",
     "进口检验检疫；按干胶含量（DRC≥60%）计价",
     1, 0.10,
     "全球约$80亿美元",
     "年增8%", "马来西亚|中国|泰国|印度尼西亚|越南",
     "泰国|马来西亚|印度尼西亚|越南|科特迪瓦",
     "科特迪瓦LATEX CI|加纳GPL",
     "ISO 2004|有机认证",
     "桶装冷链运输，防凝固；保质期约2周（需加氨保存）",
     "马来西亚主导乳胶市场|非洲产量增长快",
     "非洲天然乳胶无污染，适合医疗和婴童用品，建议开发科特迪瓦供应商",
     "active"),

    # ============================================================
    # 十三、蔗糖与特殊糖 (Sugar & Specialty Sweeteners)
    # ============================================================
    ("食品", "蔗糖/红糖（有机认证）", "Organic Cane Sugar / Sucrose",
     "1701.13|1701.14|1701.99", "MU|ZA|ET|SZ|TZ|KE",
     "食品加工|饮料|烘焙|电商零售",
     "进口检验检疫；配额许可证；原糖需精炼",
     1, 0.50,
     "全球约$150亿美元",
     "年增3%", "印度|巴西|泰国|澳大利亚|危地马拉",
     "巴西（全球最大）|泰国|印度|澳大利亚",
     "毛里求斯SunSugar|南非Grobank|斯威士兰SSCU",
     "Fairtrade|有机认证|NON-GMO",
     "散货船或集装箱运输",
     "全球糖价受补贴政策影响大|配额制度复杂",
     "蔗糖关税50%较高，建议重点进口有机认证和特殊品种糖（红糖/椰子糖等），定位高端食品加工",
     "active"),
    ("食品", "椰子糖", "Coconut Sugar / Palm Sugar",
     "1702.60|0410.00", "MU|SL|TZ|MG",
     "食品加工|烘焙|饮料|有机零售",
     "进口检验检疫",
     1, 0.10,
     "全球约$2亿美元",
     "年增15%", "美国|德国|中国|荷兰|英国",
     "菲律宾|印度尼西亚|斯里兰卡|泰国",
     "毛里求斯Coconut Sugar Co.",
     "有机认证|Fairtrade",
     "瓶装或袋装集装箱运输",
     "健康糖概念|市场规模小众",
     "椰子糖作为健康糖品种，适合有机食品渠道，建议小批量试销",
     "active"),
]


# ─── Seed data: Supplier database (Phase 2 - Expanded) ────────────────────────
# 覆盖 30+ 非洲国家，70+ 品类的高质量供应商
# (name_zh, name_en, country, region, products, hs_codes, contact_email, min_kg, payment, export_years, verified_chamber, status, intro)
SUPPLIERS_SEED = [
    # ========== 埃塞俄比亚 - 咖啡 ==========
    ("耶加雪菲咖啡出口商合作社","Yirgacheffe Coffee Farmers Cooperative Union","ET","Yirgacheffe, Gedeo Zone","水洗咖啡豆|日晒咖啡豆|耶加雪菲产区生豆","0901.11","export@yirgacheffe-coffee.et",500,"L/C, T/T",4,1,"verified","埃塞俄比亚耶加雪菲产区最大合作社之一，专注精品水洗豆，年出口量约300吨，主要市场日本、欧美，近年开拓中国市场。"),
    ("科契尔产区咖啡公司","Kochere Coffee Producer Company","ET","Kochere, SNNPR","科契尔水洗豆|精品咖啡|有机认证咖啡","0901.11","info@kochere-coffee.et",200,"T/T, L/C",3,1,"verified","位于耶加雪菲产区南部科契尔区，专注高海拔精品豆，有机认证，适合高端电商渠道。"),
    ("西达摩产区出口商","Sidama Coffee Farmers Cooperative","ET","Sidama Zone, Hawassa","西达摩水洗豆|日晒耶加|拼配咖啡豆","0901.11","sales@sidama-coffee.et",1000,"L/C, T/T",2,1,"verified","西达摩是埃塞俄比亚最重要的咖啡产区之一，产量大、品质稳定，适合电商大批量采购。"),
    ("古吉产区精品咖啡出口","Guji Zone Specialty Coffee Exporters","ET","Guji Zone, Oromia","古吉精品咖啡|日晒豆|水洗豆","0901.11","export@guji-coffee.et",300,"T/T",2,1,"verified","古吉是埃塞新兴精品咖啡产区，以其独特的果香和复杂风味著称，适合精品咖啡烘焙商。"),
    ("利姆产区咖啡合作社","Limu Coffee Farmers Union","ET","Limu, Oromia","利姆水洗豆|有机咖啡|精品咖啡","0901.11","info@limu-coffee.et",250,"T/T, L/C",3,1,"verified","利姆产区以生产高品质水洗咖啡闻名，口感平衡，酸度适中，适合意式拼配。"),
    # ========== 肯尼亚 - 咖啡、坚果 ==========
    ("肯尼亚咖啡委员会出口部","Kenya Coffee Directorate Export Division","KE","Nairobi, Central Province","肯尼亚AA|AB级咖啡|水洗咖啡豆","0901.11","exports@coffeeboard.or.ke",500,"L/C",5,1,"verified","肯尼亚官方咖啡机构代理，负责品质检验和出口协调，AA级豆享誉全球。"),
    ("蒙巴萨坚果与农产品出口公司","Mombasa Nuts & Agricultural Exports Ltd","KE","Mombasa, Coast Province","腰果|去壳腰果|烘焙腰果","0801.32","exports@mombasa-nuts.co.ke",1000,"T/T",5,1,"verified","肯尼亚蒙巴萨最大的腰果出口商之一，和西非竞争有地理优势，适合食品加工企业采购。"),
    ("肯尼亚山咖啡出口公司","Kenya Highlands Coffee Exporters Ltd","KE","Nyeri, Mount Kenya Region","肯尼亚AA|特级水洗豆|Nyeri产区","0901.11","sales@kenyahighlands.co.ke",200,"T/T, L/C",4,1,"verified","位于肯尼亚山脚下Nyyeri产区，以其明亮的果酸和复杂风味著称，是拍卖市场上最抢手的咖啡。"),
    ("肯尼亚芝麻与油籽出口公司","Kenya Sesame & Oilseeds Export Ltd","KE","Kisumu, Western Kenya","白芝麻|黑芝麻|花生","1207.40","info@kenya-sesame.co.ke",5000,"T/T",3,1,"verified","肯尼亚西部是优质芝麻产区，适合有机认证产品出口，中国市场需求旺盛。"),
    # ========== 坦桑尼亚 - 芝麻、咖啡、腰果 ==========
    ("坦桑尼亚芝麻出口公司","Tanzania Sesame Exports Co.","TZ","Shinyanga Region","白芝麻|黑芝麻|有机芝麻","1207.40","info@tz-sesame.co.tz",5000,"T/T, L/C",3,1,"verified","坦桑尼亚是全球最大芝麻生产国之一，年产约12万吨，该公司专注有机认证芝麻，主要出口中国和印度。"),
    ("乞力马扎罗咖啡出口公司","Kilimanjaro Coffee Exporters","TZ","Kilimanjaro Region, Moshi","乞力马扎罗咖啡|水洗AA|有机咖啡","0901.11","export@kilicafe.co.tz",300,"T/T, L/C",4,1,"verified","坦桑尼亚乞力马扎罗山产区咖啡，以其独特的巧克力和果香风味著称，适合高端烘焙商。"),
    ("坦桑尼亚腰果出口协会","Tanzania Cashew nut Exporters Association","TZ","Mtwara Region","带壳腰果|去壳腰果|RW500级","0801.31","exports@tanzania-cashew.or.tz",10000,"L/C",5,1,"verified","坦桑尼亚是东非最大腰果生产国，RW500是国际优质等级，适合食品加工和零食品牌。"),
    ("坦桑尼亚丁香与香料出口","Tanzania Cloves & Spices Export Ltd","TZ","Zanzibar, Pemba","丁香|肉豆蔻|黑胡椒","0907.00","spices@zanzibar.co.tz",500,"T/T",3,1,"verified","桑给巴尔是世界著名丁香产地，品质优良，适合食品香料和精油行业。"),
    # ========== 加纳 - 可可 ==========
    ("加纳可可与巧克力出口公司","Ghana Cocoa & Chocolate Exporters Ltd","GH","Ashanti Region, Kumasi","可可豆|可可脂|可可液块","1801.00, 1803.10, 1804.00","export@ghana-cocoa.gh",2000,"L/C, T/T",6,1,"verified","加纳是全球第二大可可生产国，该公司直接与可可局合作，保证品质和溯源，适合巧克力工厂采购。"),
    ("加纳可可局认证出口商","Cocobod Licensed Exporters Ghana Ltd","GH","Accra, Greater Accra","优质可可豆|有机可可|Fairtrade认证可可","1801.00","premium@cocobod-ghana.com",1000,"L/C",8,1,"verified","加纳可可局直属出口商，提供经过严格分级的优质可可豆，品质稳定可靠。"),
    # ========== 科特迪瓦 - 可可 ==========
    ("科特迪瓦可可出口集团","Côte d'Ivoire Cocoa Export Group","CI","Abidjan, Soubré","可可豆|可可饼|可可粉","1801.00, 1805.00","ventes@civ-cocoa.ci",3000,"L/C",4,1,"verified","科特迪瓦是全球最大可可生产国，该公司供应各等级可可豆，价格有竞争力，适合大宗采购。"),
    ("科特迪瓦可可质量认证公司","Côte d'Ivoire Quality Cocoa S.A.","CI","San-Pédro, Bas-Sassandra","出口级可可豆|有机认证可可|雨林联盟认证","1801.00","quality@ci-cocoa.ci",2000,"L/C",3,1,"verified","位于科特迪瓦最大可可产区San-Pédro，提供多种认证等级可可，专注可持续种植。"),
    ("科特迪瓦热带木材出口公司","Côte d'Ivoire Tropical Timber Exporters","CI","San-Pédro, Bas-Sassandra","热带硬木|桃花心木|非洲紫檀","4403.49","export@ci-timber.ci",1000,"L/C",5,1,"verified","科特迪瓦林业资源丰富，适合家具、地板和建筑材料行业。"),
    # ========== 南非 - 矿业、农产品 ==========
    ("南非矿业出口公司","South Africa Minerals & Mining Export (Pty) Ltd","ZA","Johannesburg, Northern Cape","锰矿精矿|铁矿砂|铬矿","2602.00, 2603.00, 2610.00","exports@sa-minerals.co.za",100000,"L/C",10,1,"verified","南非最大矿业出口商之一，专业出口各类金属矿砂，有完善的检测报告体系（SGS/INTERTEK），适合钢铁厂和冶炼厂。"),
    ("南非苹果与梨出口公司","South Africa Apples & Pears Export (Pty) Ltd","ZA","Stellenbosch, Western Cape","富士苹果|嘎啦苹果|梨","0808.10, 0808.30","export@sa-apples.co.za",10000,"L/C",7,1,"verified","南非是南半球重要苹果出口国，产季与中国互补，适合中国反季节水果贸易。"),
    ("南非葡萄酒出口集团","South Africa Wine Export Group","ZA","Stellenbosch, Cape Winelands","红葡萄酒|白葡萄酒|起泡酒","2204.21","exports@sawine.co.za",500,"L/C, T/T",5,1,"verified","南非葡萄酒性价比高，在国际市场增长迅速，适合进口商和经销商采购。"),
    ("南非柑橘出口公司","South Africa Citrus Exporters (Pty) Ltd","ZA","Patensie, Eastern Cape","橙子|柠檬|葡萄柚|橘子","0805.10, 0805.50, 0805.40","citrus@sa-citrus.co.za",20000,"L/C",6,1,"verified","南非是全球重要柑橘出口国，产季与中国互补，冷链物流体系成熟。"),
    # ========== 摩洛哥 - 橄榄油、坚果 ==========
    ("摩洛哥橄榄油与坚果出口公司","Morocco Olive Oil & Nuts Export SARL","MA","Meknes, Fes-Meknes","初榨橄榄油|去壳榛子|杏仁","1509.10, 0802.22","export@ma-olive-nuts.ma",500,"T/T, L/C",3,1,"verified","摩洛哥是全球最大橄榄油生产国之一，该公司同时出口优质坚果，适合食品电商和礼品渠道。"),
    ("摩洛哥阿甘油出口公司","Morocco Argan Oil Export Co.","MA","Essaouira, Marrakech-Safi","阿甘油|阿甘坚果|有机阿甘油","1513.21","export@arganoil.ma",100,"T/T",4,1,"verified","摩洛哥阿甘油是全球最珍贵的植物油之一，UNESCO认证的非物质文化遗产，适合美妆和食品行业。"),
    ("摩洛哥沙丁鱼罐头出口","Morocco Sardine Canning & Export SA","MA","Agadir, Souss-Massa","沙丁鱼罐头|金枪鱼罐头|腌制鱼","1604.14","export@ma-fish.ma",5000,"L/C",6,1,"verified","摩洛哥是全球最大沙丁鱼罐头出口国，品质符合欧盟标准，中国市场进口量稳步增长。"),
    # ========== 埃及 - 棉纤维、柑橘 ==========
    ("埃及棉纤维出口公司","Egyptian Cotton & Fiber Export Co.","EG","Alexandria, Beheira Governorate","长绒棉|棉纤维|纱线","5201.00, 5203.00","trade@eg-cotton.com.eg",10000,"L/C",8,1,"verified","埃及吉扎棉是全球最优质棉花之一，该公司直接与棉农合作，提供溯源证明，适合纺织企业。"),
    ("埃及柑橘与石榴出口公司","Egyptian Citrus & Pomegranate Export S.A.E","EG","Ismailia, Sharqia","橙子|葡萄柚|石榴|柠檬","0805.10, 0805.40","exports@eg-citrus.com.eg",10000,"L/C",5,1,"verified","埃及是全球重要柑橘出口国，纳赛尔地区产优质橙子，适合中国进口商。"),
    # ========== 卢旺达 - 茶叶、咖啡 ==========
    ("卢旺达高地茶出口公司","Rwanda Highlands Tea Exporters","RW","Ruhengeri, Northern Province","红茶|绿茶|紫茶","0902.40","sales@rwanda-tea.rw",500,"T/T",2,1,"verified","卢旺达高山茶以花香和果香著称，在欧美高端市场有口碑，适合精品茶电商和礼品采购。"),
    ("卢旺达精品咖啡出口","Rwanda Specialty Coffee Exporters Ltd","RW","Huye, Southern Province","Bourbon咖啡豆|水洗咖啡|有机认证","0901.11","export@rwanda-coffee.rw",200,"T/T, L/C",3,1,"verified","卢旺达Bourbon咖啡豆品质卓越，以其明亮的酸度和复杂果香闻名，是精品咖啡新宠。"),
    # ========== 马达加斯加 - 香草、香料 ==========
    ("马达加斯加香草出口商","Madagascar Vanilla & Spices Export SARL","MG","Sava Region, Toamasina","香草豆|丁香|依兰依兰精油","0905.00, 0907.00, 3301.29","export@mg-vanilla.mg",100,"T/T, L/C",5,1,"verified","马达加斯加供应全球约80%的香草，该公司位于香草主产区萨瓦区，提供有机认证香草，适合食品和香水行业。"),
    ("马达加斯加依兰精油出口","Madagascar Ylang-Ylang Essential Oil Export","MG","Nosy Be, Diana Region","依兰依兰精油|香草精油|丁香油","3301.29","export@mg-ylang.mg",50,"T/T",4,1,"verified","马达加斯加是世界顶级依兰依兰精油产地，品质卓越，适合香水和芳疗行业。"),
    ("马达加斯加桂皮出口公司","Madagascar Cinnamon Export SARL","MG","Sambava, Sava","锡兰桂皮|桂皮粉|桂皮油","0906.11, 0906.20","cinnamon@mg-spice.mg",500,"T/T",3,1,"verified","马达加斯加锡兰桂皮品质上乘，香气浓郁，适合食品调味和保健品行业。"),
    # ========== 毛里求斯 - 蔗糖 ==========
    ("毛里求斯蔗糖出口公司","Mauritius Sugar Export Corporation","MU","Port Louis, Moka","有机蔗糖|红糖|糖浆","1701.13, 1701.14","trade@mu-sugar.mu",5000,"L/C, T/T",7,1,"verified","毛里求斯甘蔗种植历史悠久，有机蔗糖在欧美市场有稳定需求，适合食品加工和零售电商。"),
    # ========== 塞内加尔 - 花生、鱼粉 ==========
    ("塞内加尔花生出口合作社","Senegal Groundnut Export Cooperative","SN","Kaolack, Fatick","花生|花生油|花生酱原料","1202.30, 1508.10","coop@sn-groundnut.sn",10000,"T/T",3,1,"verified","塞内加尔是西非最大花生生产国，该公司直接与合作社对接，价格竞争力强，适合榨油和食品加工。"),
    ("塞内加尔鱼粉出口公司","Senegal Fishmeal Export Co.","SN","Saint-Louis, Northern Senegal","鱼粉|鱼油|海藻粉","2301.20","export@sn-fishmeal.sn",5000,"L/C",4,1,"verified","塞内加尔海域渔业资源丰富，鱼粉品质优良，适合水产饲料行业。"),
    # ========== 乌干达 - 咖啡、茶叶 ==========
    ("乌干达咖啡出口公司","Uganda Coffee Export Company Ltd","UG","Kampala, Bugisu Region","阿拉比卡生豆|罗布斯塔|水洗豆","0901.11","export@ug-coffee.ug",500,"L/C, T/T",4,1,"verified","乌干达咖啡豆品质优良，布吉苏产区咖啡有PDO潜力，适合精品烘焙电商。"),
    ("乌干达西贡茶出口公司","Uganda Tea Exporters Ltd","UG","Jinja, Eastern Uganda","红茶CTC|绿茶|紫茶","0902.40","sales@ug-tea.ug",2000,"L/C",3,1,"verified","乌干达是东非重要茶叶生产国，西贡河谷产优质红茶，适合茶饮品牌。"),
    # ========== 吉布提 - 物流枢纽 ==========
    ("吉布提港口物流与贸易公司","Djibouti Port Trade & Logistics Co.","DJ","Djibouti City, Tadjourah","咖啡物流|芝麻|皮革原料","0901.11, 1207.40, 4101.20","trade@djibouti-port.dj",1000,"T/T",6,1,"verified","吉布提是中国一带一路重要节点，该公司提供从埃塞俄比亚到吉布提港的全套物流清关服务，适合第一次从非洲进口的企业。"),
    # ========== 尼日利亚 - 可可、芝麻 ==========
    ("尼日利亚可可出口公司","Nigeria Cocoa Export Company","NG","Lagos, Cross River State","可可豆|可可脂|可可饼","1801.00, 1804.00","exports@ng-cocoa.ng",5000,"L/C",2,0,"new","尼日利亚非洲最大人口国，可可产量全球第四，该公司近年开始开拓中国市场，提供SGS检测报告。"),
    ("尼日利亚芝麻出口协会","Nigeria Sesame Export Association","NG","Kano, Northern Nigeria","白芝麻|黑芝麻|胡麻","1207.40","export@ng-sesame.ng",5000,"T/T, L/C",2,0,"new","尼日利亚北部是优质芝麻产区，年产量大，该公司开始专注中国市场。"),
    # ========== 赞比亚 - 矿业、宝石 ==========
    ("赞比亚铜带矿业公司","Zambia Copperbelt Mining & Exports Ltd","ZM","Kitwe, Copperbelt Province","铜矿砂|钴矿|锌矿","2603.00, 2605.00, 2608.00","sales@zm-copperbelt.zm",50000,"L/C",8,1,"verified","赞比亚铜带省是全球重要铜矿区，该公司长期向中国出口矿砂，有长期合同经验，适合大型冶炼厂。"),
    ("赞比亚祖母绿出口公司","Zambia Emerald Exporters Ltd","ZM","Kafue, Lusaka Province","祖母绿宝石|紫水晶|海蓝宝","7103.91","gems@zm-emerald.zm",10,"L/C",5,1,"verified","赞比亚是世界顶级祖母绿产地之一，品质可与哥伦比亚媲美，适合珠宝行业。"),
    # ========== 贝宁 - 棉花 ==========
    ("贝宁棉花出口公司","Benin Cotton Exporters SARL","BJ","Cotonou, Borgou","原棉|棉籽|棉纱","5201.00, 5203.00","export@bj-cotton.bj",10000,"T/T, L/C",3,1,"verified","贝宁是西非重要棉花生产国，该公司与法国公司合作管理棉田，质量稳定，适合纺织企业。"),
    # ========== 喀麦隆 - 可可、咖啡 ==========
    ("喀麦隆可可出口公司","Cameroon Cocoa Export SA","CM","Douala, South Region","可可豆|可可脂|可可壳","1801.00, 1804.00","trade@cm-cocoa.cm",2000,"L/C",2,0,"new","喀麦隆可可香气浓郁，适合精品巧克力生产，该公司位于杜阿拉港口城市，物流便利。"),
    ("喀麦隆咖啡出口公司","Cameroon Arabica Coffee Exporters Ltd","CM","Bamenda, Northwest Region","阿拉比卡咖啡|罗布斯塔|有机咖啡","0901.11","export@cm-coffee.cm",300,"T/T, L/C",2,1,"verified","喀麦隆西北产区产优质阿拉比卡，以其独特的巧克力和水果风味著称。"),
    # ========== 莫桑比克 - 腰果、木材 ==========
    ("莫桑比克腰果出口公司","Mozambique Cashew nut Export Ltd","MZ","Nampula, Northern Mozambique","带壳腰果|去壳腰果|RW级","0801.31","export@mz-cashew.mz",5000,"L/C",3,1,"verified","莫桑比克是腰果传统产区，品质优良，适合食品加工和零食品牌。"),
    ("莫桑比克珍贵木材出口","Mozambique Precious Woods Export S.A.","MZ","Beira, Sofala","红木锯材|黑木|桃花心木","4403.49","export@mz-wood.mz",500,"L/C",4,1,"verified","莫桑比克拥有珍贵硬木资源，适合高端家具和乐器制造。"),
    # ========== 加蓬 - 锰矿、木材 ==========
    ("加蓬锰矿出口公司","Gabon Manganese Export Company S.A.","GA","Moanda, Haut-Ogooué","锰矿|锰精矿|锰矿石","2602.00","export@ga-manganese.ga",50000,"L/C",6,1,"verified","加蓬是世界重要锰矿生产国，品位高，适合钢铁冶炼。"),
    ("加蓬奥库姆贝丹木出口","Gabon Okoume Plywood Export SARL","GA","Port-Gentil, Ogooue-Maritime","奥库姆胶合板|红木锯材|MDF板","4412.31","export@ga-plywood.ga",1000,"L/C",4,1,"verified","加蓬奥库姆木是优质胶合板原料，适合建材和家具制造。"),
    # ========== 刚果（金）- 钴矿、铜矿 ==========
    ("刚果民主共和国矿业出口公司","DRC Mining & Exports S.A.","CD","Kolwezi, Lualaba","钴矿|铜矿|钶钽铁矿","2605.00, 2603.00, 2615.90","export@cd-mining.cd",10000,"L/C",8,1,"verified","刚果（金）是全球最大钴生产国，供应全球约70%的钴，适合电池和新能源产业。"),
    # ========== 突尼斯 - 橄榄油、椰枣 ==========
    ("突尼斯顶级橄榄油出口公司","Tunisia Premium Olive Oil Export S.A.","TN","Sfax, Sfax Governorate","特级初榨橄榄油|橄榄油渣|橄榄","1509.10, 1509.90","export@tn-olive.tn",500,"L/C",6,1,"verified","突尼斯是地中海橄榄油重要产区，品质卓越，价格有竞争力。"),
    ("突尼斯椰枣出口公司","Tunisian Dates Export Co.","TN","Tozeur, Nefzaoua","椰枣|椰枣酱|有机椰枣","0804.10","export@tn-dates.tn",1000,"T/T, L/C",5,1,"verified","突尼斯椰枣品质优良，德尔杰尔椰枣享誉世界，适合食品电商和礼品。"),
    # ========== 阿尔及利亚 - 椰枣 ==========
    ("阿尔及利亚椰枣出口公司","Algeria Dates Export Company S.A.","DZ","Biskra, Ziban","椰枣|椰枣干|有机椰枣","0804.10","export@dz-dates.dz",2000,"L/C",4,1,"verified","阿尔及利亚是椰枣主产国，瓦尔扎扎特地区产优质椰枣，适合进口分销。"),
    # ========== 苏丹 - 阿拉伯胶 ==========
    ("苏丹阿拉伯胶出口公司","Sudan Gum Arabic Export Co.","SD","Kordofan, North Kordofan","阿拉伯胶|天然树胶|食品添加剂","1301.20","export@sd-gumarabic.sd",1000,"T/T",5,1,"verified","苏丹供应全球约70%的阿拉伯胶，是食品、饮料和制药行业的重要原料。"),
    # ========== 布隆迪 - 咖啡 ==========
    ("布隆迪精品咖啡出口公司","Burundi Specialty Coffee Exporters S.A.","BI","Kayanza, Kayanza Province","波旁咖啡|水洗咖啡|日晒咖啡","0901.11","export@bi-coffee.bi",200,"T/T, L/C",2,1,"verified","布隆迪咖啡以波旁品种为主，风味复杂，酸度适中，在精品咖啡市场越来越受欢迎。"),
    # ========== 多哥 - 可可、咖啡 ==========
    ("多哥可可与咖啡出口公司","Togo Cocoa & Coffee Export Company S.A.","TG","Lomé, Maritime Region","可可豆|罗布斯塔咖啡|阿拉比卡咖啡","1801.00, 0901.11","export@tg-commodities.tg",2000,"L/C",3,1,"verified","多哥是西非可可和咖啡生产国，该公司专注出口业务，适合大宗采购。"),
    # ========== 塞拉利昂 - 可可 ==========
    ("塞拉利昂可可出口公司","Sierra Leone Cocoa Exporters Ltd","SL","Kenema, Eastern Province","有机可可豆|常规可可豆|Fairtrade认证","1801.00","export@sl-cocoa.sl",1000,"T/T, L/C",2,1,"verified","塞拉利昂可可种植区未受污染，适合有机和公平贸易认证产品。"),
    # ========== 利比里亚 - 橡胶、可可 ==========
    ("利比里亚橡胶与可可出口公司","Liberia Rubber & Cocoa Export Co.","LR","Buchanan, Grand Bassa","天然橡胶|可可豆|棕榈油","4001.22, 1801.00, 1511.10","export@lr-commodities.lr",5000,"L/C",3,1,"verified","利比里亚拥有大片橡胶种植园，物流便利，适合橡胶和可可进口商。"),
    # ========== 纳米比亚 - 葡萄、牛肉 ==========
    ("纳米比亚葡萄出口公司","Namibia Grape Export (Pty) Ltd","NA","Aussenkehr, Karas Region","鲜食葡萄|红提|绿提","0806.10","export@na-grapes.na",1000,"L/C",4,1,"verified","纳米比亚奥兰治蒙德产区葡萄品质优良，产季与中国互补，适合水果进口商。"),
    ("纳米比亚牛肉出口公司","Namibia Beef Export S.A.","NA","Windhoek, Khomas","冷冻牛肉|牛肉罐头|皮革","0202.10, 0202.20","export@na-beef.na",5000,"L/C",5,1,"verified","纳米比亚是非洲唯一批准向中国出口牛肉的国家，品质优良，适合食品进口商。"),
    # ========== 津巴布韦 - 烟草 ==========
    ("津巴布韦烟草出口公司","Zimbabwe Tobacco Export Sales (Pvt) Ltd","ZW","Harare, Mashonaland East","弗吉尼亚烟草|白肋烟|烤烟","2401.20","sales@ztes.co.zw",10000,"L/C",10,1,"verified","津巴布韦是世界重要烟草出口国，弗吉尼亚烟草品质优良，适合烟草企业。"),
    # ========== 博茨瓦纳 - 牛肉 ==========
    ("博茨瓦纳牛肉出口公司","Botswana Beef & Livestock Export Company","BW","Gaborone, South-East District","冷冻牛肉|牛肉干|皮革","0202.10","export@bw-beef.bw",3000,"L/C",4,1,"verified","博茨瓦纳牛肉品质优良，符合国际标准，适合食品加工和零售商。"),
    # ========== 马里 - 棉花、芝麻 ==========
    ("马里棉花与芝麻出口公司","Mali Cotton & Sesame Export S.A.","ML","Bamako, Koulikoro","原棉|白芝麻|花生","5201.00, 1207.40","export@ml-commodities.ml",10000,"T/T, L/C",3,1,"verified","马里是西非重要棉花和芝麻生产国，品质稳定，价格有竞争力。"),
    # ========== 尼日尔 - 洋葱 ==========
    ("尼日尔洋葱出口公司","Niger Onion Export Cooperative","NE","Galmi, Tahoua","紫皮洋葱|白洋葱|脱水洋葱","0703.10","export@ne-onion.ne",5000,"T/T",2,1,"verified","尼日尔加尔米洋葱享誉西非，品质优良，适合蔬菜进口和脱水加工。"),
]


def init_db(db_path: str) -> None:
    """Create tables and seed data if empty. Handles existing DB upgrades."""
    conn = get_db(db_path)
    cursor = conn.cursor()

    # ── Create schema ──────────────────────────────────────────────────────────
    if _is_postgres():
        # PostgreSQL: split by ';' and execute each statement separately
        for stmt in SCHEMA_PG.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                cursor.execute(stmt)
    else:
        cursor.executescript(SCHEMA_SQL)
    conn.commit()

    # ── Migration: add missing columns to existing tables ─────────────────────────
    # PostgreSQL DDL can leave a transaction aborted on error.
    # Strategy: execute each ALTER in its own mini-transaction via ROLLBACK on failure.
    _pg_migrations = [
        # users table migrations
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active INTEGER DEFAULT 1",
        # suppliers table migrations (fix incomplete PG schema)
        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS name_en TEXT",
        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS contact_name TEXT",
        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS contact_phone TEXT",
        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS website TEXT",
        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS annual_export_tons REAL",
        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS verified_实地拜访 INTEGER DEFAULT 0",
        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS verified_sgs INTEGER DEFAULT 0",
        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS rating_avg REAL DEFAULT 0",
        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS review_count INTEGER DEFAULT 0",
        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS certifications TEXT",
        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP",
        # supplier_reviews table migrations (fix incomplete PG schema)
        "ALTER TABLE supplier_reviews ADD COLUMN IF NOT EXISTS user_email TEXT",
        "ALTER TABLE supplier_reviews ADD COLUMN IF NOT EXISTS quality_score REAL",
        "ALTER TABLE supplier_reviews ADD COLUMN IF NOT EXISTS delivery_score REAL",
        "ALTER TABLE supplier_reviews ADD COLUMN IF NOT EXISTS communication_score REAL",
        "ALTER TABLE supplier_reviews ADD COLUMN IF NOT EXISTS is_verified_deal INTEGER DEFAULT 0",
        # Suppliers unique constraint for upsert (preserve manual edits)
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_suppliers_name_country ON suppliers(name_zh, country)",
    ]
    if _is_postgres():
        for alter_sql in _pg_migrations:
            try:
                cursor.execute(alter_sql)
                conn.commit()
            except Exception:
                conn.rollback()
    else:
        for alter_sql in _pg_migrations:
            try:
                cursor.execute(alter_sql)
            except Exception:
                pass

    # ── Helper: insert-or-do-nothing (works for both drivers) ─────────────────
    def upsert_many(table: str, cols: str, values: list, insert_sql: str, update_sql: str = ""):
        """Insert many rows; for PostgreSQL uses ON CONFLICT DO NOTHING."""
        if _is_postgres():
            on_conflict = f"ON CONFLICT DO NOTHING"
            final_sql = _to_pg_sql(insert_sql.replace("VALUES", f"{on_conflict} VALUES", 1))
        else:
            final_sql = insert_sql.replace("INSERT INTO", "INSERT OR IGNORE INTO", 1)
        try:
            cursor.executemany(final_sql, values)
        except Exception:
            pass

    def _to_pg_sql(sql: str) -> str:
        """Convert SQLite-style ? placeholders to PostgreSQL %s."""
        if _is_postgres():
            return sql.replace("?", "%s")
        return sql

    def force_upsert_many(table: str, values: list, insert_sql: str):
        """Delete all then insert. Works for both drivers."""
        try:
            pg_sql = _to_pg_sql(insert_sql)
            cursor.execute(f"DELETE FROM {table}")
            cursor.executemany(pg_sql, values)
        except Exception:
            pass

    def upsert_seed(table: str, values: list, insert_sql: str, id_col: str = "id"):
        """
        Smart upsert for seeding: insert only rows whose unique key doesn't exist.
        Preserves any manual edits to existing records.
        Strategy: INSERT OR IGNORE for SQLite; ON CONFLICT DO NOTHING for PG.
        """
        try:
            if _is_postgres():
                pg_sql = _to_pg_sql(insert_sql)
                on_conflict = "ON CONFLICT DO NOTHING"
                final_sql = pg_sql.replace("INSERT INTO", f"{on_conflict} INTO", 1)
                cursor.executemany(final_sql, values)
            else:
                # SQLite: INSERT OR IGNORE keeps existing rows intact
                final_sql = insert_sql.replace("INSERT INTO", "INSERT OR IGNORE INTO", 1)
                cursor.executemany(final_sql, values)
        except Exception as e:
            print(f"[WARN] upsert_seed skipped for {table}: {e}")

    # ── Seed countries ─────────────────────────────────────────────────────────
    upsert_seed(
        "africa_countries",
        AFRICA_COUNTRIES,
        "INSERT INTO africa_countries (code, name_zh, name_en, in_afcfta, has_epa) VALUES (?, ?, ?, ?, ?)",
    )

    # ── Seed HS codes ──────────────────────────────────────────────────────────
    upsert_seed(
        "hs_codes",
        HS_CODES_SEED,
        "INSERT INTO hs_codes (hs_4, hs_6, hs_8, hs_10, name_zh, name_en, mfn_rate, vat_rate, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    )

    # ── Seed freight routes ────────────────────────────────────────────────────
    upsert_seed(
        "freight_routes",
        FREIGHT_ROUTES_SEED,
        "INSERT INTO freight_routes (origin_country, origin_port, origin_port_zh, dest_port, dest_port_zh, transport_type, cost_min_usd, cost_max_usd, transit_days_min, transit_days_max, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    )

    # ── Seed certificate guides ────────────────────────────────────────────────
    upsert_seed(
        "cert_guides",
        CERT_GUIDES_SEED,
        "INSERT INTO cert_guides (country_code, country_name_zh, cert_type, issuing_authority, issuing_authority_zh, website_url, fee_usd_min, fee_usd_max, days_min, days_max, doc_requirements, step_sequence, api_available, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    )

    # ── Seed market analysis / product selection ──────────────────────────────
    upsert_seed(
        "market_analysis",
        MARKET_ANALYSIS_SEED,
        "INSERT INTO market_analysis (category, product_name_zh, product_name_en, main_hs_codes, origin_countries, target_china_market, import_requirements, zero_tariff_china, tariff_rate, market_size_usd, growth_rate, top_importers, supplier_countries, key_suppliers, certification_needs, logistics_notes, risk_factors, recommendation, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    )

    # ── Seed suppliers ─────────────────────────────────────────────────────────
    upsert_seed(
        "suppliers",
        SUPPLIERS_SEED,
        "INSERT INTO suppliers (name_zh, name_en, country, region, main_products, main_hs_codes, contact_email, min_order_kg, payment_terms, export_years, verified_chamber, status, intro) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    )

    conn.commit()
    conn.close()


# ─── Admin seed ─────────────────────────────────────────────────────────────────
def seed_admin_user(db_path: str) -> None:
    """Create seed admin user if not exists."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (SEED_ADMIN_EMAIL,))
    if cursor.fetchone():
        conn.close()
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """INSERT INTO users (email, password_hash, tier, is_admin, is_active, subscribed_at, expires_at)
           VALUES (?, ?, 'free', 1, 1, ?, NULL)""",
        (SEED_ADMIN_EMAIL, hash_password(SEED_ADMIN_PASSWORD), now)
    )
    conn.commit()
    conn.close()
    print(f"[AfricaZero] Admin seed user created: {SEED_ADMIN_EMAIL} / {SEED_ADMIN_PASSWORD}")

