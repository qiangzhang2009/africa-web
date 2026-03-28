# AfricaZero · 非洲零关税全链路决策平台

## 项目概述

**产品定位**：全球首款非洲原产地 × 多市场关税套利决策平台。

**一句话说明**：不是"查关税的工具"，而是"告诉我这批货从非洲进，能不能做，在哪里卖最划算"。

**线上地址**：`https://africa.zxqconsulting.com`

---

## 技术架构

```
用户浏览器
    │
    ▼
前端静态资源 (Vercel) — africa.zxqconsulting.com
    │
    │  /api/* → Vercel rewrite → Render 后端
    ▼
后端 API (FastAPI on Render) — africa-web-wuxs.onrender.com
    │
    ▼
Neon PostgreSQL 数据库（云端）
```

### 技术栈

| 层级 | 技术 | 说明 |
|---|---|---|
| 前端 | React 18 + Vite + Tailwind CSS + TypeScript | SPA，路由：React Router v6 |
| 状态管理 | Zustand + persist middleware | localStorage 持久化 |
| 后端 | FastAPI (Python 3.11+) | 全部同步函数，asynccontextmanager 管理生命周期 |
| 数据库 | Neon PostgreSQL（生产）+ SQLite（本地开发） | 驱动：psycopg2 + sqlite3，DB 自动适配 |
| AI | DeepSeek API（可选） | 原产地合规性 AI 判定 |
| 前端监控 | zxqTrack SDK | 用户行为分析 |
| 部署 | Vercel（前端）+ Render（后端 API） | 均推送 main 分支自动触发 |

### 前端登录状态恢复（无需等待 API）

JWT payload 是 base64url 编码的 JSON，前端使用纯 JS `atob()` 即时解码 token，页面加载后立即恢复用户状态（tier、email、is_admin），800ms 后再发后台 API 校验并同步剩余配额。参见 `frontend/src/utils/jwt.ts`。

---

## 目录结构

```
africa-zero/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口，路由挂载，CORS 配置，lifespan
│   │   ├── schemas/__init__.py     # Pydantic 请求/响应模型
│   │   ├── models/
│   │   │   └── database.py         # DB 连接层、表定义（SQLite+PG 双语）、
│   │   │                           #   init_db()、迁移、种子数据、密码哈希
│   │   └── routers/
│   │       ├── auth.py             # 登录/注册/JWT/子账号/日频次
│   │       ├── calculator.py        # 关税计算 + 进口成本精算
│   │       ├── hs_codes.py         # HS 编码模糊搜索
│   │       ├── countries.py        # 非洲国家基础数据
│   │       ├── subscribe.py        # 订阅查询
│   │       ├── subscription.py     # 订阅管理（创建/升级）
│   │       ├── api_keys.py         # API Key CRUD（企业版）
│   │       ├── admin.py            # 管理后台（用户列表/统计/人工开通订阅）
│   │       ├── freight.py          # 物流路线查询 + 运费估算
│   │       ├── certificate.py      # 原产地证书指南 + AI 申请 + 文档生成
│   │       ├── suppliers.py        # 供应商发现 + 评价 + 比价
│   │       ├── market_analysis.py  # 市场选品分析
│   │       └── debug_routes.py    # Debug 端点（db-status、upsert-data）
│   ├── data/                       # 本地 SQLite 数据库（africa_zero.db）
│   ├── scrapers/                   # 数据爬取脚本（国家、HS 编码、供应商等）
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── render.yaml                 # Render 部署配置
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # 路由定义 + AuthBootstrap + TrackPageView
│   │   ├── types/index.ts          # 所有 TypeScript 接口（API 请求/响应类型）
│   │   ├── utils/
│   │   │   ├── api.ts              # Axios 实例 + 所有 API 调用函数
│   │   │   └── jwt.ts              # 纯 JS JWT 解码（即时恢复登录状态）
│   │   ├── hooks/
│   │   │   ├── useAppStore.ts      # Zustand store（认证/订阅/兴趣清单/配额）
│   │   │   ├── useTrackInit.ts     # zxqTrack SDK 初始化
│   │   │   └── useFreeLimit.ts    # 免费配额拦截逻辑
│   │   ├── pages/
│   │   │   ├── HomePage.tsx        # 首页（功能介绍 + 立即开始）
│   │   │   ├── CalculatorPage.tsx  # 多市场关税计算器
│   │   │   ├── CostCalculatorPage.tsx  # 进口成本精算器
│   │   │   ├── HSLookupPage.tsx    # HS 编码智能查询
│   │   │   ├── OriginCheckPage.tsx # 原产地 AI 自测
│   │   │   ├── PolicyPage.tsx      # 53 国政策白名单
│   │   │   ├── PricingPage.tsx     # 定价页
│   │   │   ├── DashboardPage.tsx   # 用户仪表盘
│   │   │   ├── ProductDiscoveryPage.tsx # 市场选品
│   │   │   ├── GettingStartedPage.tsx   # 新手入门
│   │   │   ├── LoginPage.tsx / RegisterPage.tsx
│   │   │   ├── AccountPage.tsx     # 账号中心（订阅/API Key/子账号）
│   │   │   ├── AdminPage.tsx       # 管理后台（用户管理）
│   │   │   ├── FreightPage.tsx      # 物流路线
│   │   │   ├── CertificatePage.tsx  # 原产地证书
│   │   │   └── SuppliersPage.tsx   # 供应商发现
│   │   └── components/
│   │       ├── Layout.tsx          # 主布局（侧边栏 + 顶部导航）
│   │       ├── ResourcesSection.tsx # 资源链接
│   │       └── InterestListPanel.tsx # 兴趣产品清单（侧滑面板）
│   ├── public/
│   ├── vercel.json                 # Vercel rewrite 规则（/api/* → Render）
│   └── package.json
│
├── README.md
└── render.yaml
```

