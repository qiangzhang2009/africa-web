"""
Pipeline 主运行脚本
一键执行：爬虫抓取 → SQLite 写入 → 静态 JSON 导出

使用方式：
    python -m pipeline.run              # 执行全流程
    python -m pipeline.run --scrapers hs_codes countries  # 指定爬虫
    python -m pipeline.run --sqlite-only # 仅写入 SQLite
    python -m pipeline.run --export-only # 仅导出静态文件
    python -m pipeline.run --dry-run     # 预览，不执行
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
from rich import print as rprint

# 添加 backend 目录到 path，确保可导入 scrapers
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.runner import run_all as run_scrapers, run_by_name
from pipeline.writer import SQLiteWriter
from pipeline.exporter import StaticExporter

console = Console()
log = logging.getLogger("pipeline")


# ── 默认路径配置 ───────────────────────────────────────────────────────────────
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "africa_zero.db"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "static_data"


def _save_pipeline_report(results: dict, output_dir: Path):
    """保存 pipeline 运行报告。"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / "results" / f"pipeline_{ts}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    log.info(f"Pipeline 报告已保存：{report_path}")


def _print_pipeline_summary(scraper_results: list, writer_summaries: list, export_paths: list):
    """打印 pipeline 运行摘要。"""
    # 爬虫摘要
    scraper_table = Table(title="爬虫执行结果")
    scraper_table.add_column("爬虫", style="cyan")
    scraper_table.add_column("状态", style="white")
    scraper_table.add_column("记录数", justify="right")
    scraper_table.add_column("耗时(s)", justify="right")
    for r in scraper_results:
        icon = "[green]✓[/green]" if r["status"] == "success" else "[red]✗[/red]"
        scraper_table.add_row(
            r["scraper"], icon,
            str(r["records_count"]),
            f"{r['elapsed_seconds']:.1f}",
        )
    console.print(scraper_table)

    # SQLite 写入摘要
    if writer_summaries:
        writer_table = Table(title="SQLite 写入结果")
        writer_table.add_column("表", style="cyan")
        writer_table.add_column("成功", justify="right", style="green")
        writer_table.add_column("错误", justify="right", style="yellow")
        writer_table.add_column("总计", justify="right")
        for s in writer_summaries:
            if "error" not in s:
                writer_table.add_row(
                    s.get("table", "?"),
                    str(s.get("inserted", 0)),
                    str(s.get("errors", 0)),
                    str(s.get("total", 0)),
                )
        console.print(writer_table)

    # 导出摘要
    if export_paths:
        export_table = Table(title="静态文件导出结果")
        export_table.add_column("文件", style="cyan")
        export_table.add_column("路径", style="dim")
        for p in export_paths:
            export_table.add_row(p.name, str(p))
        console.print(export_table)


