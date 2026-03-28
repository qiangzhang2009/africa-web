"""
SQLite 写入器
将爬虫结果写入本地 SQLite 数据库。
保留现有 AfricaZero 的数据库 schema，追加/更新爬取数据。
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("pipeline.writer")


# ── 表字段映射（爬虫结果 dict 键 → 数据库表字段）─────────────────────────────────
# 对于 AfricaZero 现有 schema，爬虫写入以下只读表：
#   africa_countries, hs_codes, freight_routes, cert_guides, market_analysis, suppliers
# 用户数据（users, subscriptions, api_keys 等）不通过爬虫写入

_TABLE_MAPPING: dict[str, str] = {
    "africa_countries": """
        INSERT OR REPLACE INTO africa_countries
        (code, name_zh, name_en, in_afcfta, has_epa, created_at)
        VALUES (:code, :name_zh, :name_en, :in_afcfta, :has_epa, :created_at)
    """,
    "hs_codes": """
        INSERT OR REPLACE INTO hs_codes
        (hs_4, hs_6, hs_8, hs_10, name_zh, name_en, mfn_rate, vat_rate, category, updated_at)
        VALUES (:hs_4, :hs_6, :hs_8, :hs_10, :name_zh, :name_en, :mfn_rate, :vat_rate, :category, :updated_at)
    """,
    "freight_routes": """
        INSERT OR REPLACE INTO freight_routes
        (origin_country, origin_port, origin_port_zh, dest_country, dest_port, dest_port_zh,
         transport_type, cost_min_usd, cost_max_usd, transit_days_min, transit_days_max, notes, is_active, updated_at)
        VALUES (:origin_country, :origin_port, :origin_port_zh, :dest_country, :dest_port, :dest_port_zh,
                :transport_type, :cost_min_usd, :cost_max_usd, :transit_days_min, :transit_days_max, :notes, :is_active, :updated_at)
    """,
    "cert_guides": """
        INSERT OR REPLACE INTO cert_guides
        (country_code, country_name_zh, cert_type, cert_type_zh, issuing_authority, issuing_authority_zh,
         website_url, fee_usd_min, fee_usd_max, fee_cny_note, days_min, days_max,
         doc_requirements, step_sequence, api_available, notes, is_active, updated_at)
        VALUES (:country_code, :country_name_zh, :cert_type, :cert_type_zh, :issuing_authority, :issuing_authority_zh,
                :website_url, :fee_usd_min, :fee_usd_max, :fee_cny_note, :days_min, :days_max,
                :doc_requirements, :step_sequence, :api_available, :notes, :is_active, :updated_at)
    """,
    "market_analysis": """
        INSERT OR REPLACE INTO market_analysis
        (category, product_name_zh, product_name_en, main_hs_codes, origin_countries,
         target_china_market, import_requirements, zero_tariff_china, tariff_rate,
         market_size_usd, growth_rate, top_importers, supplier_countries, key_suppliers,
         certification_needs, logistics_notes, risk_factors, recommendation, status, updated_at)
        VALUES (:category, :product_name_zh, :product_name_en, :main_hs_codes, :origin_countries,
                :target_china_market, :import_requirements, :zero_tariff_china, :tariff_rate,
                :market_size_usd, :growth_rate, :top_importers, :supplier_countries, :key_suppliers,
                :certification_needs, :logistics_notes, :risk_factors, :recommendation, :status, :updated_at)
    """,
    "suppliers": """
        INSERT OR REPLACE INTO suppliers
        (name_zh, name_en, country, region, main_products, main_hs_codes, contact_name, contact_email,
         contact_phone, website, min_order_kg, payment_terms, export_years, annual_export_tons,
         verified_chamber, verified_实地拜访, verified_sgs, rating_avg, review_count, status, intro, certifications, created_at, updated_at)
        VALUES (:name_zh, :name_en, :country, :region, :main_products, :main_hs_codes, :contact_name, :contact_email,
                :contact_phone, :website, :min_order_kg, :payment_terms, :export_years, :annual_export_tons,
                :verified_chamber, :verified_实地拜访, :verified_sgs, :rating_avg, :review_count, :status, :intro, :certifications, :created_at, :updated_at)
    """,
}


class SQLiteWriter:
    """
    将爬虫结果写入 SQLite 数据库。
    支持 INSERT OR REPLACE（upsert）策略，保留现有数据。
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        log.info(f"[SQLiteWriter] 目标数据库：{self.db_path}")
        self._conn: Optional[sqlite3.Connection] = None

    def __enter__(self):
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            self._conn.close()

    def write_scraper_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """
        将单个爬虫运行结果写入数据库。
        result 必须包含：data_type, records
        返回写入统计：{table, inserted, updated, errors}
        """
        data_type = result.get("data_type")
        records = result.get("records", [])

        if not data_type:
            return {"error": "缺少 data_type 字段"}
        if data_type not in _TABLE_MAPPING:
            log.warning(f"[SQLiteWriter] 未知数据类型：{data_type}，跳过写入")
            return {"error": f"未知数据类型：{data_type}"}

        sql = _TABLE_MAPPING[data_type]
        inserted = 0
        errors = 0

        with self:
            cursor = self._conn.cursor()

            for record in records:
                try:
                    # 移除 None 值的键（SQLite 不支持）
                    clean = {k: v for k, v in record.items() if v is not None}
                    cursor.execute(sql, clean)
                    inserted += 1
                except sqlite3.IntegrityError as e:
                    log.warning(f"[SQLiteWriter] 数据完整性错误：{e}，记录：{record.get('name_zh', record.get('hs_10', '?'))}")
                    errors += 1
                except sqlite3.OperationalError as e:
                    log.error(f"[SQLiteWriter] SQL 操作错误：{e}，记录：{record.get('name_zh', record.get('hs_10', '?'))}")
                    errors += 1

            self._conn.commit()

        log.info(
            f"[SQLiteWriter] 写入 {data_type}：成功 {inserted} 条，错误 {errors} 条"
        )
        return {
            "table": data_type,
            "inserted": inserted,
            "errors": errors,
            "total": len(records),
        }

    def write_all_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        将多个爬虫运行结果批量写入数据库。
        """
        summaries = []
        for result in results:
            if result.get("status") == "success":
                summary = self.write_scraper_result(result)
                summaries.append(summary)
            else:
                summaries.append({
                    "error": f"爬虫 {result.get('scraper')} 失败：{result.get('error', 'unknown')}"
                })
        return summaries

    def get_table_stats(self) -> dict[str, int]:
        """返回当前数据库各表的行数。"""
        stats = {}
        with self:
            cursor = self._conn.cursor()
            for table in _TABLE_MAPPING.keys():
                try:
                    cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                    row = cursor.fetchone()
                    stats[table] = row["cnt"] if row else 0
                except sqlite3.OperationalError:
                    stats[table] = -1  # 表不存在
        return stats
