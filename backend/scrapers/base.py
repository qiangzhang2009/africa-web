"""
ScraperBase — 所有爬虫的基类
定义统一接口、统一错误处理、统一日志格式。
"""
from __future__ import annotations

import asyncio
import logging
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("scraper")


class ScraperBase(ABC):
    """
    所有爬虫必须继承此类并实现 scrape() 方法。

    类属性（子类必须定义）：
        name        : str   - 爬虫名称，用于注册表
        description : str   - 爬虫描述
        data_type   : str   - 数据类型标识
        source_url  : str   - 数据来源 URL

    使用示例：
        class HSScraper(ScraperBase):
            name = "hs_codes"
            description = "爬取中国海关HS编码数据库"
            data_type = "hs_codes"
            source_url = "https://www.hscode.net/..."

            async def scrape(self) -> list[dict]:
                ...  # 实现具体逻辑
    """

    name: str = ""
    description: str = ""
    data_type: str = ""
    source_url: str = ""

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self._stats: dict[str, int] = {"success": 0, "failed": 0, "skipped": 0}
        self._started_at: Optional[datetime] = None

    # ── HTTP 客户端 ────────────────────────────────────────────────────────────

    def _client_kwargs(self) -> dict[str, Any]:
        """返回 httpx.AsyncClient 的通用参数。"""
        return {
            "timeout": httpx.Timeout(self.timeout, connect=10),
            "headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept": "application/json, text/html, */*",
            },
            "follow_redirects": True,
        }

    async def _get(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> httpx.Response:
        """带重试的 GET 请求。"""
        kwargs = self._client_kwargs()
        if headers:
            kwargs["headers"].update(headers)

        async with httpx.AsyncClient(**kwargs) as client:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    return response
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in (429, 500, 502, 503, 504):
                        wait = 2 ** attempt
                        log.warning(
                            f"[{self.name}] {url} → HTTP {e.response.status_code}，"
                            f" {attempt}/{self.max_retries} 次重试，{wait}s 后重试"
                        )
                        await asyncio.sleep(wait)
                        continue
                    raise
                except httpx.RequestError as e:
                    if attempt < self.max_retries:
                        wait = 2 ** attempt
                        log.warning(
                            f"[{self.name}] {url} → {type(e).__name__}，"
                            f" {attempt}/{self.max_retries} 次重试，{wait}s 后重试"
                        )
                        await asyncio.sleep(wait)
                        continue
                    raise
        raise RuntimeError("重试耗尽，无法获取响应")

    async def _post(
        self,
        url: str,
        json: Optional[dict] = None,
        data: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> httpx.Response:
        """带重试的 POST 请求。"""
        kwargs = self._client_kwargs()
        if headers:
            kwargs["headers"].update(headers)

        async with httpx.AsyncClient(**kwargs) as client:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await client.post(url, json=json, data=data)
                    response.raise_for_status()
                    return response
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in (429, 500, 502, 503, 504):
                        wait = 2 ** attempt
                        log.warning(
                            f"[{self.name}] {url} → HTTP {e.response.status_code}，"
                            f" {attempt}/{self.max_retries} 次重试，{wait}s 后重试"
                        )
                        await asyncio.sleep(wait)
                        continue
                    raise
                except httpx.RequestError as e:
                    if attempt < self.max_retries:
                        wait = 2 ** attempt
                        log.warning(
                            f"[{self.name}] {url} → {type(e).__name__}，"
                            f" {attempt}/{self.max_retries} 次重试，{wait}s 后重试"
                        )
                        await asyncio.sleep(wait)
                        continue
                    raise
        raise RuntimeError("重试耗尽，无法获取响应")

    # ── 子类必须实现 ───────────────────────────────────────────────────────────

    @abstractmethod
    async def scrape(self) -> list[dict]:
        """
        执行爬取逻辑，返回记录列表。
        每条记录是一个 dict，键对应数据库表字段。
        """
        ...

    # ── 通用流程 ───────────────────────────────────────────────────────────────

    async def run(self) -> dict[str, Any]:
        """
        执行爬虫的标准流程：
        1. 记录开始时间
        2. 调用 scrape()
        3. 记录统计信息
        4. 返回结果摘要
        """
        self._started_at = datetime.now()
        log.info(f"[{self.name}] 开始爬取：{self.description}")
        console.print(
            f"[dim]  来源：[/dim]{self.source_url}", style="bold blue"
        )

        try:
            records = await self._run_with_progress()
            self._stats["success"] = len(records)
            elapsed = (datetime.now() - self._started_at).total_seconds()

            log.info(
                f"[{self.name}] 完成：获取 {len(records)} 条记录，"
                f"耗时 {elapsed:.1f}s"
            )
            console.print(
                f"[green]✓[/green] [{self.name}] "
                f"成功 {len(records)} 条 | "
                f"失败 {self._stats['failed']} 条 | "
                f"耗时 {elapsed:.1f}s"
            )

            return {
                "scraper": self.name,
                "data_type": self.data_type,
                "records_count": len(records),
                "records": records,
                "elapsed_seconds": round(elapsed, 2),
                "started_at": self._started_at.isoformat(),
                "finished_at": datetime.now().isoformat(),
                "status": "success",
            }

        except Exception as e:
            elapsed = (
                (datetime.now() - self._started_at).total_seconds()
                if self._started_at
                else 0
            )
            log.error(f"[{self.name}] 爬取失败：{e}", exc_info=True)
            console.print(f"[red]✗[/red] [{self.name}] 失败：{e}")
            return {
                "scraper": self.name,
                "data_type": self.data_type,
                "records_count": 0,
                "records": [],
                "elapsed_seconds": round(elapsed, 2),
                "started_at": self._started_at.isoformat() if self._started_at else None,
                "finished_at": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e),
            }

    async def _run_with_progress(self) -> list[dict]:
        """
        带进度条显示的执行包装。
        子类可覆盖此方法以自定义进度报告。
        """
        records: list[dict] = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]正在爬取 {self.name}...[/cyan]", total=None
            )
            records = await self.scrape()
            progress.update(task, completed=True)
        return records

    # ── 工具方法 ───────────────────────────────────────────────────────────────

    @staticmethod
    def normalize_hs(code: str) -> str:
        """标准化 HS 编码：移除点、空格、横杠。"""
        return code.replace(".", "").replace(" ", "").replace("-", "")

    @staticmethod
    def format_hs(code: str) -> str:
        """将标准化的 HS 编码格式化为带点的形式。"""
        c = code.replace(".", "").replace(" ", "").replace("-", "")
        if len(c) <= 4:
            return c
        return ".".join(c[i * 2 : i * 2 + 2] for i in range((len(c) + 1) // 2))

    @staticmethod
    def ts_now() -> str:
        """返回当前时间戳字符串（与数据库 updated_at 格式一致）。"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
