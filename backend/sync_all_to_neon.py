#!/usr/bin/env python3
"""
sync_all_to_neon.py — 将本地 SQLite 数据库完整同步到 Neon PostgreSQL

用法:
    python sync_all_to_neon.py                          # 使用本地 .env 的 DATABASE_URL
    DATABASE_URL="postgresql://..." python sync_all_to_neon.py  # 显式指定连接字符串

依赖:
    pip install psycopg2-binary python-dotenv

本脚本处理以下表的同步：
  - suppliers     (本地 196 → Neon 替换)
  - hs_codes      (本地 502 → Neon 替换)
  - freight_routes (本地 945 → Neon 替换)
  - cert_guides   (本地 1101 → Neon 替换)
  - supplier_reviews (本地 174 → Neon 替换)
  - africa_countries (本地 53 → Neon 替换)

Neon 中已同步且数据完整的表不会重新同步：
  - policy_rules (189), market_analysis (322)

已知 schema 差异会在写入前映射：
  - SQLite 的 review.comment  → Neon 的 review_text
  - SQLite 的 africa_countries.region/... → Neon 无此字段，静默忽略
  - SQLite 的 hs_codes.zero_tariff → Neon 无此字段，静默忽略
  - supplier_reviews: 跳过 user_id 为 null 的脏数据行
"""
import json
import sqlite3
import sys
import os
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Database paths ─────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
LOCAL_DB = SCRIPT_DIR / "data" / "africa_zero.db"

# ── Neon connection: 优先读取环境变量 DATABASE_URL ─────────────────────────────
NEON_URL = os.environ.get("DATABASE_URL")
if not NEON_URL:
    env_path = SCRIPT_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            k, _, v = line.partition("=")
            if k.strip() == "DATABASE_URL":
                NEON_URL = v.strip()
                break
if not NEON_URL:
    print("❌ 错误: 未找到 DATABASE_URL 环境变量。")
    print("   请设置: export DATABASE_URL='postgresql://...'\n")
    sys.exit(1)

