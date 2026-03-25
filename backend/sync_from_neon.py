#!/usr/bin/env python3
"""
sync_from_neon.py — 从 Neon 云端数据库同步数据到本地 SQLite
用法: python sync_from_neon.py [--neon-url URL]

需要在环境变量中设置:
  NEON_API_URL — Neon 后端地址，默认: https://africa-web-wuxs.onrender.com
"""
import sys
import os
import sqlite3
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path

# ── Database path ────────────────────────────────────────────────────────────
# The app resolves data/africa_zero.db relative to cwd at startup.
# get_db_path() uses Path.cwd() — which depends on where uvicorn starts.
# To avoid ambiguity, we compute the canonical path:
#   1. Try ROOT/data/africa_zero.db  (app started from africa-zero/ dir)
#   2. Try BACKEND/data/africa_zero.db (app started from backend/ dir)
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent  # africa-zero/
BACKEND_DIR = SCRIPT_DIR      # africa-zero/backend/

LOCAL_DB_ROOT = ROOT_DIR / "data" / "africa_zero.db"
LOCAL_DB_BACKEND = BACKEND_DIR / "data" / "africa_zero.db"

# Prefer the ROOT version if it exists and is newer; otherwise use BACKEND
if LOCAL_DB_ROOT.exists() and LOCAL_DB_ROOT.stat().st_mtime >= LOCAL_DB_BACKEND.stat().st_mtime:
    LOCAL_DB = str(LOCAL_DB_ROOT)
else:
    LOCAL_DB = str(LOCAL_DB_BACKEND)


def get_neon_data(url: str) -> dict:
    """从 Neon API 获取所有数据。"""
    req = urllib.request.Request(
        f"{url}/debug/export-all-data",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def ensure_local_db():
    """确保本地数据库文件存在。"""
    os.makedirs(os.path.dirname(LOCAL_DB), exist_ok=True)
    if not os.path.exists(LOCAL_DB):
        sqlite3.connect(LOCAL_DB).close()


def get_local_conn():
    """获取本地 SQLite 连接。"""
    return sqlite3.connect(LOCAL_DB)


# ── Column mappings for each table ──────────────────────────────────────────
# (local_column, neon_key) — we only sync these fields
TABLE_MAPPINGS = {
    "africa_countries": [
        "code", "name_zh", "name_en", "region", "capital_zh", "capital_en",
        "in_afcfta", "has_epa", "trade_highlights", "flag_emoji",
    ],
    "hs_codes": [
        "hs_4", "hs_6", "hs_8", "hs_10", "name_zh", "name_en",
        "mfn_rate", "vat_rate", "category", "zero_tariff",
    ],
    "freight_routes": [
        "origin_country", "origin_port", "origin_port_zh",
        "dest_port", "dest_port_zh", "transport_type",
        "cost_min_usd", "cost_max_usd", "transit_days_min", "transit_days_max",
        "notes",
    ],
    "cert_guides": [
        "country_code", "country_name_zh", "cert_type", "cert_type_zh",
        "issuing_authority_zh", "fee_usd_min", "fee_usd_max",
        "days_min", "days_max", "doc_requirements", "step_sequence", "api_available",
    ],
    "suppliers": [
        "name_zh", "name_en", "country", "region", "main_products",
        "main_hs_codes", "contact_name", "contact_email", "contact_phone", "website",
        "min_order_kg", "payment_terms", "export_years", "annual_export_tons",
        "verified_chamber", "verified_实地拜访", "verified_sgs",
        "rating_avg", "review_count", "status", "intro", "certifications",
    ],
}


def sync_table(conn: sqlite3.Connection, table: str, neon_data: list, columns: list):
    """同步单个表的数据。"""
    cursor = conn.cursor()

    # 1. 获取 neon 数据中的 id 字段（如果存在）
    has_id = "id" in neon_data[0] if neon_data else False

    # 2. DELETE 现有数据
    cursor.execute(f"DELETE FROM {table}")
    deleted = cursor.rowcount

    # 3. 插入新数据
    # 构建 INSERT 语句，只包含已知列
    valid_cols = [c for c in columns if c in (neon_data[0] if neon_data else {})]
    placeholders = ", ".join(["?"] * len(valid_cols))
    insert_sql = f"INSERT INTO {table} ({', '.join(valid_cols)}) VALUES ({placeholders})"

    inserted = 0
    for row in neon_data:
        values = []
        for col in valid_cols:
            val = row.get(col)
            # SQLite 不支持 JSON，序列化
            if isinstance(val, (dict, list)):
                val = json.dumps(val, ensure_ascii=False)
            elif val is None:
                val = None
            else:
                val = str(val) if not isinstance(val, (int, float)) else val
            values.append(val)
        try:
            cursor.execute(insert_sql, values)
            inserted += 1
        except Exception as e:
            print(f"    ⚠ 跳过第 {inserted + 1} 行: {e}")

    conn.commit()
    print(f"  ✅ {table}: 删除 {deleted} 行, 插入 {inserted} 行")
    return inserted, deleted


def main():
    parser = argparse.ArgumentParser(description="从 Neon 同步数据到本地 SQLite")
    parser.add_argument(
        "--neon-url",
        default=os.environ.get("NEON_API_URL", "https://africa-web-wuxs.onrender.com"),
        help="Neon 后端地址",
    )
    args = parser.parse_args()

    print(f"\n📡 正在从 {args.neon_url} 获取数据...")
    try:
        data = get_neon_data(args.neon_url)
    except urllib.error.URLError as e:
        print(f"❌ 网络错误: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析错误: {e}")
        sys.exit(1)

    print(f"\n📊 获取到数据: {', '.join(f'{k}({len(v)}条)' for k, v in data.items() if isinstance(v, list))}")

    print(f"\n💾 正在同步到 {LOCAL_DB}...")
    ensure_local_db()
    conn = get_local_conn()

    total_inserted = 0
    for table, columns in TABLE_MAPPINGS.items():
        if table not in data:
            print(f"  ⏭ 跳过 {table} (无数据)")
            continue
        neon_rows = data[table]
        if isinstance(neon_rows, dict) and "error" in neon_rows:
            print(f"  ❌ {table}: API错误 - {neon_rows['error']}")
            continue
        inserted, deleted = sync_table(conn, table, neon_rows, columns)
        total_inserted += inserted

    conn.close()
    print(f"\n🎉 同步完成！共插入 {total_inserted} 行数据。")
    print(f"\n本地数据库路径: {LOCAL_DB}")
    print("你可以用以下命令查看数据:")
    print(f"  sqlite3 {LOCAL_DB} '.tables'")
    print(f"  sqlite3 {LOCAL_DB} 'SELECT COUNT(*) FROM suppliers'")


if __name__ == "__main__":
    main()