---

## 前端状态管理（Zustand）

### useAppStore — 完整状态结构

```typescript
interface AppState {
  // 认证
  currentUser: UserResponse | null    // 从 JWT payload 解码，即时恢复
  isLoggedIn: boolean
  tier: 'free' | 'pro' | 'enterprise'
  remainingToday: number              // 免费版剩余查询次数
  maxFreeDaily: 3
  dailyFreeQueries: number
  counter: { date, remaining, totalUsed }

  // 兴趣清单（HS 编码收藏）
  interestList: InterestItem[]

  // 方法
  setAuth(token, user): void         // 登录成功后调用，存 token + 更新状态
  logout(): void                     // 清除 localStorage + 清除 JWT cache
  updateUser(user): void             // 从 /auth/me 同步最新用户信息
  decrementFreeQuery(): void         // 调用计算接口前扣减配额
  syncRemainingFromServer(n): void   // 从 /auth/daily-usage 同步服务器配额
  syncCounter(): void                // 每日零点重置配额
  addToInterestList / removeFromInterestList: void
}
```

**持久化**：`localStorage` key = `africa-app-store`，通过 `partialize` 只持久化必要字段。

**登录流程**（两阶段，无感恢复）：
1. **即时（0ms）**：从 `localStorage` 读 token → `jwt.decode()` 解码 payload → 恢复 `currentUser`/`tier`，UI 立即可交互
2. **后台（800ms 后）**：`Promise.all([/auth/me, /auth/daily-usage])` → 同步最新用户信息和配额

### 前端配额限制（免费版）

`useFreeLimit.ts` hook 在以下页面拦截未登录/配额耗尽用户：
- `CalculatorPage`（关税计算）
- `CostCalculatorPage`（进口成本）
- `HSLookupPage`（HS 查询，每 10 次算 1 次配额）
- `OriginCheckPage`（AI 原产地判定，每次消耗 1 次）

---

## 后端 API 完整列表

所有路由挂载在 `/api/v1` 前缀（通过 `app.include_router(..., prefix="/api/v1")`）。

### 认证 `/api/v1/auth`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/auth/register` | ❌ | 注册（默认 free 用户） |
| POST | `/auth/login` | ❌ | 登录，返回 JWT |
| GET | `/auth/me` | ✅ | 获取当前用户信息 |
| GET | `/auth/daily-usage` | ✅ | 查询今日剩余配额 |

### 子账号 `/api/v1/sub-accounts`（仅 enterprise tier）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/sub-accounts` | ✅ enterprise | 列出当前企业的所有子账号 |
| POST | `/sub-accounts` | ✅ enterprise | 创建子账号（上限 5 个） |
| DELETE | `/sub-accounts/{sub_id}` | ✅ enterprise | 软删除子账号 |

### 订阅 `/api/v1/subscribe`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/subscribe/check` | ❌ | 查询订阅状态（按 email 或 wechat_id） |
| GET | `/subscribe/status` | ✅ | 获取当前登录用户的订阅详情 |
| POST | `/subscribe/create` | ✅ | 创建/升级订阅 |
| GET | `/subscribe/history` | ✅ | 订阅历史记录 |

### API Key `/api/v1/api-keys`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/api-keys` | ✅ | 列出当前用户的 API Key |
| POST | `/api-keys` | ✅ enterprise | 创建新 API Key |
| DELETE | `/api-keys/{key_id}` | ✅ | 撤销 API Key |