# ── 表同步配置 ────────────────────────────────────────────────────────────────
#
# 每个表的配置:
#   cols:        要同步的列（排除 id，由 SERIAL 自增）
#   rename:      SQLite → Neon 列名映射（列名不一致时）
#   skip_if:     条件跳过（rows 为空时跳过）
#   skip_nulls:  跳过指定列为 null 的行（数据质量过滤）
#
TABLES = {
    # ── Africa countries ────────────────────────────────────────────────────────
    # Neon: id, code, name_zh, name_en, in_afcfta, has_epa, created_at
    # SQLite extras: region, capital_zh, capital_en, flag_emoji, trade_highlights
    "africa_countries": {
        "cols": ["code", "name_zh", "name_en", "in_afcfta", "has_epa"],
        "rename": {},
        "skip_nulls": {},
    },

    # ── HS codes ───────────────────────────────────────────────────────────────
    # Neon: id, hs_4, hs_6, hs_8, hs_10, name_zh, name_en, mfn_rate, vat_rate, category, updated_at
    # SQLite extras: zero_tariff
    "hs_codes": {
        "cols": ["hs_4", "hs_6", "hs_8", "hs_10", "name_zh", "name_en",
                 "mfn_rate", "vat_rate", "category"],
        "rename": {},
        "skip_nulls": {},
    },

    # ── Freight routes ─────────────────────────────────────────────────────────
    "freight_routes": {
        "cols": ["origin_country", "origin_port", "origin_port_zh",
                 "dest_country", "dest_port", "dest_port_zh",
                 "transport_type", "cost_min_usd", "cost_max_usd",
                 "transit_days_min", "transit_days_max", "notes",
                 "is_active"],
        "rename": {},
        "skip_nulls": {},
    },

    # ── Cert guides ────────────────────────────────────────────────────────────
    "cert_guides": {
        "cols": ["country_code", "country_name_zh", "cert_type", "cert_type_zh",
                 "issuing_authority", "issuing_authority_zh", "website_url",
                 "fee_usd_min", "fee_usd_max", "fee_cny_note",
                 "days_min", "days_max", "doc_requirements", "step_sequence",
                 "api_available", "notes", "is_active"],
        "rename": {},
        "skip_nulls": {},
    },

    # ── Suppliers ───────────────────────────────────────────────────────────────
    "suppliers": {
        "cols": ["name_zh", "name_en", "country", "region", "main_products",
                 "main_hs_codes", "contact_name", "contact_email", "contact_phone",
                 "website", "min_order_kg", "payment_terms", "export_years",
                 "annual_export_tons", "verified_chamber", "verified_实地拜访",
                 "verified_sgs", "rating_avg", "review_count", "status",
                 "intro", "certifications"],
        "rename": {},
        "skip_nulls": {},
    },

    # ── Supplier reviews ───────────────────────────────────────────────────────
    # Neon: id, supplier_id, user_id (NOT NULL), user_email, quality_score,
    #       delivery_score, communication_score, review_text, verified_purchase,
    #       created_at, is_verified_deal
    # SQLite: comment → Neon review_text; skip rows where user_id IS NULL
    "supplier_reviews": {
        "cols": ["supplier_id", "user_id", "user_email",
                 "quality_score", "delivery_score", "communication_score",
                 "comment", "is_verified_deal"],
        "rename": {"comment": "review_text"},
        "skip_nulls": {"user_id": None},
    },
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _serialize(val):
    """将 Python 值序列化为 PostgreSQL 可接受的格式。"""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    if isinstance(val, datetime):
        return val.isoformat()
    return val


def read_sqlite(db_path: Path, table: str, cols: list[str],
                skip_nulls: dict = None) -> list[dict]:
    """从 SQLite 读取指定列的数据，可过滤 null 行。"""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    col_str = ", ".join(f'"{c}"' for c in cols)
    cursor.execute(f'SELECT {col_str} FROM "{table}"')
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if skip_nulls:
        before = len(rows)
        rows = [r for r in rows if all(r.get(k) is not None for k in skip_nulls)]
        if before > len(rows):
            print(f"    ⚠  跳过 {before - len(rows)} 条 null 行")

    return rows


def upsert_table(pg_conn, table: str, rows: list[dict],
                 cols: list[str], rename: dict[str, str]) -> int:
    """
    将 rows 同步到 PostgreSQL。
    策略: DELETE + INSERT（覆盖式同步，Neon 数据将被本地数据替换）
    """
    if not rows:
        return 0

    cursor = pg_conn.cursor()
    pg_cols = [rename.get(c, c) for c in cols]

    try:
        cursor.execute(f'DELETE FROM "{table}"')
        placeholders = ", ".join(["%s"] * len(pg_cols))
        col_sql = ", ".join(f'"{c}"' for c in pg_cols)
        sql = f'INSERT INTO "{table}" ({col_sql}) VALUES ({placeholders})'

        for row in rows:
            vals = [_serialize(row.get(c)) for c in cols]
            cursor.execute(sql, vals)

        pg_conn.commit()
        return len(rows)

    except Exception as e:
        pg_conn.rollback()
        raise RuntimeError(f"[{table}] {e}")
    finally:
        cursor.close()


def get_local_counts(db_path: Path) -> dict[str, int]:
    """返回本地 SQLite 各表行数。"""
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cur.fetchall()]
    conn.close()

    conn2 = sqlite3.connect(str(db_path))
    cur2 = conn2.cursor()
    counts = {}
    for t in tables:
        try:
            cur2.execute(f'SELECT COUNT(*) FROM "{t}"')
            counts[t] = cur2.fetchone()[0]
        except Exception:
            counts[t] = 0
    conn2.close()
    return counts


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    import psycopg2

    if not LOCAL_DB.exists():
        print(f"❌ 本地数据库不存在: {LOCAL_DB}")
        sys.exit(1)

    # ── 1. 读取本地数据 ────────────────────────────────────────────────────────
    print(f"\n📦 读取本地数据: {LOCAL_DB}")
    local_counts = get_local_counts(LOCAL_DB)
    all_data: dict[str, list[dict]] = {}

    for table, cfg in TABLES.items():
        rows = read_sqlite(LOCAL_DB, table, cfg["cols"], cfg.get("skip_nulls"))
        local_n = local_counts.get(table, 0)
        print(f"  {table}: {len(rows)} 条 (SQLite 共 {local_n} 条)")
        all_data[table] = rows

    # ── 2. 连接 Neon ───────────────────────────────────────────────────────────
    print(f"\n🔗 连接 Neon PostgreSQL...")
    try:
        pg_conn = psycopg2.connect(NEON_URL)
        print("  ✅ 连接成功\n")
    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        sys.exit(1)

    # ── 3. 同步每个表 ─────────────────────────────────────────────────────────
    print("⬆️ 同步数据到 Neon...\n")
    results: dict[str, int] = {}

    for table, cfg in TABLES.items():
        rows = all_data[table]

        if cfg.get("skip_if_empty") and not rows:
            print(f"  ⏭  {table}: 跳过（空数据）")
            results[table] = 0
            continue

        try:
            count = upsert_table(
                pg_conn, table, rows,
                cols=cfg["cols"], rename=cfg["rename"]
            )
            results[table] = count
            print(f"  ✅ {table}: {count} 条")
        except Exception as e:
            results[table] = 0
            print(f"  ❌ {table}: {e}")

    pg_conn.close()

    # ── 4. 结果汇总 ───────────────────────────────────────────────────────────
    total_synced = sum(results.values())
    total_local = sum(len(v) for v in all_data.values())

    print(f"\n{'='*50}")
    print(f"📊 同步完成！共同步 {total_synced}/{total_local} 条数据\n")
    print(f"{'表名':<25} {'状态':>8}")
    print(f"{'-'*50}")
    for tbl, cnt in results.items():
        status = "✅" if cnt > 0 else ("⏭ 空跳过" if TABLES[tbl].get("skip_if_empty") else "⚠ 失败")
        print(f"  {tbl:<23} {cnt:>6} {status}")

    print(f"\n{'='*50}")
    if total_synced == total_local:
        print("🎉 所有数据同步成功！")
    else:
        print(f"⚠ 部分数据同步失败，请检查上方的 ❌ 行")


if __name__ == "__main__":
    main()
