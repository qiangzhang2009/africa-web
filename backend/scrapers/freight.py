"""
船运路线爬虫
数据来源：Freightos Baltic Index (FBX)、各大货代平台公开报价、
UNCTAD 贸易便利化数据（降级使用内置样本数据）。
"""
from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import ScraperBase

log = logging.getLogger("scraper.freight")


# ── 内置样本数据（数据源不可用时的降级数据）────────────────────────────────────
# 从非洲主要港口到中国主要港口的海运费参考价（USD/TEU or USD/kg for air）
_SAMPLE_FREIGHT_ROUTES = [
    # 肯尼亚 Mombasa → 中国各港
    {"origin_country": "KE", "origin_port": "MBA", "origin_port_zh": "蒙巴萨港",
     "dest_country": "CN", "dest_port": "SHA", "dest_port_zh": "上海港",
     "transport_type": "sea20gp", "cost_min_usd": 2800, "cost_max_usd": 4200,
     "transit_days_min": 22, "transit_days_max": 28,
     "notes": "蒙巴萨港为东非最大港，服务覆盖肯尼亚、乌干达、卢旺达、南苏丹"},
    {"origin_country": "KE", "origin_port": "MBA", "origin_port_zh": "蒙巴萨港",
     "dest_country": "CN", "dest_port": "NGB", "dest_port_zh": "宁波港",
     "transport_type": "sea20gp", "cost_min_usd": 2900, "cost_max_usd": 4300,
     "transit_days_min": 24, "transit_days_max": 30,
     "notes": "宁波港为中国第二大港，散货和集装箱均发达"},
    # 坦桑尼亚 Dar es Salaam → 中国各港
    {"origin_country": "TZ", "origin_port": "DAR", "origin_port_zh": "达累斯萨拉姆港",
     "dest_country": "CN", "dest_port": "SHA", "dest_port_zh": "上海港",
     "transport_type": "sea20gp", "cost_min_usd": 3000, "cost_max_usd": 4500,
     "transit_days_min": 26, "transit_days_max": 34,
     "notes": "达累斯萨拉姆港服务东非内陆国家"},
    # 南非 Durban → 中国各港
    {"origin_country": "ZA", "origin_port": "DUR", "origin_port_zh": "德班港",
     "dest_country": "CN", "dest_port": "SHA", "dest_port_zh": "上海港",
     "transport_type": "sea20gp", "cost_min_usd": 1500, "cost_max_usd": 2800,
     "transit_days_min": 20, "transit_days_max": 26,
     "notes": "德班港为南非最大集装箱港，连接南部非洲"},
    {"origin_country": "ZA", "origin_port": "DUR", "origin_port_zh": "德班港",
     "dest_country": "CN", "dest_port": "CAN", "dest_port_zh": "广州港",
     "transport_type": "sea20gp", "cost_min_usd": 1600, "cost_max_usd": 2900,
     "transit_days_min": 22, "transit_days_max": 28,
     "notes": "广州港辐射华南制造业"},
    # 尼日利亚 Lagos/Apapa → 中国各港
    {"origin_country": "NG", "origin_port": "LOS", "origin_port_zh": "拉各斯阿帕帕港",
     "dest_country": "CN", "dest_port": "SHA", "dest_port_zh": "上海港",
     "transport_type": "sea20gp", "cost_min_usd": 4500, "cost_max_usd": 7000,
     "transit_days_min": 32, "transit_days_max": 42,
     "notes": "尼日利亚为非洲最大经济体，货物通关较复杂"},
    {"origin_country": "NG", "origin_port": "LOS", "origin_port_zh": "拉各斯阿帕帕港",
     "dest_country": "CN", "dest_port": "TJN", "dest_port_zh": "天津港",
     "transport_type": "sea20gp", "cost_min_usd": 4600, "cost_max_usd": 7200,
     "transit_days_min": 34, "transit_days_max": 44,
     "notes": "天津港服务华北市场"},
    # 埃及 Port Said → 中国各港（地中海-红海航线）
    {"origin_country": "EG", "origin_port": "PSD", "origin_port_zh": "塞得港",
     "dest_country": "CN", "dest_port": "SHA", "dest_port_zh": "上海港",
     "transport_type": "sea20gp", "cost_min_usd": 2200, "cost_max_usd": 3800,
     "transit_days_min": 28, "transit_days_max": 38,
     "notes": "塞得港位于苏伊士运河入口，服务北非及地中海国家"},
    # 科特迪瓦 Abidjan → 中国各港
    {"origin_country": "CI", "origin_port": "ABJ", "origin_port_zh": "阿比让港",
     "dest_country": "CN", "dest_port": "SHA", "dest_port_zh": "上海港",
     "transport_type": "sea20gp", "cost_min_usd": 3200, "cost_max_usd": 4800,
     "transit_days_min": 28, "transit_days_max": 36,
     "notes": "阿比让港为西非重要港口，覆盖科特迪瓦及周边国家"},
    # 加纳 Tema → 中国各港
    {"origin_country": "GH", "origin_port": "TMA", "origin_port_zh": "特马港",
     "dest_country": "CN", "dest_port": "SHA", "dest_port_zh": "上海港",
     "transport_type": "sea20gp", "cost_min_usd": 3100, "cost_max_usd": 4700,
     "transit_days_min": 26, "transit_days_max": 34,
     "notes": "特马港服务加纳及西非内陆国家"},
    # 埃塞俄比亚（经吉布提）
    {"origin_country": "ET", "origin_port": "DJI", "origin_port_zh": "吉布提港",
     "dest_country": "CN", "dest_port": "SHA", "dest_port_zh": "上海港",
     "transport_type": "sea20gp", "cost_min_usd": 2700, "cost_max_usd": 4000,
     "transit_days_min": 20, "transit_days_max": 26,
     "notes": "埃塞俄比亚进出口主要通过吉布提港"},
    # 卢旺达/布隆迪（经坦桑尼亚达累斯萨拉姆）
    {"origin_country": "RW", "origin_port": "DAR", "origin_port_zh": "达累斯萨拉姆港",
     "dest_country": "CN", "dest_port": "SHA", "dest_port_zh": "上海港",
     "transport_type": "sea20gp", "cost_min_usd": 3000, "cost_max_usd": 4500,
     "transit_days_min": 26, "transit_days_max": 34,
     "notes": "卢旺达进出口货物多经坦桑尼亚达累斯萨拉姆港"},
    # 空运样本（吉布提→上海）
    {"origin_country": "DJ", "origin_port": "JIB", "origin_port_zh": "吉布提",
     "dest_country": "CN", "dest_port": "SHA", "dest_port_zh": "上海",
     "transport_type": "air", "cost_min_usd": 3.5, "cost_max_usd": 6.0,
     "transit_days_min": 1, "transit_days_max": 3,
     "notes": "空运价格以 USD/kg 计，适合高价值或紧急货物"},
    # 40HP 样本（肯尼亚蒙巴萨→上海）
    {"origin_country": "KE", "origin_port": "MBA", "origin_port_zh": "蒙巴萨港",
     "dest_country": "CN", "dest_port": "SHA", "dest_port_zh": "上海港",
     "transport_type": "sea40hp", "cost_min_usd": 5200, "cost_max_usd": 7800,
     "transit_days_min": 22, "transit_days_max": 28,
     "notes": "40HP 适合大批量货物，单箱成本低于 2×20GP"},
]


