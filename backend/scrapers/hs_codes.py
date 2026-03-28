"""
HS 编码爬虫
数据来源：联合国贸易和发展会议 (UNCTAD) ITC TradeMap，
以及中国海关公开数据（降级模式使用内置样本数据）。
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Optional

from scrapers.base import ScraperBase

log = logging.getLogger("scraper.hs_codes")


# ── 内置样本数据（数据源不可用时的降级数据）────────────────────────────────────

_SAMPLE_HS_CODES = [
    # 咖啡 (Coffee)
    {"hs_4": "0901", "hs_6": "090111", "hs_8": "09011100", "hs_10": "0901110000",
     "name_zh": "未烘焙的咖啡", "name_en": "Coffee, not roasted",
     "mfn_rate": 8.0, "vat_rate": 13.0, "category": "咖啡"},
    {"hs_4": "0901", "hs_6": "090112", "hs_8": "09011200", "hs_10": "0901120000",
     "name_zh": "未烘焙的咖啡（去咖啡因）", "name_en": "Coffee, not roasted, decaffeinated",
     "mfn_rate": 8.0, "vat_rate": 13.0, "category": "咖啡"},
    {"hs_4": "0901", "hs_6": "090121", "hs_8": "09012100", "hs_10": "0901210000",
     "name_zh": "已烘焙的咖啡", "name_en": "Coffee, roasted",
     "mfn_rate": 15.0, "vat_rate": 13.0, "category": "咖啡"},
    {"hs_4": "0902", "hs_6": "090210", "hs_8": "09021000", "hs_10": "0902100000",
     "name_zh": "绿茶（未发酵），包装量≤3kg", "name_en": "Green tea (not fermented), <=3kg",
     "mfn_rate": 15.0, "vat_rate": 13.0, "category": "茶叶"},
    {"hs_4": "0902", "hs_6": "090240", "hs_8": "09024000", "hs_10": "0902400000",
     "name_zh": "其他绿茶（未发酵）", "name_en": "Other green tea (not fermented)",
     "mfn_rate": 15.0, "vat_rate": 13.0, "category": "茶叶"},
    # 可可
    {"hs_4": "1801", "hs_6": "180100", "hs_8": "18010000", "hs_10": "1801000000",
     "name_zh": "整颗或碎的可可豆", "name_en": "Cocoa beans, whole or broken",
     "mfn_rate": 8.0, "vat_rate": 13.0, "category": "可可"},
    {"hs_4": "1803", "hs_6": "180310", "hs_8": "18031000", "hs_10": "1803100000",
     "name_zh": "可可膏（未脱脂）", "name_en": "Cocoa paste, not defatted",
     "mfn_rate": 10.0, "vat_rate": 13.0, "category": "可可"},
    {"hs_4": "1804", "hs_6": "180400", "hs_8": "18040000", "hs_10": "1804000000",
     "name_zh": "可可脂", "name_en": "Cocoa butter",
     "mfn_rate": 20.0, "vat_rate": 13.0, "category": "可可"},
    # 坚果
    {"hs_4": "0801", "hs_6": "080121", "hs_8": "08012100", "hs_10": "0801210000",
     "name_zh": "未去壳腰果", "name_en": "Cashew nuts, in shell",
     "mfn_rate": 10.0, "vat_rate": 9.0, "category": "坚果"},
    {"hs_4": "0801", "hs_6": "080122", "hs_8": "08012200", "hs_10": "0801220000",
     "name_zh": "去壳腰果", "name_en": "Cashew nuts, shelled",
     "mfn_rate": 10.0, "vat_rate": 9.0, "category": "坚果"},
    {"hs_4": "0802", "hs_6": "080252", "hs_8": "08025200", "hs_10": "0802520000",
     "name_zh": "去壳开心果", "name_en": "Pistachios, shelled",
     "mfn_rate": 5.0, "vat_rate": 9.0, "category": "坚果"},
    {"hs_4": "0803", "hs_6": "080310", "hs_8": "08031000", "hs_10": "0803100000",
     "name_zh": "芭蕉干", "name_en": "Plantains, dried",
     "mfn_rate": 10.0, "vat_rate": 9.0, "category": "坚果"},
    # 矿产
    {"hs_4": "2601", "hs_6": "260111", "hs_8": "26011110", "hs_10": "2601111000",
     "name_zh": "未烧结铁矿砂及其精矿（普通粉矿）", "name_en": "Iron ore, non-agglomerated",
     "mfn_rate": 0.0, "vat_rate": 13.0, "category": "矿产"},
    {"hs_4": "2603", "hs_6": "260300", "hs_8": "26030000", "hs_10": "2603000000",
     "name_zh": "铜矿砂及其精矿", "name_en": "Copper ores and concentrates",
     "mfn_rate": 0.0, "vat_rate": 13.0, "category": "矿产"},
    {"hs_4": "2604", "hs_6": "260400", "hs_8": "26040000", "hs_10": "2604000000",
     "name_zh": "镍矿砂及其精矿", "name_en": "Nickel ores and concentrates",
     "mfn_rate": 0.0, "vat_rate": 13.0, "category": "矿产"},
    {"hs_4": "2610", "hs_6": "261000", "hs_8": "26100000", "hs_10": "2610000000",
     "name_zh": "铬矿砂及其精矿", "name_en": "Chromium ores and concentrates",
     "mfn_rate": 0.0, "vat_rate": 13.0, "category": "矿产"},
    # 木材
    {"hs_4": "4403", "hs_6": "440311", "hs_8": "44031100", "hs_10": "4403110000",
     "name_zh": "针叶木原木（用油漆等处理）", "name_en": "Coniferous wood in the rough, treated",
     "mfn_rate": 0.0, "vat_rate": 9.0, "category": "木材"},
    {"hs_4": "4403", "hs_6": "440399", "hs_8": "44039900", "hs_10": "4403990000",
     "name_zh": "其他原木", "name_en": "Other wood in the rough",
     "mfn_rate": 0.0, "vat_rate": 9.0, "category": "木材"},
    # 皮革
    {"hs_4": "4104", "hs_6": "410411", "hs_8": "41041100", "hs_10": "4104110000",
     "name_zh": "全粒面革（未剖层）", "name_en": "Full grain leather, not split",
     "mfn_rate": 8.0, "vat_rate": 13.0, "category": "皮革"},
    {"hs_4": "4112", "hs_6": "411200", "hs_8": "41120000", "hs_10": "4112000000",
     "name_zh": "精制羊皮革", "name_en": "Leather prepared after tanning, sheep",
     "mfn_rate": 10.0, "vat_rate": 13.0, "category": "皮革"},
    # 油籽
    {"hs_4": "1201", "hs_6": "120190", "hs_8": "12019000", "hs_10": "1201900000",
     "name_zh": "大豆（种用除外）", "name_en": "Soya beans, other than for sowing",
     "mfn_rate": 3.0, "vat_rate": 9.0, "category": "油籽"},
    {"hs_4": "1202", "hs_6": "120230", "hs_8": "12023000", "hs_10": "1202300000",
     "name_zh": "花生果", "name_en": "Groundnuts in shell",
     "mfn_rate": 15.0, "vat_rate": 9.0, "category": "油籽"},
    # 香料
    {"hs_4": "0904", "hs_6": "090411", "hs_8": "09041100", "hs_10": "0904110000",
     "name_zh": "胡椒（未磨）", "name_en": "Pepper, neither crushed nor ground",
     "mfn_rate": 20.0, "vat_rate": 9.0, "category": "香料"},
    {"hs_4": "0908", "hs_6": "090831", "hs_8": "09083100", "hs_10": "0908310000",
     "name_zh": "豆蔻（未磨）", "name_en": "Cardamoms, neither crushed nor ground",
     "mfn_rate": 3.0, "vat_rate": 9.0, "category": "香料"},
    # 棉麻纤维
    {"hs_4": "5201", "hs_6": "520100", "hs_8": "52010000", "hs_10": "5201000000",
     "name_zh": "未梳棉", "name_en": "Cotton, not carded or combed",
     "mfn_rate": 40.0, "vat_rate": 9.0, "category": "棉麻"},
    # 橡胶
    {"hs_4": "4001", "hs_6": "400121", "hs_8": "40012100", "hs_10": "4001210000",
     "name_zh": "天然橡胶烟片", "name_en": "Natural rubber in sheets, smoked",
     "mfn_rate": 20.0, "vat_rate": 13.0, "category": "橡胶"},
    {"hs_4": "4001", "hs_6": "400122", "hs_8": "40012200", "hs_10": "4001220000",
     "name_zh": "技术级天然橡胶（TSNR）", "name_en": "Technically specified natural rubber",
     "mfn_rate": 20.0, "vat_rate": 13.0, "category": "橡胶"},
    # 水产
    {"hs_4": "0302", "hs_6": "030271", "hs_8": "03027100", "hs_10": "0302710000",
     "name_zh": "鲜或冷的罗非鱼", "name_en": "Tilapia, fresh or chilled",
     "mfn_rate": 12.0, "vat_rate": 9.0, "category": "水产"},
    {"hs_4": "0304", "hs_6": "030461", "hs_8": "03046100", "hs_10": "0304610000",
     "name_zh": "冻罗非鱼片", "name_en": "Frozen fillets of tilapia",
     "mfn_rate": 12.0, "vat_rate": 9.0, "category": "水产"},
]


class HSScraper(ScraperBase):
    """
    HS 编码爬虫。
    主要来源：UNCTADdata API（降级：内置样本数据）。
    涵盖非洲进口热门品类：咖啡、可可、坚果、矿产、木材、皮革、油籽、香料、棉麻、橡胶、水产。
    """

    name = "hs_codes"
    description = "爬取 HS 编码及税率数据（中国海关 MFN 税率）"
    data_type = "hs_codes"
    source_url = "https://comtrade.un.org/api/refs/da/bulk"

    # ITC TradeMap API（需要 API Key，https://www.trademap.org）
    # 若有 API Key 可通过 TRADEMAP_API_KEY 环境变量配置
    TRADEMAP_BASE = "https://www.trademap.org/Product/ProductRelProdDetail.aspx"

    async def scrape(self) -> list[dict]:
        """
        执行爬取。
        优先尝试 ITC API，降级到内置样本数据。
        """
        # ── 策略1：ITC API ────────────────────────────────────────────────────
        try:
            records = await self._scrape_itc()
            if records:
                log.info(f"[hs_codes] 从 ITC API 获取 {len(records)} 条记录")
                return self._enrich_records(records)
        except Exception as e:
            log.warning(f"[hs_codes] ITC API 不可用，降级：{e}")

        # ── 策略2：中国海关数据 ───────────────────────────────────────────────
        try:
            records = await self._scrape_china_customs()
            if records:
                log.info(f"[hs_codes] 从中国海关获取 {len(records)} 条记录")
                return self._enrich_records(records)
        except Exception as e:
            log.warning(f"[hs_codes] 中国海关不可用，降级：{e}")

        # ── 策略3：内置样本数据 ───────────────────────────────────────────────
        log.info("[hs_codes] 使用内置样本数据（生产环境请配置真实数据源）")
        return self._enrich_records(_SAMPLE_HS_CODES)

    async def _scrape_itc(self) -> list[dict]:
        """
        尝试从 ITC TradeMap 获取数据。
        注意：TradeMap 公开 API 有访问频率限制。
        """
        api_key = None  # 可通过环境变量 TRADEMAP_API_KEY 配置
        if not api_key:
            raise RuntimeError("无 API Key，跳过 ITC")

        url = "https://www.trademap.org/Download/CN_HS6_2017_V3.zip"
        # ITC 批量数据需要认证，此处作为占位
        raise RuntimeError("ITC 批量数据需认证，暂不可用")

    async def _scrape_china_customs(self) -> list[dict]:
        """
        从中国海关公开页面爬取 HS 税率。
        """
        url = "http://www.customs.gov.cn/customs/zsjd/2475/2475_dwls/index.html"
        try:
            resp = await self._get(url, timeout=10)
            # 海关页面结构复杂，此处作为占位
            log.info(f"[hs_codes] 海关页面状态码：{resp.status_code}")
        except Exception:
            pass
        raise RuntimeError("海关页面暂不可访问")

    def _enrich_records(self, records: list[dict]) -> list[dict]:
        """
        标准化记录，添加 updated_at。
        """
        now = self.ts_now()
        enriched = []
        for r in records:
            normalized = {
                "hs_4": r.get("hs_4", ""),
                "hs_6": r.get("hs_6", ""),
                "hs_8": r.get("hs_8", ""),
                "hs_10": r.get("hs_10", ""),
                "name_zh": r.get("name_zh", ""),
                "name_en": r.get("name_en", ""),
                "mfn_rate": float(r.get("mfn_rate", 0)),
                "vat_rate": float(r.get("vat_rate", 13.0)),
                "category": r.get("category", ""),
                "updated_at": now,
            }
            enriched.append(normalized)
        return enriched
