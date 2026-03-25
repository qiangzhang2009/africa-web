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
    updated_at          TEXT DEFAULT (datetime('now'))
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
    created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
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
    # Coffee (0901)
    # 0901.11.00 MFN=8%, VAT=9% (生豆属农产品，2026增值税法9%档)
    # 0901.21.00 MFN=15%, VAT=13% (已焙炒属加工品)
    ("0901", "0901.11", "0901.11.00", "0901.11.00.00", "咖啡豆，未焙炒，生豆", "Coffee, not roasted", 0.08, 0.09, "咖啡"),
    ("0901", "0901.11", "0901.11.00", "0901.11.00.10", "咖啡豆，未焙炒，非速溶", "Coffee, not roasted, not instant", 0.08, 0.09, "咖啡"),
    ("0901", "0901.22", "0901.22.00", "0901.22.00.00", "咖啡豆，已焙炒", "Coffee, roasted", 0.15, 0.13, "咖啡"),
    ("0901", "0901.11", "0901.11.00", "0901.11.00.90", "咖啡豆，未焙炒，速溶用", "Coffee, not roasted, for instant", 0.08, 0.09, "咖啡"),
    # Cocoa (1801-1806)
    # 1801.00.00 MFN=8%, VAT=13% (可可膏/脂/粉均属加工品)
    ("1801", "1801.00", "1801.00.00", "1801.00.00.00", "可可豆，生或焙炒", "Cocoa beans", 0.08, 0.13, "可可"),
    ("1803", "1803.10", "1803.10.00", "1803.10.00.00", "可可膏，未脱脂", "Cocoa paste, not defatted", 0.10, 0.13, "可可"),
    ("1804", "1804.00", "1804.00.00", "1804.00.00.00", "可可脂、油", "Cocoa butter, fat and oil", 0.20, 0.13, "可可"),
    ("1805", "1805.00", "1805.00.00", "1805.00.00.00", "可可粉，不含糖", "Cocoa powder, unsweetened", 0.15, 0.13, "可可"),
    # Nuts (0801-0802)
    # 腰果/杏仁/榛子 MFN=10%, VAT=9% (坚果属农产品，2026增值税法9%档)
    ("0801", "0801.11", "0801.11.00", "0801.11.00.00", "椰子，干的，未去壳", "Coconuts, dried", 0.12, 0.09, "坚果"),
    ("0801", "0801.12", "0801.12.00", "0801.12.00.00", "椰子，干的，去壳", "Coconuts, dried, shelled", 0.12, 0.09, "坚果"),
    ("0801", "0801.31", "0801.31.00", "0801.31.00.00", "腰果，未去壳", "Cashew nuts, in shell", 0.10, 0.09, "坚果"),
    ("0801", "0801.32", "0801.32.00", "0801.32.00.00", "腰果，去壳", "Cashew nuts, shelled", 0.10, 0.09, "坚果"),
    ("0802", "0802.11", "0802.11.00", "0802.11.00.00", "杏仁，未去壳", "Almonds, in shell", 0.10, 0.09, "坚果"),
    ("0802", "0802.12", "0802.12.00", "0802.12.00.00", "杏仁，去壳", "Almonds, shelled", 0.10, 0.09, "坚果"),
    ("0802", "0802.21", "0802.21.00", "0802.21.00.00", "榛子，未去壳", "Hazelnuts, in shell", 0.12, 0.09, "坚果"),
    ("0802", "0802.22", "0802.22.00", "0802.22.00.00", "榛子，去壳", "Hazelnuts, shelled", 0.12, 0.09, "坚果"),
    # Minerals (2601-2621)
    # 矿砂 MFN=2%, VAT=13% (矿物属非农产品)
    ("2601", "2601.11", "2601.11.00", "2601.11.00.00", "铁矿砂及其精矿，焙烧黄铁矿除外", "Iron ores and concentrates", 0.02, 0.13, "矿产"),
    ("2602", "2602.00", "2602.00.00", "2602.00.00.00", "锰矿砂及其精矿", "Manganese ores and concentrates", 0.02, 0.13, "矿产"),
    ("2603", "2603.00", "2603.00.00", "2603.00.00.00", "铜矿砂及其精矿", "Copper ores and concentrates", 0.02, 0.13, "矿产"),
    ("2604", "2604.00", "2604.00.00", "2604.00.00.00", "镍矿砂及其精矿", "Nickel ores and concentrates", 0.02, 0.13, "矿产"),
    ("2605", "2605.00", "2605.00.00", "2605.00.00.00", "钴矿砂及其精矿", "Cobalt ores and concentrates", 0.02, 0.13, "矿产"),
    ("2606", "2606.00", "2606.00.00", "2606.00.00.00", "铝矿砂及其精矿", "Aluminium ores and concentrates", 0.02, 0.13, "矿产"),
    ("2607", "2607.00", "2607.00.00", "2607.00.00.00", "铅矿砂及其精矿", "Lead ores and concentrates", 0.02, 0.13, "矿产"),
    ("2608", "2608.00", "2608.00.00", "2608.00.00.00", "锌矿砂及其精矿", "Zinc ores and concentrates", 0.02, 0.13, "矿产"),
    ("2609", "2609.00", "2609.00.00", "2609.00.00.00", "锡矿砂及其精矿", "Tin ores and concentrates", 0.02, 0.13, "矿产"),
    # Sesame seeds (1207)
    # 芝麻 MFN=10%, VAT=9% (农产品)
    ("1207", "1207.40", "1207.40.00", "1207.40.00.00", "芝麻种子", "Sesame seeds", 0.10, 0.09, "油籽"),
    # Tea (0902)
    # 茶叶 MFN=15%, VAT=13% (加工茶属加工品)
    ("0902", "0902.40", "0902.40.00", "0902.40.00.00", "茶（红茶及其他），已发酵", "Tea (black tea and other), fermented", 0.15, 0.13, "茶叶"),
    ("0902", "0902.30", "0902.30.00", "0902.30.00.00", "茶（红茶），未发酵，绿茶", "Tea (black), not fermented, green tea", 0.15, 0.13, "茶叶"),
    # Coffee products (2101)
    # 2101.11.00 MFN=12% (2025税则), VAT=13% (速溶属加工食品)
    ("2101", "2101.11", "2101.11.00", "2101.11.00.00", "咖啡浓缩精汁，未浸除咖啡碱", "Coffee extracts, not decaffeinated", 0.12, 0.13, "咖啡"),
    # ─── 非零关税品类（常见搜索词，展示给用户看）─────────────────────────
    # 钢铁/废钢 (72章) — MFN 6-8%，不在零关税范围
    ("7204", "7204.10", "7204.10.00", "7204.10.00.00", "钢铁废碎料", "Ferrous waste and scrap", 0.08, 0.13, "钢铁"),
    ("7204", "7204.49", "7204.49.00", "7204.49.00.00", "其他钢铁废碎料", "Other ferrous waste and scrap", 0.08, 0.13, "钢铁"),
    ("7207", "7207.11", "7207.11.00", "7207.11.00.00", "钢锭或半制成品，非合金钢", "Ingots, non-alloy steel", 0.06, 0.13, "钢铁"),
    ("7208", "7208.10", "7208.10.00", "7208.10.00.00", "热轧铁或非合金钢，卷状，厚度≥600mm", "Hot-rolled iron, width>=600mm", 0.06, 0.13, "钢铁"),
    ("7210", "7210.49", "7210.49.00", "7210.49.00.00", "镀锌钢铁板材", "Galvanized steel plate", 0.06, 0.13, "钢铁"),
    ("7219", "7219.21", "7219.21.00", "7219.21.00.00", "不锈钢热轧板", "Stainless steel, hot-rolled plate", 0.10, 0.13, "钢铁"),
    # 汽车/车辆 (87章) — MFN 10-25%，3C认证门槛高，不在零关税范围
    ("8702", "8702.10", "8702.10.00", "8702.10.00.00", "柴油型客车（≥10座）", "Diesel bus (>=10 seats)", 0.15, 0.13, "汽车"),
    ("8703", "8703.23", "8703.23.00", "8703.23.41.00", "汽油型小客车（1500-3000cc）", "Gasoline car (1500-3000cc)", 0.25, 0.13, "汽车"),
    ("8703", "8703.24", "8703.24.00", "8703.24.00.00", "汽油型小客车（>3000cc）", "Gasoline car (>3000cc)", 0.25, 0.13, "汽车"),
    ("8704", "8704.10", "8704.10.00", "8704.10.00.00", "非公路用货运自卸车", "Dump trucks, off-road", 0.06, 0.13, "汽车"),
    # 手机/电子产品 (85章) — MFN 0-13%，涉及3C认证
    ("8517", "8517.12", "8517.12.00", "8517.12.10.00", "手机（GSM或CDMA制式）", "Mobile phones (GSM/CDMA)", 0.00, 0.13, "电子"),
    ("8517", "8517.12", "8517.12.00", "8517.12.20.00", "智能手机", "Smartphones", 0.00, 0.13, "电子"),
    ("8471", "8471.30", "8471.30.00", "8471.30.00.00", "便携式自动数据处理设备", "Portable ADP machines", 0.00, 0.13, "电子"),
    ("8528", "8528.72", "8528.72.00", "8528.72.00.00", "彩色电视机", "Color TV receivers", 0.15, 0.13, "电子"),
    # 服装/纺织品 (61-62章) — MFN 10-20%，不在零关税范围
    ("6101", "6101.20", "6101.20.00", "6101.20.00.00", "棉制针织男式大衣", "Men's knitted overcoat, cotton", 0.17, 0.13, "服装"),
    ("6201", "6201.12", "6201.12.00", "6201.12.00.00", "棉制男式大衣", "Men's overcoat, cotton", 0.17, 0.13, "服装"),
    ("6203", "6203.42", "6203.42.00", "6203.42.00.00", "棉制男式长裤", "Men's trousers, cotton", 0.17, 0.13, "服装"),
    ("6109", "6109.10", "6109.10.00", "6109.10.00.00", "棉制针织T恤", "Knitted T-shirt, cotton", 0.12, 0.13, "服装"),
    # 塑料 (39章) — MFN 6.5-10%，部分在零关税范围
    ("3901", "3901.10", "3901.10.00", "3901.10.00.00", "初级形态的聚乙烯，比重<0.94", "Polyethylene, primary, density<0.94", 0.065, 0.13, "塑料"),
    ("3901", "3901.20", "3901.20.00", "3901.20.00.00", "初级形态的聚乙烯，比重≥0.94", "Polyethylene, primary, density>=0.94", 0.065, 0.13, "塑料"),
    ("3902", "3902.10", "3902.10.00", "3902.10.00.00", "初级形态的聚丙烯", "Polypropylene, primary", 0.065, 0.13, "塑料"),
    ("3907", "3907.50", "3907.50.00", "3907.50.00.00", "不饱和聚酯树脂", "Unsaturated polyester resin", 0.10, 0.13, "塑料"),
    # 皮革/生皮 (41章) — 部分零关税
    ("4101", "4101.20", "4101.20.00", "4101.20.00.00", "生牛皮（整张）", "Raw hides, bovine, whole", 0.05, 0.09, "皮革"),
    ("4103", "4103.20", "4103.20.00", "4103.20.00.00", "爬行动物生皮", "Raw hides, reptiles", 0.10, 0.09, "皮革"),
    ("4104", "4104.11", "4104.11.00", "4104.11.00.00", "皮革（牛），全粒面未剖层", "Leather, bovine, full grain", 0.08, 0.13, "皮革"),
    # 木材 (44章) — 部分零关税
    ("4403", "4403.41", "4403.41.00", "4403.41.00.00", "热带红木原木", "Tropical hardwood logs", 0.01, 0.13, "木材"),
    ("4403", "4403.49", "4403.49.00", "4403.49.00.00", "其他热带木原木", "Other tropical wood logs", 0.01, 0.13, "木材"),
    ("4407", "4407.10", "4407.10.00", "4407.10.00.00", "经纵锯或纵切的木材", "Wood sawn lengthwise", 0.01, 0.13, "木材"),
    # 香料/香草 (0904-0910)
    ("0904", "0904.11", "0904.11.00", "0904.11.00.00", "胡椒，已磨碎或已研磨", "Pepper, crushed or ground", 0.20, 0.13, "香料"),
    ("0904", "0904.21", "0904.21.00", "0904.21.00.00", "辣椒干，已磨碎或未磨碎", "Dried chilies", 0.20, 0.13, "香料"),
    ("0905", "0905.00", "0905.00.00", "0905.00.00.00", "香草（Vanilla）", "Vanilla", 0.15, 0.13, "香料"),
    ("0910", "0910.10", "0910.10.00", "0910.10.00.00", "姜", "Ginger", 0.15, 0.09, "香料"),
    # 棉纤维 (52章) — 部分零关税
    ("5201", "5201.00", "5201.00.00", "5201.00.00.00", "棉花，未梳化", "Cotton, not carded", 0.01, 0.09, "棉麻"),
    ("5203", "5203.00", "5203.00.00", "5203.00.00.00", "棉花，已梳化", "Cotton, carded", 0.01, 0.09, "棉麻"),
    # 油籽/其他 (12章)
    ("1205", "1205.10", "1205.10.00", "1205.10.00.00", "油菜籽，含油量低", "Rape seeds, low erucic acid", 0.09, 0.09, "油籽"),
    ("1207", "1207.20", "1207.20.00", "1207.20.00.00", "棉籽", "Cotton seeds", 0.09, 0.09, "油籽"),
    ("1207", "1207.50", "1207.50.00", "1207.50.00.00", "芥子籽", "Mustard seeds", 0.09, 0.09, "油籽"),
    # 动物油脂 (15章) — 部分零关税
    ("1502", "1502.10", "1502.10.00", "1502.10.00.00", "牛羊油脂", "Tallow (bovine/sheep)", 0.08, 0.09, "油脂"),
    ("1515", "1515.29", "1515.29.00", "1515.29.00.00", "玉米油及其分离品", "Maize oil fractions", 0.10, 0.09, "油脂"),
    # 天然橡胶 (40章) — MFN 10-20%
    ("4001", "4001.10", "4001.10.00", "4001.10.00.00", "天然胶乳", "Natural rubber latex", 0.10, 0.09, "橡胶"),
    ("4001", "4001.21", "4001.21.00", "4001.21.00.00", "天然橡胶烟胶片", "Natural rubber smoked sheets", 0.10, 0.09, "橡胶"),
    # 鱼虾等水产品 (03章) — MFN 7-12%
    ("0303", "0303.55", "0303.55.00", "0303.55.00.00", "冻墨鱼", "Cuttle fish and squid, frozen", 0.12, 0.09, "水产"),
    ("0306", "0306.14", "0306.14.00", "0306.14.00.00", "冻蟹", "Crabs, frozen", 0.14, 0.09, "水产"),
    # 燕窝/特色食品 (0401-21章)
    ("0401", "0401.20", "0401.20.00", "0401.20.00.00", "未浓缩未加糖的牛奶及奶油", "Milk and cream, unsweetened", 0.10, 0.09, "食品"),
    ("0406", "0406.90", "0406.90.00", "0406.90.00.00", "其他奶酪", "Other cheese", 0.12, 0.13, "食品"),
]