async def run_pipeline(
    scraper_names: list[str] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    write_sqlite: bool = True,
    export_static: bool = True,
) -> dict:
    """
    执行完整的 pipeline：
    1. 运行爬虫
    2. 写入 SQLite（可选）
    3. 导出静态 JSON（可选）
    """
    console.print(f"\n[bold cyan]AfricaZero Pipeline 开始执行[/bold cyan]")
    console.print(f"  SQLite 路径: {db_path}")
    console.print(f"  静态文件目录: {output_dir}\n")

    # ── Step 1: 运行爬虫 ──────────────────────────────────────────────────────
    scraper_results: list[dict] = []

    if scraper_names:
        # 运行指定爬虫
        for name in scraper_names:
            try:
                result = await run_by_name(name)
                scraper_results.append(result)
            except Exception as e:
                log.error(f"运行爬虫 {name} 失败：{e}")
                scraper_results.append({
                    "scraper": name, "status": "failed", "error": str(e),
                    "records_count": 0, "records": [], "elapsed_seconds": 0,
                })
    else:
        # 运行全部爬虫
        scraper_results = await run_scrapers()

    # ── Step 2: 写入 SQLite ──────────────────────────────────────────────────
    writer_summaries: list = []
    if write_sqlite:
        console.print("\n[bold]Step 2: 写入 SQLite 数据库[/bold]")
        writer = SQLiteWriter(db_path)
        writer_summaries = writer.write_all_results(scraper_results)

        stats = writer.get_table_stats()
        stats_table = Table(title="SQLite 表行数统计")
        stats_table.add_column("表名", style="cyan")
        stats_table.add_column("行数", justify="right")
        for table, count in stats.items():
            color = "green" if count > 0 else "yellow"
            stats_table.add_row(table, f"[{color}]{count}[/{color}]")
        console.print(stats_table)

    # ── Step 3: 导出静态文件 ────────────────────────────────────────────────
    export_paths: list = []
    if export_static:
        console.print("\n[bold]Step 3: 导出静态 JSON 文件[/bold]")
        exporter = StaticExporter(output_dir)
        export_paths = exporter.export_all_results(scraper_results)

    # ── Step 4: 保存报告 ────────────────────────────────────────────────────
    report = {
        "run_at": datetime.now().isoformat(),
        "scrapers": [
            {"scraper": r["scraper"], "status": r["status"],
             "records_count": r["records_count"], "elapsed_seconds": r["elapsed_seconds"]}
            for r in scraper_results
        ],
        "sqlite_writes": writer_summaries,
        "exported_files": [str(p) for p in export_paths],
    }
    _save_pipeline_report(report, output_dir)

    # ── 打印摘要 ─────────────────────────────────────────────────────────────
    _print_pipeline_summary(scraper_results, writer_summaries, export_paths)

    success_count = sum(1 for r in scraper_results if r["status"] == "success")
    total_count = len(scraper_results)
    console.print(f"\n[bold]Pipeline 执行完成：{success_count}/{total_count} 个爬虫成功[/bold]")
    console.print(f"[dim]详细报告已保存至 {output_dir}/results/[/dim]\n")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="AfricaZero Pipeline — 爬虫→SQLite→静态文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--scrapers",
        nargs="+",
        help="指定运行的爬虫名称，如：hs_codes countries freight",
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help=f"SQLite 数据库路径（默认 {DEFAULT_DB_PATH}）",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"静态文件输出目录（默认 {DEFAULT_OUTPUT_DIR}）",
    )
    parser.add_argument(
        "--sqlite-only",
        action="store_true",
        help="跳过爬虫，仅使用现有数据库数据导出静态文件",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="仅导出静态文件（假设爬虫已运行，数据在 static_data/）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不写入数据库也不导出文件",
    )
    args = parser.parse_args()

    if args.export_only:
        # 仅导出模式：从现有 static_data/ 读取已爬取的数据，导出为前端可用格式
        console.print("[bold cyan]Export-Only 模式[/bold cyan]")
        from pathlib import Path
        input_dir = Path(args.output)
        export_paths = []
        for json_file in input_dir.glob("*.json"):
            console.print(f"  发现数据文件：{json_file.name}")
            export_paths.append(json_file)
        console.print(f"\n[yellow]Export-only 模式待实现：[/yellow]")
        console.print("  请先运行完整 pipeline 生成数据，或将已有数据放入 static_data/ 目录")
        return

    if args.dry_run:
        console.print("[yellow]Dry-run 模式：仅预览，不执行[/yellow]")
        console.print(f"  数据库路径: {args.db}")
        console.print(f"  输出目录: {args.output}")
        if args.scrapers:
            console.print(f"  指定爬虫: {', '.join(args.scrapers)}")
        else:
            console.print("  爬虫: 全部")
        return

    db_path = Path(args.db)
    output_dir = Path(args.output)

    if args.sqlite_only:
        # 从 static_data 读取已生成的文件，写入 SQLite
        console.print("[bold cyan]SQLite-Only 模式[/bold cyan]")
        writer = SQLiteWriter(db_path)
        # 读取 static_data/*.json 并写入
        results = []
        for json_file in sorted(output_dir.glob("*.json")):
            data = json.loads(json_file.read_text())
            # 映射文件名到数据类型
            name_map = {
                "countries.json": "africa_countries",
                "hs_codes.json": "hs_codes",
                "freight_routes.json": "freight_routes",
                "cert_guides.json": "cert_guides",
                "market_products.json": "market_analysis",
                "suppliers.json": "suppliers",
            }
            data_type = name_map.get(json_file.name)
            if data_type:
                # 提取 data 字段
                records = data.get("data", data.get("results", data.get("products",
                          data.get("suppliers", data.get("countries", [])))))
                results.append({"data_type": data_type, "records": records, "status": "success"})
        summaries = writer.write_all_results(results)
        stats = writer.get_table_stats()
        console.print(f"\n[green]SQLite 写入完成[/green]")
        for table, count in stats.items():
            console.print(f"  {table}: {count} 行")
        return

    # 完整 pipeline
    report = asyncio.run(run_pipeline(
        scraper_names=args.scrapers,
        db_path=db_path,
        output_dir=output_dir,
    ))


if __name__ == "__main__":
    main()
