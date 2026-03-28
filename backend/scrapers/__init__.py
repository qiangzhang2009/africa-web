"""
AfricaZero Scraper Framework
============================
统一爬虫框架，基于 Scrapling 引擎。
支持：HS编码、非洲国家、船运路线、证书指南、供应商、市场分析 等数据源。

使用方式：
    from scrapers.runner import run_all, run_by_name

    # 运行所有爬虫
    await run_all()

    # 运行指定爬虫
    await run_by_name("hs_codes")
    await run_by_name("countries")
"""
