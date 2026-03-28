# AfricaZero Scraping & Data Pipeline

## 架构概览

```
数据源（网页/API）
       ↓
  Scrapling 爬虫
       ↓
  SQLite 数据库  ←  本地存储
       ↓
  静态 JSON 文件  ←  前端直接读取
       ↓
  前端静态部署（无需后端 API）
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements-scrapers.txt
```

### 2. 运行完整 Pipeline（爬虫 → SQLite → 静态文件）

```bash
python -m pipeline.run
```

输出示例：

```
AfricaZero Pipeline 开始执行
  SQLite 路径: /path/to/data/africa_zero.db
  静态文件目录: /path/to/static_data

[hs_codes] 开始爬取：爬取 HS 编码及税率数据
✓ [hs_codes] 成功 27 条 | 失败 0 条 | 耗时 1.2s
...
```

### 3. 查看所有可用爬虫

```bash
python -m scrapers.runner --list
```

### 4. 运行指定爬虫

```bash
# 仅运行 HS 编码爬虫
python -m pipeline.run --scrapers hs_codes

# 仅运行国家数据爬虫
python -m pipeline.run --scrapers countries

# 运行多个
python -m pipeline.run --scrapers hs_codes countries freight
```

### 5. 预览模式（不执行）

```bash
python -m pipeline.run --dry-run
```

### 6. 仅导出静态文件（假设已有数据）

```bash
python -m pipeline.run --export-only
```

## 静态数据 → 前端部署

```bash
cd frontend
npm run build   # 自动将 static_data/*.json 复制到 dist/data/
# 将 dist/ 部署到 Vercel / Cloudflare Pages / GitHub Pages
```

## 数据更新流程

```
1. 运行爬虫：    python -m pipeline.run
2. 审核数据：    检查 static_data/*.json 中的数据是否正确
3. 构建前端：    cd frontend && npm run build
4. 部署：        将 dist/ 部署到生产环境
```

## 内置数据 vs 真实爬取

所有爬虫都实现了**降级策略**：

| 爬虫 | 内置数据 | 真实数据源 |
|------|---------|-----------|
| `hs_codes` | ✅ 27 条样本 HS 编码 | ITC TradeMap API（需申请 API Key） |
| `countries` | ✅ 54 个非洲国家 | AfCFTA 官方数据（需解析页面） |
| `freight` | ✅ 15 条样本路线 | Freightos FBX API（需付费订阅） |
| `cert_guides` | ✅ 12 个国家指南 | 各国商会官网（需逐个维护） |
| `market_analysis` | ✅ 10 个品类分析 | ITC TradeMap（需 API Key） |
| `suppliers` | ✅ 8 个样本供应商 | Afreximbank / 贸促机构（需认证） |

## 配置真实数据源

### ITC TradeMap API
```bash
export TRADEMAP_API_KEY="your_api_key_here"
```

### Freightos FBX API
```bash
export FREIGHTOS_API_KEY="your_api_key_here"
```

## 扩展新的爬虫

1. 在 `scrapers/` 目录创建新文件，如 `scrapers/my_data.py`
2. 继承 `ScraperBase` 并实现 `scrape()` 方法
3. 在 `scrapers/runner.py` 的 `_load_scrapers()` 中注册

```python
from scrapers.base import ScraperBase

class MyDataScraper(ScraperBase):
    name = "my_data"
    description = "我的数据"
    data_type = "my_table"
    source_url = "https://example.com"

    async def scrape(self) -> list[dict]:
        # 实现爬取逻辑
        return records
```

## 添加新的数据类型到 Pipeline

1. 在 `scrapers/` 创建爬虫类
2. 在 `pipeline/writer.py` 的 `_TABLE_MAPPING` 添加 INSERT SQL
3. 在 `pipeline/exporter.py` 的 `filename_map` 添加文件名映射
4. 在前端 `frontend/src/data/local.ts` 添加对应的加载函数
5. 将对应页面中的 API 调用替换为 `localData` 调用
