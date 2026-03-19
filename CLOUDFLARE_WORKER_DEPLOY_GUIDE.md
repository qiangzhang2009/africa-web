# Cloudflare Worker 部署指南

## 背景

Render 免费版的 Web Service 前置了 Cloudflare 代理，会在 FastAPI 处理 OPTIONS preflight 之前拦截所有 CORS preflight 请求，返回 "Disallowed CORS origin"。这导致浏览器中所有 POST/PUT/DELETE 请求都会失败。

Cloudflare Worker 会完全绕过这个拦截层，在 Cloudflare 边缘节点处理 CORS preflight，直接返回正确的 headers，再把实际请求代理到后端。

## 需要部署的文件

已生成于 `frontend/` 目录：
- `public/_worker.js` — Worker 代码
- `wrangler.toml` — 部署配置

## 两种 Worker 项目（先看你是哪一种）

### A. 已连接 GitHub（你截图里这种）

**特点：** 设置里能看到「已连接仓库」、**部署命令** 是 `npx wrangler deploy`。  
**没有「编辑代码」是正常的**——代码在 Git 仓库里改，推送后 Cloudflare 自动部署。

你要做的：

1. 在本机编辑仓库里的 **`africa-zero/frontend/public/_worker.js`**（与 `wrangler.toml` 同级目录下的 `public/`）。
2. **提交并 push** 到 GitHub。
3. 在 Cloudflare → 该 Worker → **部署**，等最新一次部署成功。

**重要：** 在 Cloudflare **设置 → 构建** 里确认 **根目录（Root directory）** 指向包含 `wrangler.toml` 的文件夹，一般为：

`africa-zero/frontend`

否则 `wrangler deploy` 在仓库根目录执行会找不到 `public/_worker.js`。

**不要把整段 JS 粘到「构建命令」里**——那里只能写短 shell 命令（且有长度限制），不是贴代码的地方。

### B. 未连接 Git 的「纯 Worker」

1. Workers & Pages → **Create Worker** → 起名为 `africa-web-cors-proxy` → Deploy  
2. 进入后若有 **Quick edit / 编辑代码**，在**代码编辑区**粘贴 `public/_worker.js` 全文 → Save and Deploy  

若始终找不到编辑器，就用 **方式 C：本机 Wrangler**。

### C. 本机 Wrangler（不依赖 Dashboard 编辑器）

```bash
cd africa-zero/frontend
npx wrangler deploy
```

需已登录：`npx wrangler login`。

---

## 后续配置（部署成功后）

### 1. 配置 Worker 环境变量

Cloudflare → 该 Worker → **设置 → 变量和机密（Variables）** → 添加**纯文本**变量（不是 D1 绑定）：

| 变量名 | 值 |
|--------|-----|
| `BACKEND_ORIGIN` | `https://africa-web-wuxs.onrender.com` |
| `ALLOWED_ORIGINS` | `https://africa-web-1.onrender.com,http://localhost:5173,http://localhost:3000` |
| `WORKER_ORIGIN` | `https://africa-web-cors-proxy.<你的账号>.workers.dev`（以控制台显示的 Worker 域名为准） |

### 2. 记录 Worker URL

形如：`https://africa-web-cors-proxy.<你的账号>.workers.dev`

### 3. 配置前端（Vite 构建时注入）

在 **`africa-zero/frontend/.env`** 或 Render 静态站的环境变量里设置（**仅前端构建需要**，不要加到 Worker 里）：

```
VITE_WORKER_URL=https://africa-web-cors-proxy.<你的账号>.workers.dev
```

然后重新构建并部署前端：

```bash
cd africa-zero/frontend
npm run build
```

部署后，生产环境会把 API 请求发到 Worker，由 Worker 处理 CORS 并转发到 Render 后端。
