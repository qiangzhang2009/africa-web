"""
统一运行器 — 管理和执行所有爬虫

使用方式：
    python -m scrapers.runner           # 运行所有
    python -m scrapers.runner --name hs_codes  # 运行指定
    python -m scrapers.runner --list   # 列出所有爬虫
    python -m scrapers.runner --dry-run # 仅列出，不执行
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from scrapers.base import ScraperBase

console = Console()
log = logging.getLogger("runner")

# ── 延迟导入爬虫，避免循环依赖 ────────────────────────────────────────────────

SCRAPER_REGISTRY: dict[str, type[ScraperBase]] = {}


def _load_scrapers():
    """延迟加载所有爬虫模块，注册到全局表。"""
    global SCRAPER_REGISTRY
    if SCRAPER_REGISTRY:
        return
    from scrapers.hs_codes import HSScraper
    from scrapers.countries import CountriesScraper
    from scrapers.freight import FreightScraper
    from scrapers.cert_guides import CertGuideScraper
    from scrapers.market_analysis import MarketAnalysisScraper
    from scrapers.suppliers import SupplierScraper

    for cls in (HSScraper, CountriesScraper, FreightScraper,
                CertGuideScraper, MarketAnalysisScraper, SupplierScraper):
        SCRAPER_REGISTRY[cls.name] = cls


# ── 运行结果持久化 ─────────────────────────────────────────────────────────────

def _save_run_results(results: list[dict], output_dir: Path):
    """将运行结果写入 output_dir/results/ 目录。"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = output_dir / f"run_{ts}_summary.json"
    summary = {
        "run_at": datetime.now().isoformat(),
        "scrapers": [
            {
                "scraper": r["scraper"],
                "data_type": r["data_type"],
                "records_count": r["records_count"],
                "elapsed_seconds": r["elapsed_seconds"],
                "status": r["status"],
            }
            for r in results
        ]
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    log.info(f"运行摘要已保存：{summary_path}")
    console.print(f"\n[dim]运行摘要已保存至 {summary_path}[/dim]")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AfricaZero Scraper Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--name", "-n",
        help="指定运行单个爬虫（如 hs_codes）",
    )
    parser.add_argument(
        "--list", "-l", action="store_true",
        help="列出所有已注册的爬虫",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅列出，不执行",
    )
    parser.add_argument(
        "--output", "-o",
        default="static_data",
        help="静态数据输出目录（默认 static_data）",
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=int, default=3,
        help="并发爬虫数（默认 3）",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int, default=30,
        help="单次请求超时秒数（默认 30）",
    )
    args = parser.parse_args()

    _load_scrapers()

    # ── 列出爬虫 ──────────────────────────────────────────────────────────────
    if args.list:
        table = Table(title="已注册的爬虫")
        table.add_column("名称", style="cyan")
        table.add_column("描述", style="white")
        table.add_column("数据类型", style="green")
        for name, cls in SCRAPER_REGISTRY.items():
            table.add_row(name, cls.description, cls.data_type)
        console.print(table)
        return

    # ── 确定要运行的爬虫列表 ─────────────────────────────────────────────────
    if args.name:
        if args.name not in SCRAPER_REGISTRY:
            console.print(f"[red]未知爬虫：{args.name}[/red]")
            console.print(f"[dim]可用：{', '.join(SCRAPER_REGISTRY.keys())}[/dim]")
            sys.exit(1)
        names = [args.name]
    else:
        names = list(SCRAPER_REGISTRY.keys())

    if args.dry_run:
        console.print(f"[yellow]Dry-run 模式，仅列出待执行爬虫：[/yellow]")
        for name in names:
            cls = SCRAPER_REGISTRY[name]
            console.print(f"  • {name}  — {cls.description}")
        return

    # ── 执行爬虫 ──────────────────────────────────────────────────────────────
    output_dir = Path(args.output)

    console.print(f"\n[bold cyan]AfricaZero Scraper Runner[/bold cyan]")
    console.print(f"  并发数: {args.concurrency}  |  超时: {args.timeout}s  |  输出: {output_dir}\n")

    results: list[dict] = []
    semaphore = asyncio.Semaphore(args.concurrency)

    async def run_one(name: str) -> dict:
        async with semaphore:
            cls = SCRAPER_REGISTRY[name]
            scraper = cls(timeout=args.timeout)
            result = await scraper.run()
            # 将爬取结果写入对应数据文件
            if result["records"] and result["status"] == "success":
                _write_data_file(output_dir, result)
            results.append(result)
            return result

    async def run_all():
        tasks = [run_one(name) for name in names]
        await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.run(run_all())

    # ── 摘要报告 ──────────────────────────────────────────────────────────────
    _save_run_results(results, output_dir / "results")
    _print_summary(results)


def _write_data_file(output_dir: Path, result: dict):
    """将爬取结果写入 static_data/{data_type}.json"""
    data_type = result["data_type"]
    file_path = output_dir / f"{data_type}.json"
    data = {
        "updated_at": result["finished_at"],
        "source": result["scraper"],
        "count": len(result["records"]),
        "data": result["records"],
    }
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def _print_summary(results: list[dict]):
    table = Table(title="运行结果汇总")
    table.add_column("爬虫", style="cyan")
    table.add_column("状态", style="white")
    table.add_column("记录数", justify="right")
    table.add_column("耗时(s)", justify="right")

    for r in results:
        status_icon = "[green]✓[/green]" if r["status"] == "success" else "[red]✗[/red]"
        table.add_row(
            r["scraper"],
            status_icon,
            str(r["records_count"]),
            f"{r['elapsed_seconds']:.1f}",
        )
    console.print(table)

    total = len(results)
    ok = sum(1 for r in results if r["status"] == "success")
    console.print(f"\n[bold]总计：{ok}/{total} 个爬虫成功[/bold]")


# ── 便捷函数（供 pipeline 调用）───────────────────────────────────────────────

async def run_all(timeout: int = 30, concurrency: int = 3) -> list[dict]:
    """运行所有爬虫，返回结果列表。"""
    _load_scrapers()
    results = []
    semaphore = asyncio.Semaphore(concurrency)

    async def run_one(name: str) -> dict:
        async with semaphore:
            cls = SCRAPER_REGISTRY[name]
            scraper = cls(timeout=timeout)
            result = await scraper.run()
            results.append(result)
            return result

    await asyncio.gather(*[run_one(name) for name in SCRAPER_REGISTRY])
    return results


async def run_by_name(name: str, timeout: int = 30) -> dict:
    """运行指定名称的爬虫。"""
    _load_scrapers()
    if name not in SCRAPER_REGISTRY:
        raise ValueError(f"未知爬虫：{name}，可用：{', '.join(SCRAPER_REGISTRY.keys())}")
    scraper = SCRAPER_REGISTRY[name](timeout=timeout)
    return await scraper.run()


if __name__ == "__main__":
    main()
