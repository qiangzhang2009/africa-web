# Cloudflare Worker 部署指南

## 背景

Render 免费版的 Web Service 前置了 Cloudflare 代理，会在 FastAPI 处理 OPTIONS preflight 之前拦截所有 CORS preflight 请求，返回 "Disallowed CORS origin"。这导致浏览器中所有 POST/PUT/DELETE 请求都会失败。

Cloudflare Worker 会完全绕过这个拦截层，在 Cloudflare 边缘节点处理 CORS preflight，直接返回正确的 headers，再把实际请求代理到后端。

## 需要部署的文件

已生成于 `frontend/` 目录：
- `public/_worker.js` — Worker 代码
- `wrangler.toml` — 部署配置

## 部署步骤（Cloudflare Dashboard，无需 CLI）

### 第一步：登录 Cloudflare

打开 https://dash.cloudflare.com/ 并登录你的账号。

### 第二步：创建 Worker

1. 在左侧菜单选择 **Workers & Pages**
2. 点击 **Create Worker**
3. Worker 名称填写：`africa-web-cors-proxy`（也可以填你喜欢的名字）
4. 点击 **Deploy**

### 第三步：上传 Worker 代码（两种方式）

#### 方式 A：用 Dashboard 内置编辑器（推荐）

1. Worker 创建完成后，点击 **Edit code**
2. 删除所有默认代码
3. 打开 `/Users/john/Africa-web/africa-zero/frontend/public/_worker.js` 文件，把全部内容复制粘贴进去
4. 点击 **Save and Deploy**

#### 方式 B：使用 Wrangler CLI

```bash
cd /Users/john/Africa-web/africa-zero/frontend
npx wrangler deploy
```

### 第四步：记录 Worker URL

部署完成后，Worker 的 URL 类似：
`https://africa-web-cors-proxy.<your-account>.workers.dev`

记下这个 URL。

### 第五步：修改前端 API 调用地址

需要修改 `frontend/src/utils/api.ts`，把 API baseURL 从：
```
https://africa-web-wuxs.onrender.com/api/v1
```
改成你的 Worker URL：
```
https://africa-web-cors-proxy.xxx.workers.dev/api/v1
```

让我来帮你改：
