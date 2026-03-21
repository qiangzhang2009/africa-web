# Vercel 部署指南

## 架构说明

```
用户浏览器 → Vercel 前端 → /api/* → Vercel Rewrite → Render 后端
```

前端部署在 Vercel，使用 Vercel 的 rewrite 功能将 `/api/*` 请求代理到 Render 后端，无需额外的环境变量配置。

## 第一步：在 Vercel 上导入项目

1. 登录 [vercel.com](https://vercel.com)，用 GitHub 账号授权
2. 点击 **Add New → Project**
3. 在 "Import Git Repository" 页面，找到 `qiangzhang2009/africa-web`
4. 点击 **Import**

---

## 第二步：配置项目

| 设置项 | 值 |
|---|---|
| **Framework Preset** | `Vite`（重要！） |
| **Root Directory** | `./`（默认，留空） |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |
| **Install Command** | `npm install` |

> ⚠️ 如果看到 `Root Directory` 默认是 `frontend`，改成 `./`（因为 monorepo 的根目录有 frontend/ 和 backend/ 两个子目录）

---

## 第三步：部署

1. 点击 **Deploy**
2. 等待 1-2 分钟
3. 看到 ✅ Deployment Complete 就成功了

Vercel 会给你一个 URL：`https://africa-zero-xxxx.vercel.app`

---

## 第四步：配置自定义域名（可选）

1. Vercel → 你的项目 → Settings → Domains
2. 添加自定义域名（如 `africa.zxqconsulting.com`）
3. 按照提示配置 DNS 记录

> 注意：自定义域名需要配置 DNS CNAME 记录指向 Vercel

---

## API Rewrite 配置

Vercel 的 `vercel.json` 已经配置好了 API 代理：

```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://africa-web-wuxs.onrender.com/api/:path*"
    }
  ]
}
```

这意味着所有 `/api/*` 请求会自动转发到 Render 后端。

---

## 自动部署

推送到 main 分支后，GitHub Actions 会自动：
1. 构建前端
2. 部署到 Vercel

无需手动干预。

---

## 常见问题

**Q: 如何确认 API Rewrite 生效？**
A: 访问 `https://your-domain.com/api/v1/health`，应该返回 `{"status":"ok","service":"africa-zero"}`

**Q: 后端地址在哪里配置？**
A: 在 `vercel.json` 的 `rewrites` 配置中修改 Render 后端地址。

**Q: Vercel 免费版有域名限制吗？**
A: `.vercel.app` 子域名是免费的，自定义域名需要升级。