class FreightScraper(ScraperBase):
    """
    船运路线爬虫。
    数据来源：Freightos Baltic Index、Drewry World Container Index、
    各主要货代平台公开报价（降级：内置样本数据）。
    """

    name = "freight"
    description = "爬取非洲→中国船运路线及运费参考价"
    data_type = "freight_routes"
    source_url = "https://fbx.freightos.com/"

    async def scrape(self) -> list[dict]:
        """
        船运费率数据来源：
        1. Freightos FBX API（需付费订阅）
        2. Drewry WCI 公开报告
        3. 内置样本数据（降级）
        """
        # ── 策略1：Freightos FBX API ──────────────────────────────────────────
        try:
            records = await self._scrape_freightos()
            if records:
                log.info(f"[freight] 从 Freightos 获取 {len(records)} 条记录")
                return self._enrich_records(records)
        except Exception as e:
            log.warning(f"[freight] Freightos 不可用，降级：{e}")

        # ── 策略2：Drewry WCI ────────────────────────────────────────────────
        try:
            records = await self._scrape_drewry()
            if records:
                log.info(f"[freight] 从 Drewry 获取 {len(records)} 条记录")
                return self._enrich_records(records)
        except Exception as e:
            log.warning(f"[freight] Drewry 不可用，降级：{e}")

        # ── 降级：内置样本数据 ─────────────────────────────────────────────
        log.info("[freight] 使用内置样本数据（生产环境请订阅 Freightos FBX）")
        return self._enrich_records(_SAMPLE_FREIGHT_ROUTES)

    async def _scrape_freightos(self) -> list[dict]:
        """从 Freightos FBX API 获取运费指数。"""
        api_key = None  # 可通过环境变量 FREIGHTOS_API_KEY 配置
        if not api_key:
            raise RuntimeError("无 Freightos API Key，跳过")

        url = "https://api.freightos.com/v1/rates"
        resp = await self._get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        # Freightos 返回 JSON 格式的运费指数
        log.info(f"[freight] Freightos API 响应状态：{resp.status_code}")
        raise RuntimeError("Freightos API 响应格式待解析")

    async def _scrape_drewry(self) -> list[dict]:
        """从 Drewry WCI 公开报告获取运费数据。"""
        url = "https://www.drewry.co.uk/supply-chain-advisors/supply-chain-advisories"
        resp = await self._get(url, timeout=15)
        log.info(f"[freight] Drewry 页面状态：{resp.status_code}")
        raise RuntimeError("Drewry WCI 需订阅，暂不可访问")

    def _enrich_records(self, records: list[dict]) -> list[dict]:
        """标准化记录，添加 is_active 和 updated_at。"""
        now = self.ts_now()
        return [
            {
                "origin_country": r["origin_country"],
                "origin_port": r["origin_port"],
                "origin_port_zh": r["origin_port_zh"],
                "dest_country": r.get("dest_country", "CN"),
                "dest_port": r["dest_port"],
                "dest_port_zh": r["dest_port_zh"],
                "transport_type": r["transport_type"],
                "cost_min_usd": float(r["cost_min_usd"]),
                "cost_max_usd": float(r["cost_max_usd"]),
                "transit_days_min": int(r["transit_days_min"]),
                "transit_days_max": int(r["transit_days_max"]),
                "notes": r.get("notes"),
                "is_active": 1,
                "updated_at": now,
            }
            for r in records
        ]