### 管理后台 `/api/v1/admin`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/admin/users` | ✅ admin | 分页用户列表 |
| GET | `/admin/stats` | ✅ admin | 全站统计数据 |
| PATCH | `/admin/users/{user_id}` | ✅ admin | 更新用户（封禁/改 tier） |
| POST | `/admin/subscriptions` | ✅ admin | 人工为用户开通订阅 |

### 关税与成本 `/api/v1/calculate`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/calculate/tariff` | ✅ | 多市场关税计算 |
| POST | `/calculate/import-cost` | ✅ | 进口成本精算（FOB→到岸→回本） |

### HS 编码 `/api/v1/hs-codes`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/hs-codes/search` | ❌ | 模糊搜索 HS 编码 |

### 国家数据 `/api/v1/countries`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/countries` | ❌ | 非洲 54 国基础数据列表 |

### 原产地 `/api/v1/origin`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/origin/check` | ✅ | AI 原产地合规判定（DeepSeek） |

### 物流 `/api/v1/freight`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/freight/routes` | ❌ | 物流路线列表 |
| GET | `/freight/routes/countries` | ❌ | 起运国列表 |
| GET | `/freight/routes/ports` | ❌ | 目的港列表 |
| POST | `/freight/estimate` | ❌ | 运费估算 |

### 原产地证书 `/api/v1/certificate`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/certificate/guides` | ❌ | 各国证书办理指南列表 |
| GET | `/certificate/guides/{country_code}` | ❌ | 单国证书详情 |
| GET | `/certificate/steps` | ❌ | 证书办理步骤 |
| POST | `/certificate/application/start` | ✅ | 发起 AI 申请 |
| GET | `/certificate/application` | ✅ | 我的申请列表 |
| POST | `/certificate/document/generate` | ✅ | AI 生成证书文档 |

### 供应商 `/api/v1/suppliers`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/suppliers` | ❌ | 搜索供应商（分页+过滤） |
| GET | `/suppliers/countries` | ❌ | 供应商国家分布 |
| GET | `/suppliers/{supplier_id}` | ❌ | 供应商详情 |
| GET | `/suppliers/{supplier_id}/reviews` | ❌ | 供应商评价列表 |
| POST | `/suppliers/{supplier_id}/reviews` | ✅ | 发布评价 |
| GET | `/suppliers/{supplier_id}/compare` | ❌ | 供应商比价（配合物流数据） |

### 市场选品 `/api/v1/market`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/market/products` | ❌ | 市场选品列表 |

### Debug `/api/v1/debug`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/debug/db-status` | ❌ | 各表行数统计（用于监控数据完整性） |
| POST | `/debug/reinit-db` | ❌ | 重建缺失的表和列（保留现有数据） |
| GET | `/debug/export-suppliers` | ❌ | 导出供应商 JSON |
| GET | `/debug/export-all-data` | ❌ | 导出全部参考数据 JSON |
| POST | `/debug/upsert-data` | ❌ | 批量 upsert 参考数据 |

### 根路径（无前缀）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/health` | ❌ | 后端存活检查（冷启动探活） |
| GET | `/debug/db-status` | ❌ | 同上，本地开发兼容 |

---

## 数据库 Schema

### 表列表

| 表名 | 说明 | 核心字段 |
|---|---|---|
| `users` | 用户账户 | email, password_hash, tier, expires_at, is_admin, is_active |
| `subscriptions` | 订阅记录 | user_id, tier, amount, status, started_at, expires_at, auto_renew |
| `api_keys` | API Key | user_id, key_hash, name, tier, rate_limit_day, is_active |
| `sub_accounts` | 子账号 | parent_user_id, email, password_hash, name, is_active |
| `calculations` | 计算日志 | user_id, hs_code, origin, destination, result, created_at |
| `usage_logs` | API 使用日志 | user_id, api_key_id |
| `africa_countries` | 非洲国家 | code, name_zh, name_en, in_afcfta, has_epa |
| `hs_codes` | HS 编码 | hs_4/6/8/10, name_zh, mfn_rate, vat_rate, category |
| `policy_rules` | 政策规则 | market, rule_type, hs_pattern, rate, effective_date |
| `freight_routes` | 物流路线 | origin_country, origin_port, dest_port, transport_type, cost_range |
| `cert_guides` | 证书指南 | country_code, cert_type, issuing_authority, fee, days, steps |
| `suppliers` | 供应商 | name_zh, country, main_products, contact_*, verified_*, rating_avg |
| `supplier_reviews` | 供应商评价 | supplier_id, quality/delivery/communication_score, is_verified_deal |
| `market_analysis` | 市场选品 | country, hs_code, opportunity_score, market_size |

