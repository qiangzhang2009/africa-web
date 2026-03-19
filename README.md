# AfricaZero · 非洲零关税全链路决策平台

> 全球首款非洲原产地 × 多市场关税套利决策平台

## 产品定位

**一句话**：不是"查关税的工具"，而是"告诉我这批货从非洲进，能不能做，在哪里卖最划算"。

## 功能

- 多市场关税计算器（中国零关税 + 欧盟EPA估算 + AfCFTA估算）
- 非洲进口成本精算器（FOB→到岸→回本测算）
- HS编码智能查询
- AI原产地合规自测（DeepSeek）
- 53国白名单查询
- 会员订阅系统

## 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | React 18 + Vite + Tailwind CSS + TypeScript |
| 后端 | FastAPI (Python 3.11+) |
| 数据库 | SQLite（零运维） |
| AI | DeepSeek API（可选） |
| 部署 | Vercel（前端）+ Render（后端） |

## 快速启动

### 前端

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

### 后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 启动开发服务器（自动初始化数据库）
uvicorn app.main:app --reload --port 8000
# API 文档：http://localhost:8000/docs
```

## 部署

前端推送到 main 分支后，GitHub Actions 自动部署到 Vercel。
后端推送到 main 分支后，GitHub Actions 自动部署到 Render。

## 环境变量

| 变量 | 说明 |
|---|---|
| `DEEPSEEK_API_KEY` | DeepSeek API Key（可选） |
| `DATABASE_URL` | SQLite 数据库路径 |
| `CORS_ORIGINS` | 允许的跨域来源 |
| `VITE_API_URL` | 后端 API 地址（前端构建时用） |

## API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/calculate/tariff` | 关税计算 |
| POST | `/api/v1/calculate/import-cost` | 进口成本精算 |
| GET | `/api/v1/hs-codes/search` | HS编码查询 |
| POST | `/api/v1/origin/check` | 原产地AI判定 |
| GET | `/api/v1/countries` | 国家列表 |
| GET | `/api/v1/subscribe/check` | 订阅状态 |

---

*© 2026 AfricaZero. 数据仅供参考，不构成法律建议。*
