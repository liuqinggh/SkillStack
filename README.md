# demo-csbot

Deep Agent 客服 / 聊天 Demo：FastAPI Runtime API + 精简聊天前端（`demo-frontend/agent-chat-lite`）。

## 环境要求

- **Python** 3.11+
- **uv**
- **Node.js** 18+
- **npm**（agent-chat-lite 用）/ 可选 **pnpm**（hermes_client 用）
- 根目录存在 `conf.yaml`（可从 `conf.example.yaml` 复制）

## 后端启动

在项目根目录执行：

```bash
uv sync --group dev
uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

- 健康检查：`GET http://127.0.0.1:8000/health`
- Runtime API：`/api/runtime/*`
- Hermes Client 兼容 API（含 mock）：`/api/auth/*`、`/api/agent/*`、`/api/conversation/*`、`/api/message/*`、`/api/plugin/*` 等

## 前端启动

前端目录为 `demo-frontend/hermes_client/client`。

### 开发模式

1. 先启动后端（默认 8000）。
2. 新开终端：

```bash
cd demo-frontend/hermes_client/client
pnpm install
pnpm dev
```

`vite.config.ts` 已代理：
- `/api` -> `http://127.0.0.1:8000`
- `/ws/pty` -> `ws://127.0.0.1:8000`

### 构建并由 FastAPI 托管

```bash
cd demo-frontend/hermes_client/client
pnpm install
pnpm build
```

构建完成后，FastAPI 会优先返回 `demo-frontend/hermes_client/client/dist/index.html` 作为 `/` 首页。

## 说明

- `demo-frontend/hermes_client/api` 在当前仓库中已废弃，不参与运行。
- 插件、技能、Cron、洞察、更新、PTY 等页面会保留 UI，后端接口目前由 FastAPI mock 响应。