### 双语 SQL 设计

`database.py` 使用 `_is_postgres()` 判断运行环境，动态切换：
- **SQLite**（本地开发）：占位符 `?`，自增 `INTEGER PRIMARY KEY AUTOINCREMENT`
- **PostgreSQL**（Neon）：占位符 `%s`，自增 `SERIAL PRIMARY KEY`，`TIMESTAMPTZ` 时间戳

```python
if _is_postgres():
    cursor.execute("INSERT INTO users ... VALUES (%s, %s, ...)", (email, password_hash))
else:
    cursor.execute("INSERT INTO users ... VALUES (?, ?, ...)", (email, password_hash))
```

### init_db() 冷启动优化

`init_db()` 包含 fast-skip 逻辑：若 PostgreSQL 且 `cert_guides > 1000` 行，直接 return，不执行任何 SQL。**副作用**是后续新增的表（如 `sub_accounts`）不会被创建。为此新增了 `ensure_sub_accounts_table()`，在 lifespan 中单独调用，绕过 skip：

```python
@asynccontextmanager
async def lifespan(app):
    from app.models.database import get_db_path, init_db, seed_admin_user, ensure_sub_accounts_table
    db_path = get_db_path()
    init_db(db_path)
    ensure_sub_accounts_table(db_path)  # 绕过 fast-skip，确保子账号表存在
    seed_admin_user(db_path)
    yield
```

### 订阅自动降级

`get_user_tier_from_db()` 在用户登录/鉴权时检查 `expires_at < today`，若过期则将 tier 改为 `free`。异常捕获后返回 503，确保 Neon 冷启动时返回友好错误而非 500。

---

## 订阅体系

### 等级

| 等级 | 价格 | 每日查询 | API Key | 子账号 | 功能限制 |
|---|---|---|---|---|---|
| **free** | 免费 | 3 次/天 | ❌ | ❌ | 仅基础关税计算 |
| **pro** | ¥99/年 | 不限 | ❌ | ❌ | 全部计算功能 |
| **enterprise** | ¥298/年 | 不限 | ✅ | ✅（最多 5 个） | 全功能 |

### 配额实现

- **免费版**：前端 `useAppStore` 维护每日计数器（基于 `DATE(created_at)`），调用 `/auth/daily-usage` 同步服务器计数。
- **付费版**：不限制，但 `get_user_tier_from_db()` 每日检查 `expires_at`，过期自动降为 free。

---

## 前端→后端请求流程

```
前端 api.ts（axios 实例）
  baseURL: ${VITE_API_BASE}/api/v1   (生产: https://africa-web-sffq.onrender.com/api/v1)
  timeout: 30000ms
  自动附加 Authorization: Bearer <token>（从 localStorage 读）

请求 → Vercel（前端静态）
  vercel.json rewrite: /api/* → https://africa-web-wuxs.onrender.com/api/$1
     → Render 后端（FastAPI）
        → CORS 中间件检查 origin
        → 路由匹配
        → JWT 鉴权（若需要）
        → DB 查询（Neon PostgreSQL）
        → 响应
```

### 前端 API 层设计模式

所有 API 调用封装在 `api.ts` 中的命名函数：

```typescript
// 调用方式
const result = await calculateTariff({ hs_code, origin_country, destination, fob_value })
const status = await getSubscriptionStatus()
const keys = await listApiKeys()

// Axios 实例配置
export const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})
// 请求拦截器：自动附加 Bearer token
```

---

## 环境变量

### 前端（`.env.production`）

```bash
VITE_API_BASE=https://africa-web-sffq.onrender.com
```

### 后端（Render Dashboard 环境变量）

| 变量 | 说明 |
|---|---|
| `DATABASE_URL` | Neon PostgreSQL 连接字符串（`postgresql://user:pass@host/db`） |
| `JWT_SECRET` | JWT 签名密钥（生产必须设置，替换默认明文密钥） |
| `DEEPSEEK_API_KEY` | DeepSeek API Key（AI 原产地判定，可选） |
| `EXCHANGE_RATE_API_KEY` | 汇率 API（可选） |

---

## 部署流程

### 前端（Vercel）

- 监听目录：`africa-zero/frontend/`
- 构建命令：`npm run build`（含 TypeScript 检查）
- 输出目录：`dist/`
- `vercel.json` rewrites：将 `/api/*` 代理到 Render 后端

### 后端（Render）

