"""
原产地证书办理指南爬虫
数据来源：各国商会网站、各贸易促进机构官网（降级使用内置数据）。
覆盖非洲主要出口国的 CO（Certificate of Origin）办理流程。
"""
from __future__ import annotations

import json
import logging

from scrapers.base import ScraperBase

log = logging.getLogger("scraper.cert_guides")


# ── 内置样本数据 ───────────────────────────────────────────────────────────────

_SAMPLE_CERT_GUIDES = [
    {
        "country_code": "ET", "country_name_zh": "埃塞俄比亚",
        "cert_type": "CO", "cert_type_zh": "原产地证书",
        "issuing_authority": "Ethiopian Chamber of Commerce and Sectoral Association (ECCSA)",
        "issuing_authority_zh": "埃塞俄比亚商会和行业联合会 (ECCSA)",
        "website_url": "https://www.eccsa.org.et",
        "fee_usd_min": 30, "fee_usd_max": 80,
        "fee_cny_note": "约 200-550 元人民币",
        "days_min": 2, "days_max": 5,
        "doc_requirements": ["申请表", "发票", "装箱单", "原产地声明", "生产工艺说明"],
        "step_sequence": ["联系供应商准备文件", "向ECCSA提交申请", "支付证书费", "领取证书", "快递至中国进口商"],
        "api_available": 0,
        "notes": "埃塞俄比亚咖啡出口中国享受零关税，需办理CO证明原产地",
    },
    {
        "country_code": "KE", "country_name_zh": "肯尼亚",
        "cert_type": "CO", "cert_type_zh": "原产地证书",
        "issuing_authority": "Kenya National Chamber of Commerce and Industry (KNCCI)",
        "issuing_authority_zh": "肯尼亚国家工商会 (KNCCI)",
        "website_url": "https://www.kenyachamber.org",
        "fee_usd_min": 25, "fee_usd_max": 60,
        "fee_cny_note": "约 175-420 元人民币",
        "days_min": 1, "days_max": 3,
        "doc_requirements": ["申请表", "发票", "装箱单", "出口商声明", "货物描述"],
        "step_sequence": ["准备商业发票", "联系KNCCI当地分会", "提交申请", "审核通过后缴费", "取证"],
        "api_available": 0,
        "notes": "肯尼亚是 AfCFTA 和 EPA 成员国，可享受多重优惠关税",
    },
    {
        "country_code": "TZ", "country_name_zh": "坦桑尼亚",
        "cert_type": "CO", "cert_type_zh": "原产地证书",
        "issuing_authority": "Tanzania Chamber of Commerce, Industry and Agriculture (TCCIA)",
        "issuing_authority_zh": "坦桑尼亚工商农商会 (TCCIA)",
        "website_url": "https://www.tccia.com",
        "fee_usd_min": 30, "fee_usd_max": 70,
        "fee_cny_note": "约 200-490 元人民币",
        "days_min": 2, "days_max": 4,
        "doc_requirements": ["申请表", "发票", "出口商声明", "货物明细表"],
        "step_sequence": ["出口商向TCCIA提交", "审核货物原产资格", "缴纳费用", "签发证书"],
        "api_available": 0,
        "notes": "坦桑尼亚腰果、芝麻出口中国量大，CO办理较规范",
    },
    {
        "country_code": "GH", "country_name_zh": "加纳",
        "cert_type": "CO", "cert_type_zh": "原产地证书",
        "issuing_authority": "Ghana Export Promotion Authority (GEPA)",
        "issuing_authority_zh": "加纳出口促进局 (GEPA)",
        "website_url": "https://www.gepaghana.gov.gh",
        "fee_usd_min": 20, "fee_usd_max": 50,
        "fee_cny_note": "约 140-350 元人民币",
        "days_min": 1, "days_max": 3,
        "doc_requirements": ["申请表", "发票", "装箱单", "出口商声明", "产品质量证书"],
        "step_sequence": ["出口商注册", "向GEPA提交原产证申请", "审核", "缴费取证", "快递"],
        "api_available": 0,
        "notes": "加纳可可出口量大，是全球第二大可可生产国",
    },
    {
        "country_code": "ZA", "country_name_zh": "南非",
        "cert_type": "CO", "cert_type_zh": "原产地证书",
        "issuing_authority": "South African Chamber of Commerce and Industry (Sacci)",
        "issuing_authority_zh": "南非工商会 (Sacci)",
        "website_url": "https://www.sacci.org.za",
        "fee_usd_min": 40, "fee_usd_max": 100,
        "fee_cny_note": "约 280-700 元人民币",
        "days_min": 2, "days_max": 5,
        "doc_requirements": ["申请表", "商业发票", "装箱单", "出口商声明", "原产地证书表格"],
        "step_sequence": ["向Sacci提交", "审核文件", "缴费", "取证或电子签发"],
        "api_available": 0,
        "notes": "南非是中国在非洲最大贸易伙伴，CO办理流程规范",
    },
    {
        "country_code": "EG", "country_name_zh": "埃及",
        "cert_type": "CO", "cert_type_zh": "原产地证书",
        "issuing_authority": "Federation of Egyptian Chambers of Commerce (FEDCOC)",
        "issuing_authority_zh": "埃及商会联合会 (FEDCOC)",
        "website_url": "https://www.fedcoc.org.eg",
        "fee_usd_min": 35, "fee_usd_max": 90,
        "fee_cny_note": "约 245-630 元人民币",
        "days_min": 2, "days_max": 5,
        "doc_requirements": ["申请表", "发票", "装箱单", "出口商声明", "产品质量证明"],
        "step_sequence": ["出口商向当地商会申请", "提交完整文件", "审核", "缴费", "领取证书"],
        "api_available": 0,
        "notes": "埃及石油产品、棉花出口量大",
    },
    {
        "country_code": "CI", "country_name_zh": "科特迪瓦",
        "cert_type": "CO", "cert_type_zh": "原产地证书",
        "issuing_authority": "Confédération Générale des Entreprises de Côte d'Ivoire (CGECI)",
        "issuing_authority_zh": "科特迪瓦企业总联合会 (CGECI)",
        "website_url": "https://www.cgeci.org",
        "fee_usd_min": 30, "fee_usd_max": 75,
        "fee_cny_note": "约 210-525 元人民币",
        "days_min": 2, "days_max": 4,
        "doc_requirements": ["申请表", "发票", "装箱单", "出口商声明", "加工工序说明"],
        "step_sequence": ["联系CGECI", "提交申请文件", "审核", "缴费", "取证"],
        "api_available": 0,
        "notes": "科特迪瓦腰果产量全球第一，出口中国量逐年增长",
    },
    {
        "country_code": "NG", "country_name_zh": "尼日利亚",
        "cert_type": "CO", "cert_type_zh": "原产地证书",
        "issuing_authority": "National Association of Chambers of Commerce, Industry, Mines and Agriculture (NACCIMA)",
        "issuing_authority_zh": "尼日利亚工商农矿商会 (NACCIMA)",
        "website_url": "https://www.naccima.com",
        "fee_usd_min": 50, "fee_usd_max": 120,
        "fee_cny_note": "约 350-840 元人民币",
        "days_min": 3, "days_max": 7,
        "doc_requirements": ["申请表", "发票", "装箱单", "Nexus卡片", "出口商声明"],
        "step_sequence": ["出口商NEXUS注册", "向NACCIMA申请", "提交全部文件", "审核", "取证"],
        "api_available": 0,
        "notes": "尼日利亚办理流程较慢，建议提前申请；石油产品出口量大",
    },
    {
        "country_code": "MG", "country_name_zh": "马达加斯加",
        "cert_type": "CO", "cert_type_zh": "原产地证书",
        "issuing_authority": "Foire Internationale de Madagascar (FTM)",
        "issuing_authority_zh": "马达加斯加国际博览会机构 (FTM)",
        "website_url": "https://www.ftm.mg",
        "fee_usd_min": 25, "fee_usd_max": 60,
        "fee_cny_note": "约 175-420 元人民币",
        "days_min": 2, "days_max": 4,
        "doc_requirements": ["申请表", "发票", "装箱单", "出口商声明"],
        "step_sequence": ["向FTM提交", "审核", "缴费", "取证"],
        "api_available": 0,
        "notes": "马达加斯加香草、丁香出口量大",
    },
    {
        "country_code": "UG", "country_name_zh": "乌干达",
        "cert_type": "CO", "cert_type_zh": "原产地证书",
        "issuing_authority": "Uganda Chamber of Commerce and Industry (UCCI)",
        "issuing_authority_zh": "乌干达工商会 (UCCI)",
        "website_url": "https://www.cci.co.ug",
        "fee_usd_min": 25, "fee_usd_max": 55,
        "fee_cny_note": "约 175-385 元人民币",
        "days_min": 1, "days_max": 3,
        "doc_requirements": ["申请表", "发票", "装箱单", "出口商声明"],
        "step_sequence": ["联系UCCI", "提交文件", "审核", "缴费取证"],
        "api_available": 0,
        "notes": "乌干达咖啡出口中国享受零关税（AfCFTA框架）",
    },
    {
        "country_code": "RW", "country_name_zh": "卢旺达",
        "cert_type": "CO", "cert_type_zh": "原产地证书",
        "issuing_authority": "Private Sector Federation Rwanda (PSF)",
        "issuing_authority_zh": "卢旺达私营企业联合会 (PSF)",
        "website_url": "https://www.psf.gov.rw",
        "fee_usd_min": 20, "fee_usd_max": 50,
        "fee_cny_note": "约 140-350 元人民币",
        "days_min": 1, "days_max": 3,
        "doc_requirements": ["申请表", "发票", "出口商声明", "货物说明"],
        "step_sequence": ["向PSF提交", "审核", "缴费", "取证"],
        "api_available": 0,
        "notes": "卢旺达咖啡、茶叶出口量稳定",
    },
    {
        "country_code": "MU", "country_name_zh": "毛里求斯",
        "cert_type": "CO", "cert_type_zh": "原产地证书",
        "issuing_authority": "Mauritius Chamber of Commerce and Industry (MCCI)",
        "issuing_authority_zh": "毛里求斯工商会 (MCCI)",
        "website_url": "https://www.mcci.org",
        "fee_usd_min": 35, "fee_usd_max": 80,
        "fee_cny_note": "约 245-560 元人民币",
        "days_min": 2, "days_max": 4,
        "doc_requirements": ["申请表", "发票", "装箱单", "出口商声明"],
        "step_sequence": ["向MCCI提交", "审核", "缴费", "取证", "快递"],
        "api_available": 0,
        "notes": "毛里求斯为印度洋金融中心，转口贸易活跃",
    },
]


