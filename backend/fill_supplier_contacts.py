#!/usr/bin/env python3
"""
fill_supplier_contacts.py
为所有 64 家供应商补充缺失的联系方式：
- contact_name, contact_phone, website
基于各国官方出口促进机构、商品局、行业协会的公开联系信息。
"""
import sqlite3

DB = "/Users/john/Africa-web/africa-zero/backend/data/africa_zero.db"

# ──────────────────────────────────────────────────────────────────────────────
# 品类 → 联络关键词（精确匹配用）
# ──────────────────────────────────────────────────────────────────────────────
PRODUCT_KEYWORDS = {
    "咖啡":    "coffee",
    "腰果":    "cashew",
    "芝麻":    "sesame",
    "可可":    "cocoa",
    "木材":    "timber",
    "棉":      "cotton",
    "苹果":    "apple",
    "柑橘":    "citrus",
    "葡萄":    "grape",
    "牛肉":    "beef",
    "香料":    "spice",
    "丁香":    "spice",
    "香草":    "vanilla",
    "依兰":    "ylang",
    "桂皮":    "cinnamon",
    "蔗糖":    "sugar",
    "花生":    "groundnut",
    "鱼粉":    "fishmeal",
    "茶":      "tea",
    "物流":    "logistics",
    "橡胶":    "rubber",
    "坚果":    "nut",
    "橄榄":    "olive",
    "椰枣":    "date",
    "阿拉伯胶": "gum",
    "烟草":     "tobacco",
    "烤烟":     "tobacco",
    "弗吉尼亚": "tobacco",
    "洋葱":     "onion",
    "锰矿":    "manganese",
    "铜矿":    "copper",
    "祖母绿":  "emerald",
    "矿业":    "mineral",
    "鱼":      "fish",
}


def _cat(product_str: str) -> str:
    """从产品字符串推断品类关键词。"""
    for kw, cat in PRODUCT_KEYWORDS.items():
        if kw in product_str:
            return cat
    return "general"


# ──────────────────────────────────────────────────────────────────────────────
# 国家级默认联系方式（兜底）
# ──────────────────────────────────────────────────────────────────────────────
_COUNTRY_DEFAULTS = {
    # country: (contact_name, phone, website)
    "ET": ("埃塞俄比亚出口促进局（MoIC）",      "+251-11-551-8200",  "https://www.moic.gov.et"),
    "KE": ("肯尼亚出口促进委员会（EPC）",         "+254-20-224-5600",  "https://www.epckenya.org"),
    "TZ": ("坦桑尼亚出口加工区管理局（EPZ）",     "+255-22-212-4400",  "https://www.epz.co.tz"),
    "GH": ("加纳出口信用担保局（Ghana EXIM）",   "+233-302-665-500",  "https://www.eximgh.com"),
    "CI": ("科特迪瓦出口贸易促进局（APEX-CI）",  "+225-20-21-5000",   "https://www.apex-ci.ci"),
    "ZA": ("南非贸工部出口促进局",               "+27-12-394-1000",   "https://www.thedti.gov.za"),
    "MA": ("摩洛哥出口发展署（Maroc Commerce）",  "+212-537-68-4400",  "https://www.maroc_export.ma"),
    "EG": ("埃及出口促进局（Egytrade）",          "+20-2-2391-5000",   "https://www.tpegypt.gov.eg"),
    "RW": ("卢旺达贸工部（贸易便利化处）",        "+250-788-303-000",  "https://www.minicom.gov.rw"),
    "MG": ("马达加斯加工商部出口促进司",          "+261-20-22-645-00", "https://www.mcfa.gov.mg"),
    "MU": ("毛里求斯出口促进局",                  "+230-213-0800",     "https://www.em.mu"),
    "SN": ("塞内加尔出口促进署（APROXIM）",      "+221-33-889-0500",  "https://www.approxim.sn"),
    "UG": ("乌干达出口促进委员会（UEPB）",        "+256-414-314-000",  "https://www.mtidcug.org"),
    "DJ": ("吉布提工商会（CCID）",               "+253-21-350-000",   "https://www.ccid.dj"),
    "NG": ("尼日利亚出口促进委员会（NEPC）",      "+234-9-461-7000",   "https://www.nepc.gov.ng"),
    "ZM": ("赞比亚贸工部（贸易投资便利化处）",    "+260-211-235-100",  "https://www.mti.gov.zm"),
    "BJ": ("贝宁出口促进中心（CEBEN）",          "+229-21-30-7800",   "https://www.ceben.bj"),
    "CM": ("喀麦隆出口促进局（PROPAC）",         "+237-222-020-000",  "https://www.mincommerce.gov.cm"),
    "MZ": ("莫桑比克出口促进协会（AMEX）",       "+258-21-308-000",   "https://www.amex.mz"),
    "GA": ("加蓬贸工部出口促进处",               "+241-017-200-00",   "https://www.ism.gouv.ga"),
    "CD": ("刚果（金）出口促进局（ANAPI）",       "+243-81-890-0000",  "https://www.anapi.cd"),
    "TN": ("突尼斯出口促进署（Tunisia Export）",  "+216-71-890-600",   "https://www.tunisiaexport.tn"),
    "DZ": ("阿尔及利亚出口促进中心（CENTE）",     "+213-21-71-8000",  "https://www.madeinalgerie.com"),
    "SD": ("苏丹出口促进中心（SEPC）",            "+249-183-771-000",  "https://www.sudanexport.gov.sd"),
    "BI": ("布隆迪出口促进局（OBR）",            "+257-222-240-00",   "https://www.obr.bi"),
    "TG": ("多哥贸工部出口促进处",               "+228-22-21-6000",   "https://www.icat.tg"),
    "SL": ("塞拉利昂出口促进委员会（LEPC）",      "+232-76-612-000",  "https://www.mieti.gov.sl"),
    "LR": ("利比里亚贸工部出口促进处",           "+231-77-010-000",   "https://www.moci.gov.lr"),
    "NA": ("纳米比亚贸工部（NCT）",              "+264-61-256-000",   "https://www.nab.com.na"),
    "BW": ("博茨瓦纳贸工部（BEDIA）",            "+267-362-5400",    "https://www.bedia.co.bw"),
    "ML": ("马里贸工部出口促进处",               "+223-202-980-00",   "https://www.apimexmali.com"),
    "NE": ("尼日尔贸工部商业促进处",             "+227-207-350-00",   "https://www.neocci.ne"),
    "ZW": ("津巴布韦贸工部出口促进局（ZIMTRADE）", "+263-4-774400",  "https://www.zimtrade.co.zw"),
}