- 配置文件：`africa-zero/render.yaml`
- 监听目录：`africa-zero/`
- 启动命令：`cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **冷启动注意事项**：Neon 免费版休眠后唤醒约需 10-30 秒，`/health` 返回 200 即表示就绪

### 部署触发

推送代码到 `main` 分支后自动触发：
```bash
cd africa-zero
git add . && git commit -m "描述" && git push origin main
```

### 本地数据同步到 Neon

```bash
cd backend
# 设置 DATABASE_URL 环境变量指向 Neon
export DATABASE_URL="postgresql://..."
# 运行同步脚本（清空线上表，从本地种子数据批量插入）
python sync_all_to_neon.py
```

---

## AI 集成（DeepSeek）

### 原产地合规判定（`/api/v1/origin/check`）

**输入**：产品名称、HS 编码、原产国、加工步骤、材料来源

**调用方式**：
```python
from openai import OpenAI
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
# 系统 prompt：AfCFTA 原产地规则专家
# 用户 prompt：拼接产品信息 + 判定要求
# 返回：是否合规、合规规则、置信度、建议
```

### 证书文档 AI 生成（`/api/v1/certificate/document/generate`）

根据用户填写的申请信息，AI 生成原产地证书申请表内容。

---

## 安全设计

| 机制 | 实现 |
|---|---|
| 密码存储 | bcrypt（passlib 或 bcrypt） |
| JWT | HS256，30 天有效期，`exp` 字段防重放 |
| CORS | 白名单域名，FastAPI CORSMiddleware |
| Tier 鉴权 | 每个受保护路由手动检查 `current_user["tier"]` |
| 子账号隔离 | 查询按 `parent_user_id` 过滤，软删除 `is_active=0` |
| API Key 限流 | 按企业账号维度限流（`rate_limit_day` 字段） |
| 管理后台 | 仅 `is_admin=True` 用户可访问 |

---

## 关键工程经验（可供其他项目复用）

### 1. 前端即时登录状态恢复

无需等待 API，在页面加载时用纯 JS 解码 JWT payload 即恢复 UI 状态。800ms 后台校验防止 token 伪造。

**复用模式**：
```typescript
// jwt.ts — 纯 JS，无依赖
export function decodeToken(token: string): JWTPayload | null
// App.tsx AuthBootstrap
const payload = decodeToken(token)  // 即时
if (payload) updateUser(payload)    // 无需等待
setTimeout(() => verifyWithServer(), 800)  // 后台同步
```

### 2. SQLite/PostgreSQL 双驱动

同一套代码，通过 `_is_postgres()` 动态切换占位符风格（`?` vs `%s`）和自增语法。开发和生产环境无缝切换。

**复用模式**：将占位符风格抽象为 `_adapt_sql(sql)` 函数，DB 连接由 `get_db()` 统一管理。

### 3. 后端冷启动容错

Neon 免费版休眠后首次请求超时导致 500。加了两层防护：
- `get_user_tier_from_db()` try-except → 503（而非 500）
- `/health` 探活端点，前端轮询确认就绪后再发业务请求

### 4. 订阅自动降级

不依赖定时任务，在每次用户鉴权时检查 `expires_at`，过期则自动更新 DB tier 为 `free`。无需额外基础设施。

### 5. FastAPI + Vercel Rewrite 架构

前端纯静态部署（Vercel），后端独立服务（Render），通过 `vercel.json` rewrite 解决跨域问题，同时支持本地开发（前端直连 `localhost:8000`）。

---

## 数据流向图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户浏览器                            │
│  localStorage: { token, tier, remainingToday, interestList }│
│  JWT payload 解码 → 立即恢复 UI 状态                         │
└──────────┬──────────────────────────────────┬──────────────┘
           │  /api/*                          │
           ▼                                  ▼
    ┌──────────────┐                   ┌─────────────────┐
    │   Vercel     │  rewrite          │    Render        │
    │  静态前端     │ ────────────────→ │   FastAPI 后端   │
    │ (无后端逻辑)  │                  │                 │
    └──────────────┘                  ┌─────────────────┤
                                       │  lifespan:      │
                                       │  init_db()      │
                                       │  ensure_sub_    │
                                       │    accounts_    │
                                       │    table()      │
                                       │  seed_admin_    │
                                       │    user()       │
                                       └────────┬────────┘
                                                │
                                                ▼
                                       ┌─────────────────┐
                                       │  Neon PostgreSQL│
                                       │  (africa_zero)  │
                                       └─────────────────┘
```

---

*© 2026 AfricaZero · 数据仅供参考，不构成法律建议。*