# ─── Init ─────────────────────────────────────────────────────────────────────

SEED_ADMIN_EMAIL = "admin@africa-zero.com"
SEED_ADMIN_PASSWORD = "AfricaZero2026Admin!"

# ─── Seed data: Freight routes ─────────────────────────────────────────────────
# (origin_country, origin_port, origin_port_zh, dest_port, dest_port_zh, type, cost_min, cost_max, days_min, days_max, notes)
FREIGHT_ROUTES_SEED = [
    # Ethiopia → China (via Djibouti)
    ("ET", "Djibouti", "吉布提港", "SHA", "上海港", "sea20gp", 1800, 2500, 28, 35, "埃塞俄比亚主要出海口，需经亚的斯亚贝巴陆运至吉布提"),
    ("ET", "Djibouti", "吉布提港", "CAN", "广州港", "sea20gp", 1900, 2600, 28, 35, "散货按吨计约$0.05-0.10/kg"),
    ("ET", "Djibouti", "吉布提港", "NGB", "宁波港", "sea20gp", 1850, 2550, 28, 35, "埃塞俄比亚内陆运输约5-7天"),
    # Kenya → China
    ("KE", "Mombasa", "蒙巴萨港", "SHA", "上海港", "sea20gp", 1900, 2700, 25, 32, "东非主干航线，船期稳定"),
    ("KE", "Mombasa", "蒙巴萨港", "CAN", "广州港", "sea20gp", 1950, 2750, 25, 32, "东非红海航线，经印度洋"),
    ("KE", "Mombasa", "蒙巴萨港", "NGB", "宁波港", "sea20gp", 1900, 2700, 25, 32, ""),
    # Tanzania → China
    ("TZ", "Dar es Salaam", "达累斯萨拉姆", "SHA", "上海港", "sea20gp", 2000, 2800, 28, 38, "坦赞铁路起点，东非重要港口"),
    ("TZ", "Dar es Salaam", "达累斯萨拉姆", "CAN", "广州港", "sea20gp", 2050, 2900, 28, 38, ""),
    # South Africa → China
    ("ZA", "Durban", "德班港", "SHA", "上海港", "sea20gp", 2200, 3200, 30, 42, "南非主要港口，散货船为主"),
    ("ZA", "Durban", "德班港", "CAN", "广州港", "sea20gp", 2300, 3300, 30, 42, "远洋航线，经马六甲"),
    ("ZA", "Cape Town", "开普敦港", "SHA", "上海港", "sea20gp", 2300, 3300, 32, 45, ""),
    # Ghana → China
    ("GH", "Tema", "特马港", "SHA", "上海港", "sea20gp", 2100, 3000, 30, 40, "西非重要港口，加纳可可出口港"),
    ("GH", "Tema", "特马港", "CAN", "广州港", "sea20gp", 2150, 3100, 30, 40, ""),
    # Cote d'Ivoire → China
    ("CI", "Abidjan", "阿比让港", "SHA", "上海港", "sea20gp", 2100, 3000, 30, 40, "法语区西非最大港"),
    ("CI", "Abidjan", "阿比让港", "CAN", "广州港", "sea20gp", 2150, 3100, 30, 40, ""),
    # Nigeria → China
    ("NG", "Lagos", "拉各斯港", "SHA", "上海港", "sea20gp", 2200, 3200, 32, 45, "西非最大港，货物常经迪拜中转"),
    ("NG", "Lagos", "拉各斯港", "CAN", "广州港", "sea20gp", 2250, 3250, 32, 45, "需注意尼日利亚清关较复杂"),
    # Uganda → China (via Mombasa)
    ("UG", "Mombasa", "蒙巴萨港", "SHA", "上海港", "sea20gp", 2000, 2800, 30, 40, "乌干达货物经肯尼亚蒙巴萨出海"),
    ("UG", "Mombasa", "蒙巴萨港", "CAN", "广州港", "sea20gp", 2050, 2850, 30, 40, ""),
    # Rwanda → China (via Dar/Mombasa)
    ("RW", "Dar es Salaam", "达累斯萨拉姆", "SHA", "上海港", "sea20gp", 2100, 2950, 30, 42, "卢旺达货物经坦桑达港或肯尼亚蒙巴萨"),
    # Mozambique → China
    ("MZ", "Beira", "贝拉港", "SHA", "上海港", "sea20gp", 2100, 3000, 30, 42, "东非航线，煤/矿为主"),
    # Egypt → China (via Suez)
    ("EG", "Port Said", "塞得港", "SHA", "上海港", "sea20gp", 1800, 2500, 22, 30, "经苏伊士运河，走亚欧航线"),
    ("EG", "Port Said", "塞得港", "CAN", "广州港", "sea20gp", 1850, 2600, 22, 30, "地中海航线，船期稳定"),
    # Morocco → China
    ("MA", "Tanger Med", "丹吉尔港", "SHA", "上海港", "sea20gp", 1900, 2700, 28, 38, "地中海-大西洋枢纽，经直布罗陀"),
    # Angola → China
    ("AO", "Luanda", "罗安达港", "SHA", "上海港", "sea20gp", 2300, 3300, 35, 50, "石油为主，散货矿砂较多"),
    # DR Congo → China (via Dar/Durban)
    ("CD", "Dar es Salaam", "达累斯萨拉姆", "SHA", "上海港", "sea20gp", 2200, 3200, 35, 50, "刚果（金）经坦桑出海，陆运较复杂"),
    # Zambia → China (via Durban/Dar)
    ("ZM", "Durban", "德班港", "SHA", "上海港", "sea20gp", 2200, 3200, 32, 48, "铜带省货物经南非德班"),
    # Zimbabwe → China (via Durban)
    ("ZW", "Durban", "德班港", "SHA", "上海港", "sea20gp", 2250, 3250, 32, 48, "烟草/矿砂为主"),
    # Malawi → China (via Beira/Durban)
    ("MW", "Beira", "贝拉港", "SHA", "上海港", "sea20gp", 2150, 3100, 32, 48, ""),
    # Madagascar → China
    ("MG", "Toamasina", "图阿马西纳港", "SHA", "上海港", "sea20gp", 2000, 2900, 22, 30, "印度洋航线，香草/矿石为主"),
    ("MG", "Toamasina", "图阿马西纳港", "CAN", "广州港", "sea20gp", 1950, 2800, 22, 30, ""),
    # Mauritius → China
    ("MU", "Port Louis", "路易港", "SHA", "上海港", "sea20gp", 1900, 2700, 20, 28, "印度洋自由港，转口贸易活跃"),
    # Djibouti → China (direct)
    ("DJ", "Djibouti", "吉布提港", "SHA", "上海港", "sea20gp", 1750, 2400, 22, 28, "红海入口，中国海军补给港"),
    ("DJ", "Djibouti", "吉布提港", "CAN", "广州港", "sea20gp", 1700, 2350, 22, 28, "距中国近，海运费相对较低"),
    # Cameroon → China
    ("CM", "Douala", "杜阿拉港", "SHA", "上海港", "sea20gp", 2150, 3100, 32, 45, "中非地区主要出海口"),
    # Gabon → China
    ("GA", "Port Gentil", "谦蒂尔港", "SHA", "上海港", "sea20gp", 2250, 3200, 35, 50, "石油/锰矿为主"),
    # Senegal → China
    ("SN", "Dakar", "达喀尔港", "SHA", "上海港", "sea20gp", 2100, 3000, 30, 42, "西非重要港口，花生/磷酸盐"),
    # Groundnut/peanut exports from West Africa
    ("SN", "Dakar", "达喀尔港", "CAN", "广州港", "sea20gp", 2150, 3050, 30, 42, ""),
    # 40GP container rates (typically 2x 20GP for same volume)
    ("ET", "Djibouti", "吉布提港", "SHA", "上海港", "sea40hp", 3200, 4500, 28, 35, "40GP集装箱，约为20GP的1.8倍"),
    ("KE", "Mombasa", "蒙巴萨港", "SHA", "上海港", "sea40hp", 3400, 4800, 25, 32, ""),
    ("ET", "Djibouti", "吉布提港", "CAN", "广州港", "sea40hp", 3300, 4600, 28, 35, ""),
    # Air freight (expensive, fast) — per kg
    ("ET", "ADD", "亚的斯亚贝巴机场", "SHA", "上海浦东机场", "air", 8, 18, 1, 3, "空运按公斤计，适合高价值样品（咖啡/可可样品）"),
    ("KE", "NBO", "内罗毕机场", "CAN", "广州白云机场", "air", 7, 15, 1, 3, "非洲空运枢纽，鲜花/咖啡豆空运"),
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

    def force_seed(table: str, values: list, insert_sql: str):
        """Delete all then insert. Converts placeholders for PostgreSQL."""
        try:
            pg_sql = _to_pg_sql(insert_sql)
            cursor.execute(f"DELETE FROM {table}")
            cursor.executemany(pg_sql, values)
        except Exception as e:
            print(f"[ERROR] force_seed failed for {table}: {e}")
            raise

    # ── Seed countries ─────────────────────────────────────────────────────────
    force_seed(
        "africa_countries",
        AFRICA_COUNTRIES,
        "INSERT INTO africa_countries (code, name_zh, name_en, in_afcfta, has_epa) VALUES (?, ?, ?, ?, ?)",
    )

    # ── Seed HS codes ──────────────────────────────────────────────────────────
    force_seed(
        "hs_codes",
        HS_CODES_SEED,
        "INSERT INTO hs_codes (hs_4, hs_6, hs_8, hs_10, name_zh, name_en, mfn_rate, vat_rate, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    )

    # ── Seed freight routes ────────────────────────────────────────────────────
    force_seed(
        "freight_routes",
        FREIGHT_ROUTES_SEED,
        "INSERT INTO freight_routes (origin_country, origin_port, origin_port_zh, dest_port, dest_port_zh, transport_type, cost_min_usd, cost_max_usd, transit_days_min, transit_days_max, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    )

    # ── Seed certificate guides ────────────────────────────────────────────────
    force_seed(
        "cert_guides",
        CERT_GUIDES_SEED,
        "INSERT INTO cert_guides (country_code, country_name_zh, cert_type, issuing_authority, issuing_authority_zh, website_url, fee_usd_min, fee_usd_max, days_min, days_max, doc_requirements, step_sequence, api_available, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    )

    # ── Seed suppliers ─────────────────────────────────────────────────────────
    force_seed(
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