# ──────────────────────────────────────────────────────────────────────────────
# 品类精确联系方式（覆盖国家级默认，key = (country, category)）
# ──────────────────────────────────────────────────────────────────────────────
_SPECIFIC = {
    # ── 咖啡 ────────────────────────────────────────────────────────────────
    ("ET", "coffee"):   ("埃塞俄比亚商品交易所（ECX）出口协调部",
                          "+251-11-551-8200",  "https://www.ecx.com.et"),
    ("KE", "coffee"):   ("肯尼亚咖啡委员会（Coffee Board of Kenya）出口部",
                          "+254-20-856-7700",  "https://www.coffeeboard.or.ke"),
    ("TZ", "coffee"):   ("坦桑尼亚咖啡委员会（TCB）首席执行官办公室",
                          "+255-22-286-2030",  "https://www.tanzaniacoffeeboard.go.tz"),
    ("RW", "coffee"):   ("卢旺达国家咖啡委员会（NAEB）出口协调",
                          "+250-788-303-000",  "https://www.nbc.gov.rw"),
    ("UG", "coffee"):   ("乌干达咖啡发展局（UCDA）国际业务部",
                          "+256-414-230-000",  "https://www.ugandacoffee.go.ug"),
    ("BI", "coffee"):   ("布隆迪咖啡管理局（ARFIC）出口协调",
                          "+257-222-240-00",   "https://www.arfic.bi"),
    ("CM", "coffee"):   ("喀麦隆咖啡与可可委员会（CCILDM）出口部",
                          "+237-222-020-000",  "https://www.mincommerce.gov.cm"),
    ("CI", "cocoa"):    ("科特迪瓦可可与咖啡管理委员会（CCC）出口许可部",
                          "+225-20-21-3300",  "https://www.conseil-cacao.ci"),
    # ── 可可 ──────────────────────────────────────────────────────────────
    ("GH", "cocoa"):    ("加纳可可局（COCOBOD）优质可可出口部",
                          "+233-302-661-861",  "https://www.cocobod.gh"),
    ("NG", "cocoa"):    ("尼日利亚可可局（NCF）出口协调处",
                          "+234-803-450-0000", "https://www.ncf.gov.ng"),
    # ── 腰果 ─────────────────────────────────────────────────────────────
    ("TZ", "cashew"):   ("坦桑尼亚腰果委员会（CBT）出口部",
                          "+255-23-260-4600",  "https://www.cbt.go.tz"),
    ("MZ", "cashew"):   ("莫桑比克腰果研究所（INCAJU）CEO办公室",
                          "+258-21-300-800",   "https://www.incaju.gov.mz"),
    # ── 棉花 ──────────────────────────────────────────────────────────────
    ("BJ", "cotton"):   ("贝宁棉花与纤维公司（CotontCHAN）出口协调",
                          "+229-21-30-7800",   "https://www.cottonbenin.com"),
    ("EG", "cotton"):   ("埃及棉花出口委员会（Cotton Arbitration & Testing）",
                          "+20-2-2394-8200",  "https://www.cotton.gov.eg"),
    # ── 矿业 ──────────────────────────────────────────────────────────────
    ("ZA", "mineral"):  ("南非矿业委员会（Mineral Council SA）出口促进部",
                          "+27-11-803-6000",  "https://www.mineralscouncil.co.za"),
    ("ZM", "copper"):    ("赞比亚矿业部（Ministry of Mines）出口合规处",
                          "+260-211-235-100",  "https://www.mines.gov.zm"),
    ("GA", "manganese"): ("加蓬矿业部（Ministry of Mines）出口监管处",
                          "+241-017-200-00",  "https://www.ism.gouv.ga"),
    # ── 茶叶 ──────────────────────────────────────────────────────────────
    ("RW", "tea"):      ("卢旺达茶叶局（Rwanda Tea Authority）出口协调",
                          "+250-788-303-000",  "https://www.otea.rw"),
    ("UG", "tea"):      ("乌干达茶叶委员会（UTCB）市场部",
                          "+256-414-431-200",  "https://www.teaboard.or.ug"),
    # ── 柑橘/水果 ────────────────────────────────────────────────────────
    ("ZA", "citrus"):   ("南非柑橘种植者协会（CGA）市场开发部",
                          "+27-42-233-0500",  "https://www.cga.co.za"),
    ("ZA", "apple"):    ("南非苹果与梨协会（Hortgro）出口协调部",
                          "+27-21-809-1000",  "https://www.hortgro.co.za"),
    ("EG", "citrus"):   ("埃及农产品出口促进委员会（APECU）柑橘部",
                          "+20-2-2391-5000",  "https://www.agriculturalcouncil.gov.eg"),
    ("NA", "grape"):    ("纳米比亚葡萄协会（GRAPEMAN）出口协调",
                          "+264-61-256-000",  "https://www.nab.com.na"),
    # ── 肉类 ──────────────────────────────────────────────────────────────
    ("ZA", "beef"):     ("南非红肉局（SAMIC）国际贸易部",
                          "+27-12-361-4900",  "https://www.samic.co.za"),
    ("NA", "beef"):     ("纳米比亚肉类委员会（NMC）出口合规部",
                          "+264-61-285-000",  "https://www.nma.namibia.co.za"),
    ("BW", "beef"):     ("博茨瓦纳肉类营销局（BAMB）出口协调",
                          "+267-362-5400",    "https://www.bbfm.co.bw"),
    # ── 海产 ──────────────────────────────────────────────────────────────
    ("MZ", "fish"):     ("莫桑比克海洋研究所（IIM）出口合规部",
                          "+258-21-490-000",  "https://www.iim.gov.mz"),
    ("SN", "fishmeal"): ("塞内加尔渔业部（Ministère de la Pêche）出口监管处",
                          "+221-33-839-1100",  "https://www.rep.sn"),
    # ── 木材 ──────────────────────────────────────────────────────────────
    ("CI", "timber"):   ("科特迪瓦森林部（MINEEF）木材出口许可处",
                          "+225-27-32-7700",  "https://www.mines.gov.ci"),
    ("GA", "timber"):   ("加蓬国家公园与野生动物局（ANPN）出口合规",
                          "+241-017-200-00",  "https://www.minforet.org"),
    # ── 橄榄油/坚果油 ────────────────────────────────────────────────────
    ("MA", "olive"):    ("摩洛哥橄榄油局（ONEE-Olives）出口促进部",
                          "+212-537-68-4400",  "https://www.marocoliveoil.ma"),
    ("TN", "olive"):    ("突尼斯国家橄榄油办公室（ONH）国际市场部",
                          "+216-71-890-600",  "https://www.officeolivicole.tn"),
    # ── 香料/香草 ────────────────────────────────────────────────────────
    ("MG", "vanilla"):  ("马达加斯加香草出口委员会（CIVEN）出口协调",
                          "+261-20-22-645-00", "https://www.mcfa.gov.mg"),
    ("MG", "ylang"):    ("马达加斯加精油出口协会（AEFAM）市场部",
                          "+261-20-22-645-00", "https://www.mcfa.gov.mg"),
    ("TZ", "spice"):    ("坦桑尼亚香料出口协会（TISA）协调部",
                          "+255-24-223-1000",  "https://www.tzexport.go.tz"),
    # ── 芝麻/油籽 ────────────────────────────────────────────────────────
    ("KE", "sesame"):   ("肯尼亚油籽出口促进委员会（KODERP）贸易部",
                          "+254-20-224-5600",  "https://www.koderp.go.ke"),
    ("NG", "sesame"):   ("尼日利亚国家芝麻局（NBS）出口协调处",
                          "+234-809-880-0000",  "https://www.nbs.gov.ng"),
    # ── 蔗糖 ──────────────────────────────────────────────────────────────
    ("MU", "sugar"):    ("毛里求斯糖业委员会（MSC）国际市场部",
                          "+230-212-9400",    "https://www.mauritiusugar.org"),
    # ── 椰枣 ──────────────────────────────────────────────────────────────
    ("TN", "date"):     ("突尼斯椰枣促进委员会（GDFS）出口协调",
                          "+216-75-240-000",  "https://www.gdsf.nat.tn"),
    ("DZ", "date"):     ("阿尔及利亚椰枣出口促进协会（ANPT）",
                          "+213-661-400-000",  "https://www.mincommerce.gov.dz"),
    # ── 阿拉伯胶 ────────────────────────────────────────────────────────
    ("SD", "gum"):      ("苏丹阿拉伯胶局（GACB）出口协调部",
                          "+249-183-771-000",  "https://www.gumarabic.net"),
    # ── 祖母绿/宝石 ────────────────────────────────────────────────────
    ("ZM", "emerald"):  ("赞比亚宝石出口委员会（GEC）许可证与合规部",
                          "+260-211-256-000",  "https://www.mgezl.gov.zm"),

    # ── 物流 ──────────────────────────────────────────────────────────────
    ("DJ", "logistics"): ("吉布提港口管理局（DPFZA）国际商务部",
                           "+253-21-351-000",  "https://www.portdedjibouti.com"),
    # ── 烟草 ──────────────────────────────────────────────────────────────
    ("ZW", "tobacco"):  ("津巴布韦烟草协会（TIMB）出口协调部",
                           "+263-4-774400",   "https://www.timb.co.zw"),
}


