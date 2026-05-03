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
- 聊天 API：`/api/auth/*`、`/api/agent/*`、`/api/conversation/*`、`/api/message/*`
- Hermes 风格 mock API（仅供 hermes_client 前端使用）：`/api/plugin/*`、`/api/skill/*`、`/api/cron/*` 等

## 前端启动

默认前端为 `demo-frontend/agent-chat-lite`，只保留 Agent 选择 + 会话 + 流式聊天。

### 开发模式

1. 先启动后端（默认 8000）。
2. 新开终端：

```bash
cd demo-frontend/agent-chat-lite
npm install
npm run dev
```

默认访问：`http://127.0.0.1:18900`，已代理 `/api -> http://127.0.0.1:8000`。

默认登录账号：`admin@admin.com / 123456`（与 `conf.example.yaml` 一致，正式环境请覆盖）。

### 构建并由 FastAPI 托管

```bash
cd demo-frontend/agent-chat-lite
npm install
npm run build
```

构建完成后，访问 `http://127.0.0.1:8000/` 即由 FastAPI 直接返回 `demo-frontend/agent-chat-lite/dist/index.html`。

### 旧 Hermes Client（可选）

如果仍想使用 `demo-frontend/hermes_client/client` 完整版控制台，需要：

1. 修改 `src/csbot/api/routes/root_static.py` 中 `frontend_dist_dir` 指向 `hermes_client/client/dist`；
2. 在 `demo-frontend/hermes_client/client` 内执行 `pnpm install && pnpm build`。

## 说明

- `demo-frontend/hermes_client/api` 在当前仓库中已废弃，不参与运行。
- `agent-chat-lite` 不使用 plugin/skill/cron/insights/pty 等接口，所以那些 mock 路由对它而言不可见。
