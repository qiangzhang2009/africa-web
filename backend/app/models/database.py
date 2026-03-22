"""
Database models using SQLite + Peewee ORM.
Schema: africa_countries, hs_codes, policy_rules, users, calculations,
        subscriptions, api_keys, sub_accounts, usage_logs
"""
import sqlite3
import json
import hashlib
import secrets
from pathlib import Path
from datetime import datetime
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

def init_db(db_path: str) -> None:
    """Create tables and seed data if empty. Handles existing DB upgrades."""
    conn = get_db(db_path)
    cursor = conn.cursor()

    # Create schema
    cursor.executescript(SCHEMA_SQL)
    conn.commit()

    # ── Migration: add missing columns to existing users table ─────────────────
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
    except Exception:
        pass

    # Seed countries if empty
    cursor.execute("SELECT COUNT(*) FROM africa_countries")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT OR IGNORE INTO africa_countries (code, name_zh, name_en, in_afcfta, has_epa) VALUES (?, ?, ?, ?, ?)",
            AFRICA_COUNTRIES
        )

    # Seed HS codes if empty OR re-seed to ensure all new entries are present
    cursor.execute("SELECT COUNT(*) FROM hs_codes")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            """INSERT OR IGNORE INTO hs_codes
               (hs_4, hs_6, hs_8, hs_10, name_zh, name_en, mfn_rate, vat_rate, category)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            HS_CODES_SEED
        )
    else:
        # Force re-seed: delete and re-insert to capture any new entries added to seed data
        cursor.execute("DELETE FROM hs_codes")
        cursor.executemany(
            """INSERT INTO hs_codes
               (hs_4, hs_6, hs_8, hs_10, name_zh, name_en, mfn_rate, vat_rate, category)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            HS_CODES_SEED
        )

    conn.commit()
    conn.close()
