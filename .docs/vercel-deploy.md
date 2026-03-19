# Vercel 部署指南

## 第一步：在 Vercel 上创建项目

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

## 第三步：设置环境变量

点击 **Environment Variables**，添加：

| Name | Value | Environments |
|---|---|---|
| `VITE_API_URL` | `https://africa-zero-api.onrender.com` | All |
| `VITE_DEEPSEEK_API_KEY` | `sk-98bf5907ed564bad91368107eca1f586` | All |

> 注意：`VITE_` 前缀的环境变量才能在 Vite 前端代码里访问到。
> `VITE_API_URL` 的值等 Render 后端部署完成后填入（先填一个占位符，上线后再改）。

---

## 第四步：部署

1. 点击 **Deploy**
2. 等待 1-2 分钟
3. 看到 ✅ Deployment Complete 就成功了

Vercel 会给你一个 URL：`https://africa-zero-xxxx.vercel.app`

---

## 第五步：更新后端 API URL

后端 Render 上线后：

1. Vercel → 你的项目 → Settings → Environment Variables
2. 把 `VITE_API_URL` 的值改成真实的 Render URL（如 `https://africa-zero-api.onrender.com`）
3. 点击 **Redeploy**

---

## 第六步：配置 GitHub Actions 自动部署

在 GitHub 仓库的 Settings → Secrets，添加：

| Secret Name | Value |
|---|---|
| `VERCEL_TOKEN` | Vercel Account Settings → Tokens → Create Token |
| `VERCEL_ORG_ID` | Vercel Dashboard → Team Settings → ID |
| `VERCEL_PROJECT_ID` | Vercel Dashboard → 你的项目 → Settings → General → Project ID |

添加后，每次 `git push` 到 main 分支，前端会自动重新部署。

---

## 常见问题

**Q: `vite.config.ts` 里的 proxy 配置在 Vercel 上还有效吗？**
A: 没有。Vercel 是静态托管，proxy 不生效。API 请求直接打到 `VITE_API_URL` 指定的地址。

**Q: Vercel 免费版有域名限制吗？**
A: `.vercel.app` 子域名是免费的，自定义域名需要升级。
