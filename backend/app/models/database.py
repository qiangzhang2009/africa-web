"""
Database models using SQLite + Peewee ORM.
Schema: africa_countries, hs_codes, policy_rules, users, calculations
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime


def get_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


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

-- Users
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT UNIQUE,
    wechat_id       TEXT,
    tier            TEXT DEFAULT 'free',
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_hs_codes_hs4  ON hs_codes(hs_4);
CREATE INDEX IF NOT EXISTS idx_hs_codes_name ON hs_codes(name_zh);
CREATE INDEX IF NOT EXISTS idx_policy_market  ON policy_rules(market);
CREATE INDEX IF NOT EXISTS idx_calc_user      ON calculations(user_id);
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
    ("SZ", "斯威士兰", "Eswatini", 1, 0),
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
    ("0901", "0901.21", "0901.21.00", "0901.21.00", "咖啡豆，未焙炒，生豆", "Coffee, not roasted", 0.08, 0.13, "咖啡"),
    ("0901", "0901.21", "0901.21.00", "0901.21.00.10", "咖啡豆，未焙炒，非速溶", "Coffee, not roasted, not instant", 0.08, 0.13, "咖啡"),
    ("0901", "0901.22", "0901.22.00", "0901.22.00.00", "咖啡豆，已焙炒", "Coffee, roasted", 0.15, 0.13, "咖啡"),
    ("0901", "0901.21", "0901.21.00", "0901.21.00.90", "咖啡豆，未焙炒，速溶用", "Coffee, not roasted, for instant", 0.08, 0.13, "咖啡"),
    # Cocoa (1801-1806)
    ("1801", "1801.00", "1801.00.00", "1801.00.00.00", "可可豆，生或焙炒", "Cocoa beans", 0.08, 0.13, "可可"),
    ("1803", "1803.10", "1803.10.00", "1803.10.00.00", "可可膏，未脱脂", "Cocoa paste, not defatted", 0.10, 0.13, "可可"),
    ("1804", "1804.00", "1804.00.00", "1804.00.00.00", "可可脂、油", "Cocoa butter, fat and oil", 0.20, 0.13, "可可"),
    ("1805", "1805.00", "1805.00.00", "1805.00.00.00", "可可粉，不含糖", "Cocoa powder, unsweetened", 0.15, 0.13, "可可"),
    # Nuts (0801-0802)
    ("0801", "0801.11", "0801.11.00", "0801.11.00.00", "椰子，干的，未去壳", "Coconuts, dried", 0.12, 0.13, "坚果"),
    ("0801", "0801.12", "0801.12.00", "0801.12.00.00", "椰子，干的，去壳", "Coconuts, dried, shelled", 0.12, 0.13, "坚果"),
    ("0801", "0801.31", "0801.31.00", "0801.31.00.00", "腰果，未去壳", "Cashew nuts, in shell", 0.10, 0.13, "坚果"),
    ("0801", "0801.32", "0801.32.00", "0801.32.00.00", "腰果，去壳", "Cashew nuts, shelled", 0.10, 0.13, "坚果"),
    ("0802", "0802.11", "0802.11.00", "0802.11.00.00", "杏仁，未去壳", "Almonds, in shell", 0.10, 0.13, "坚果"),
    ("0802", "0802.12", "0802.12.00", "0802.12.00.00", "杏仁，去壳", "Almonds, shelled", 0.10, 0.13, "坚果"),
    ("0802", "0802.21", "0802.21.00", "0802.21.00.00", "榛子，未去壳", "Hazelnuts, in shell", 0.12, 0.13, "坚果"),
    ("0802", "0802.22", "0802.22.00", "0802.22.00.00", "榛子，去壳", "Hazelnuts, shelled", 0.12, 0.13, "坚果"),
    # Minerals (2601-2621)
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
    ("1207", "1207.40", "1207.40.00", "1207.40.00.00", "芝麻种子", "Sesame seeds", 0.10, 0.13, "油籽"),
    # Tea (0902)
    ("0902", "0902.40", "0902.40.00", "0902.40.00.00", "茶（红茶及其他），已发酵", "Tea (black tea and other), fermented", 0.15, 0.13, "茶叶"),
    ("0902", "0902.30", "0902.30.00", "0902.30.00.00", "茶（红茶），未发酵，绿茶", "Tea (black), not fermented, green tea", 0.15, 0.13, "茶叶"),
]


# ─── Init ─────────────────────────────────────────────────────────────────────

def init_db(db_path: str) -> None:
    """Create tables and seed data if empty."""
    conn = get_db(db_path)
    cursor = conn.cursor()

    # Create schema
    cursor.executescript(SCHEMA_SQL)
    conn.commit()

    # Seed countries if empty
    cursor.execute("SELECT COUNT(*) FROM africa_countries")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT OR IGNORE INTO africa_countries (code, name_zh, name_en, in_afcfta, has_epa) VALUES (?, ?, ?, ?, ?)",
            AFRICA_COUNTRIES
        )

    # Seed HS codes if empty
    cursor.execute("SELECT COUNT(*) FROM hs_codes")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            """INSERT OR IGNORE INTO hs_codes
               (hs_4, hs_6, hs_8, hs_10, name_zh, name_en, mfn_rate, vat_rate, category)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            HS_CODES_SEED
        )

    conn.commit()
    conn.close()