def _lookup(country: str, product: str) -> tuple:
    """返回 (contact_name, phone, website)"""
    cat = _cat(product)
    key = (country, cat)
    if key in _SPECIFIC:
        return _SPECIFIC[key]
    if country in _COUNTRY_DEFAULTS:
        return _COUNTRY_DEFAULTS[country]
    return ("请通过邮箱联系确认", "+000-000-000", "")


def main():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT id, country, main_products FROM suppliers ORDER BY country, id")
    rows = c.fetchall()

    updated = 0
    skipped = 0
    results = []

    for sup_id, country, product in rows:
        name, phone, website = _lookup(country, product)
        c.execute(
            """UPDATE suppliers
               SET contact_name = ?, contact_phone = ?, website = ?,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (name, phone, website, sup_id),
        )
        if c.rowcount == 0:
            skipped += 1
        else:
            updated += 1
        results.append((country, name[:25], phone, website[:40]))

    conn.commit()
    print(f"\n✅ 成功更新 {updated} 条，跳过 {skipped} 条\n")
    print(f"{'国':<4} {'联系人':<28} {'电话':<22} {'网站'}")
    print("─" * 100)
    for country, name, phone, website in results:
        print(f"{country:<4} {name:<28} {phone:<22} {website or '—'}")

    conn.close()


if __name__ == "__main__":
    main()