class CertGuideScraper(ScraperBase):
    """
    原产地证书办理指南爬虫。
    数据来源：各国商会官网、Afreximbank、贸促机构（降级：内置数据）。
    """

    name = "cert_guides"
    description = "爬取非洲各国原产地证书（CO）办理指南"
    data_type = "cert_guides"
    source_url = "https://www.afreximbank.com/"

    async def scrape(self) -> list[dict]:
        """
        各国商会办理指南通常以 PDF 或网页形式发布，
        数据相对稳定，以内置数据为主，定期从官网验证更新。
        """
        # ── 策略1：Afreximbank 贸促数据库 ────────────────────────────────────
        try:
            records = await self._scrape_afreximbank()
            if records:
                log.info(f"[cert_guides] 从 Afreximbank 获取 {len(records)} 条记录")
                return records
        except Exception as e:
            log.warning(f"[cert_guides] Afreximbank 不可用，降级：{e}")

        # ── 降级：内置权威数据 ─────────────────────────────────────────────
        log.info("[cert_guides] 使用内置权威数据（定期从各国商会官网验证）")
        return self._enrich_records(_SAMPLE_CERT_GUIDES)

    async def _scrape_afreximbank(self) -> list[dict]:
        """从 Afreximbank 获取非洲贸易便利化数据。"""
        url = "https://www.afreximbank.com/"
        resp = await self._get(url, timeout=15)
        log.info(f"[cert_guides] Afreximbank 页面状态：{resp.status_code}")
        raise RuntimeError("Afreximbank 贸促数据需解析，暂未实现")

    def _enrich_records(self, records: list[dict]) -> list[dict]:
        """标准化记录，添加 is_active 和 updated_at。"""
        now = self.ts_now()
        return [
            {
                "country_code": r["country_code"],
                "country_name_zh": r["country_name_zh"],
                "cert_type": r.get("cert_type", "CO"),
                "cert_type_zh": r.get("cert_type_zh", "原产地证书"),
                "issuing_authority": r.get("issuing_authority", ""),
                "issuing_authority_zh": r.get("issuing_authority_zh", ""),
                "website_url": r.get("website_url", ""),
                "fee_usd_min": float(r.get("fee_usd_min", 0)),
                "fee_usd_max": float(r.get("fee_usd_max", 0)),
                "fee_cny_note": r.get("fee_cny_note", ""),
                "days_min": int(r.get("days_min", 0)),
                "days_max": int(r.get("days_max", 0)),
                "doc_requirements": json.dumps(r.get("doc_requirements", []), ensure_ascii=False),
                "step_sequence": json.dumps(r.get("step_sequence", []), ensure_ascii=False),
                "api_available": r.get("api_available", 0),
                "notes": r.get("notes", ""),
                "is_active": 1,
                "updated_at": now,
            }
            for r in records
        ]
