"""
静态文件导出器
将爬虫结果直接导出为静态 JSON 文件，随前端代码一起部署。
这是简化架构的核心：前端直接从本地 JSON 文件读取数据，无需后端 API。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger("pipeline.exporter")


class StaticExporter:
    """
    将爬虫结果导出为静态 JSON 文件。
    输出格式与前端 API 响应完全一致，前端可直接导入使用。
    """

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"[StaticExporter] 输出目录：{self.output_dir}")

    def export_scraper_result(self, result: dict[str, Any]) -> Path | None:
        """导出单个爬虫结果为 JSON 文件。"""
        data_type = result.get("data_type")
        records = result.get("records", [])
        finished_at = result.get("finished_at", datetime.now().isoformat())

        if not data_type:
            return None

        # 根据数据类型选择导出文件名
        filename_map = {
            "africa_countries": "countries.json",
            "hs_codes": "hs_codes.json",
            "freight_routes": "freight_routes.json",
            "cert_guides": "cert_guides.json",
            "market_analysis": "market_products.json",
            "suppliers": "suppliers.json",
        }

        filename = filename_map.get(data_type, f"{data_type}.json")
        file_path = self.output_dir / filename

        # 统一导出格式，模拟现有 API 响应结构
        output = self._format_output(data_type, records)

        # 添加元数据
        output["_meta"] = {
            "updated_at": finished_at,
            "source": result.get("scraper"),
            "count": len(records),
            "generated_by": "AfricaZero Scraper Pipeline",
        }

        file_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))
        log.info(f"[StaticExporter] 导出 {data_type} → {file_path} ({len(records)} 条记录)")
        return file_path

    def export_all_results(self, results: list[dict[str, Any]]) -> list[Path]:
        """导出所有爬虫结果。"""
        paths = []
        for result in results:
            if result.get("status") == "success":
                path = self.export_scraper_result(result)
                if path:
                    paths.append(path)
        return paths

    def _format_output(self, data_type: str, records: list[dict]) -> dict:
        """根据数据类型格式化输出，模拟现有 API 响应结构。"""
        if data_type == "africa_countries":
            return {
                "countries": [
                    {
                        "id": i + 1,
                        "code": r.get("code"),
                        "name_zh": r.get("name_zh"),
                        "name_en": r.get("name_en"),
                        "in_afcfta": bool(r.get("in_afcfta", False)),
                        "has_epa": bool(r.get("has_epa", False)),
                    }
                    for i, r in enumerate(records)
                ]
            }

        elif data_type == "hs_codes":
            return {
                "results": [
                    {
                        "hs_10": r.get("hs_10"),
                        "name_zh": r.get("name_zh"),
                        "name_en": r.get("name_en"),
                        "mfn_rate": r.get("mfn_rate", 0),
                        "vat_rate": r.get("vat_rate", 13),
                        "category": r.get("category"),
                        "zero_tariff": r.get("category") in [
                            "咖啡", "可可", "坚果", "矿产", "木材", "皮革",
                            "油籽", "香料", "棉麻", "橡胶", "水产"
                        ],
                    }
                    for r in records
                ]
            }

        elif data_type == "freight_routes":
            return [
                {
                    "id": i + 1,
                    "origin_country": r.get("origin_country"),
                    "origin_port": r.get("origin_port"),
                    "origin_port_zh": r.get("origin_port_zh"),
                    "dest_country": r.get("dest_country"),
                    "dest_port": r.get("dest_port"),
                    "dest_port_zh": r.get("dest_port_zh"),
                    "transport_type": r.get("transport_type"),
                    "cost_min_usd": r.get("cost_min_usd"),
                    "cost_max_usd": r.get("cost_max_usd"),
                    "transit_days_min": r.get("transit_days_min"),
                    "transit_days_max": r.get("transit_days_max"),
                    "notes": r.get("notes"),
                }
                for i, r in enumerate(records)
            ]

        elif data_type == "cert_guides":
            return [
                {
                    "id": i + 1,
                    "country_code": r.get("country_code"),
                    "country_name_zh": r.get("country_name_zh"),
                    "cert_type": r.get("cert_type"),
                    "cert_type_zh": r.get("cert_type_zh"),
                    "issuing_authority": r.get("issuing_authority") or r.get("issuing_authority_zh", ""),
                    "issuing_authority_zh": r.get("issuing_authority_zh"),
                    "website_url": r.get("website_url"),
                    "fee_usd_min": r.get("fee_usd_min"),
                    "fee_usd_max": r.get("fee_usd_max"),
                    "days_min": r.get("days_min"),
                    "days_max": r.get("days_max"),
                    "doc_requirements": json.loads(r.get("doc_requirements", "[]")) if isinstance(r.get("doc_requirements"), str) else (r.get("doc_requirements") or []),
                    "step_sequence": json.loads(r.get("step_sequence", "[]")) if isinstance(r.get("step_sequence"), str) else (r.get("step_sequence") or []),
                    "notes": r.get("notes"),
                    "api_available": bool(r.get("api_available", False)),
                }
                for i, r in enumerate(records)
            ]

        elif data_type == "market_analysis":
            return {
                "products": [
                    {
                        "id": i + 1,
                        "category": r.get("category"),
                        "product_name_zh": r.get("product_name_zh"),
                        "product_name_en": r.get("product_name_en"),
                        "main_hs_codes": r.get("main_hs_codes"),
                        "origin_countries": r.get("origin_countries"),
                        "target_china_market": r.get("target_china_market"),
                        "zero_tariff_china": bool(r.get("zero_tariff_china")),
                        "tariff_rate": r.get("tariff_rate"),
                        "market_size_usd": r.get("market_size_usd"),
                        "growth_rate": r.get("growth_rate"),
                        "certification_needs": r.get("certification_needs"),
                        "logistics_notes": r.get("logistics_notes"),
                        "risk_factors": r.get("risk_factors"),
                        "recommendation": r.get("recommendation"),
                        "status": r.get("status", "active"),
                    }
                    for i, r in enumerate(records)
                ],
                "total": len(records),
            }

        elif data_type == "suppliers":
            def _parse_list(v):
                if isinstance(v, list):
                    return v
                if isinstance(v, str):
                    try:
                        return json.loads(v)
                    except Exception:
                        return [x.strip() for x in v.split("|") if x.strip()]
                return []
            return {
                "suppliers": [
                    {
                        "id": i + 1,
                        "name_zh": r.get("name_zh"),
                        "name_en": r.get("name_en"),
                        "country": r.get("country"),
                        "region": r.get("region"),
                        "main_products": _parse_list(r.get("main_products")),
                        "main_hs_codes": _parse_list(r.get("main_hs_codes")),
                        "contact_name": r.get("contact_name"),
                        "contact_email": r.get("contact_email"),
                        "contact_phone": r.get("contact_phone"),
                        "website": r.get("website"),
                        "min_order_kg": r.get("min_order_kg"),
                        "payment_terms": r.get("payment_terms"),
                        "export_years": r.get("export_years", 0),
                        "annual_export_tons": r.get("annual_export_tons"),
                        "verified_chamber": bool(r.get("verified_chamber", False)),
                        "verified_实地拜访": bool(r.get("verified_实地拜访", False)),
                        "verified_sgs": bool(r.get("verified_sgs", False)),
                        "rating_avg": r.get("rating_avg", 0),
                        "review_count": r.get("review_count", 0),
                        "status": r.get("status", "verified"),
                        "intro": r.get("intro"),
                        "certifications": _parse_list(r.get("certifications")),
                    }
                    for i, r in enumerate(records)
                ],
                "total": len(records),
            }

        else:
            return {"data": records}
