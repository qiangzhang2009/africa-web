#!/usr/bin/env python3
"""sync_to_cloud.py - 直接从本地 SQLite 同步数据到云端 Neon PostgreSQL
   适配云端数据库的实际表结构
"""
import json, sqlite3, psycopg2, sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LOCAL_DB = SCRIPT_DIR / "data" / "africa_zero.db"

# 从 Render 后端获取的 Neon 连接信息
NEON_URL = "postgresql://neondb_owner:npg_78oFJkaWtPBd@ep-mute-grass-a1etwjuh-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

# 定义每个表要同步的字段（云端存在的字段）
TABLE_COLUMNS = {
    "africa_countries": ["code", "name_zh", "name_en", "in_afcfta", "has_epa"],
    "hs_codes": ["hs_4", "hs_6", "hs_8", "hs_10", "name_zh", "name_en", "mfn_rate", "vat_rate", "category"],
    "policy_rules": None,  # 全部字段
    "market_analysis": None,  # 全部字段
    "freight_routes": None,  # 全部字段
    "cert_guides": None,  # 全部字段
    "suppliers": None,  # 全部字段
    "supplier_reviews": ["supplier_id", "user_id", "user_email", "quality_score", "delivery_score", "communication_score", "created_at", "is_verified_deal"],
}

def get_local_data():
    """从本地 SQLite 读取所有数据"""
    conn = sqlite3.connect(LOCAL_DB)
    conn.row_factory = sqlite3.Row
    data = {}
    for tbl, cols in TABLE_COLUMNS.items():
        try:
            if cols:
                col_str = ", ".join(cols)
                rows = [dict(r) for r in conn.execute(f"SELECT {col_str} FROM {tbl}")]
            else:
                rows = [dict(r) for r in conn.execute(f"SELECT * FROM {tbl}")]
            data[tbl] = rows
            print(f"  📦 {tbl}: {len(rows)} 条")
        except Exception as e:
            print(f"  ⚠ {tbl}: {e}")
            data[tbl] = []
    conn.close()
    return data

def serialize(val):
    """序列化值以便 PostgreSQL 插入"""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    return val

def sync_table(pg_conn, table: str, rows: list[dict], cols: list = None) -> int:
    """同步单个表到 PostgreSQL"""
    if not rows:
        return 0
    
    cursor = pg_conn.cursor()
    # 确定要同步的列
    if cols is None:
        cols = [c for c in rows[0].keys() if c != "id"]
    
    try:
        # 清空表
        cursor.execute(f"DELETE FROM {table}")
        
        # 插入数据
        placeholders = ", ".join(["%s"] * len(cols))
        cols_str = ", ".join(cols)
        sql = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders})"
        
        for row in rows:
            vals = [serialize(row.get(c)) for c in cols]
            cursor.execute(sql, vals)
        
        pg_conn.commit()
        return len(rows)
    except Exception as e:
        pg_conn.rollback()
        raise Exception(f"{table}: {e}")
    finally:
        cursor.close()

def main():
    print("🔍 读取本地数据库...")
    data = get_local_data()
    
    total = sum(len(v) for v in data.values())
    print(f"\n📊 共 {total} 条数据待同步")
    
    print(f"\n🔗 连接云端 Neon PostgreSQL...")
    try:
        pg_conn = psycopg2.connect(NEON_URL)
        print("✅ 连接成功!")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        sys.exit(1)
    
    print("\n⬆️ 同步数据到云端...")
    results = {}
    for tbl, rows in data.items():
        cols = TABLE_COLUMNS.get(tbl)
        try:
            count = sync_table(pg_conn, tbl, rows, cols)
            results[tbl] = count
            print(f"  ✅ {tbl}: {count} 条")
        except Exception as e:
            print(f"  ❌ {tbl}: {e}")
            results[tbl] = 0
    
    pg_conn.close()
    
    print("\n✅ 同步完成!")
    print("\n📊 同步结果:")
    for tbl, count in results.items():
        print(f"  {tbl}: {count} 条")

if __name__ == "__main__":
    main()
