#!/usr/bin/env python3
"""upload_enriched_data.py — 将本地 SQLite 中的丰富数据上传到云端 Render 后端"""
import json, sqlite3, urllib.request, urllib.error, sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LOCAL_DB = SCRIPT_DIR / "data" / "africa_zero.db"
CLOUD_URL = "https://africa-web-wuxs.onrender.com"

def get_all_tables(conn):
    """导出所有数据表"""
    cursor = conn.cursor()
    tables = [
        "africa_countries",
        "hs_codes",
        "policy_rules",
        "market_analysis",
        "freight_routes",
        "cert_guides",
        "suppliers",
        "supplier_reviews",
    ]
    result = {}
    for tbl in tables:
        try:
            cursor.execute(f"SELECT * FROM {tbl}")
            cols = [d[0] for d in cursor.description]
            rows = []
            for row in cursor.fetchall():
                rows.append(dict(zip(cols, row)))
            result[tbl] = rows
            print(f"  📦 {tbl}: {len(rows)} 条")
        except Exception as e:
            print(f"  ⚠ {tbl}: {e}")
            result[tbl] = []
    return result

def upload_data(url: str, data: dict):
    """POST 到 /debug/upsert-data"""
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{url}/debug/upsert-data",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
        return result

def main():
    print(f"🔍 读取本地数据库: {LOCAL_DB}")
    if not LOCAL_DB.exists():
        print(f"❌ 数据库不存在: {LOCAL_DB}")
        sys.exit(1)

    conn = sqlite3.connect(LOCAL_DB)
    print("\n📤 导出本地数据:")
    data = get_all_tables(conn)
    conn.close()

    total = sum(len(v) for v in data.values())
    print(f"\n📊 共 {total} 条数据待上传")

    print(f"\n⬆️ 上传到 {CLOUD_URL}...")
    try:
        result = upload_data(CLOUD_URL, data)
        print(f"\n✅ 上传结果:")
        if result.get("status") == "ok":
            inserted = result.get("inserted", {})
            for tbl, count in inserted.items():
                print(f"  {tbl}: {count} 条")
            print(f"\n🎉 数据同步完成！")
        else:
            print(f"  ❌ 错误: {result.get('message', result)}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"❌ HTTP {e.code}: {body}")
    except Exception as e:
        print(f"❌ 网络错误: {e}")

if __name__ == "__main__":
    main()
