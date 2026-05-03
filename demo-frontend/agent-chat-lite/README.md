# agent-chat-lite

基于 `demo-frontend/hermes_client` 的精简版前端，仅保留：

- Agent 选择
- 会话选择 / 新建
- 聊天发送与流式回复

## 启动

先启动后端（默认 `http://127.0.0.1:8000`），再在本目录执行：

```bash
npm install
npm run dev
```

默认访问：`http://127.0.0.1:18900`

开发服务器已代理 `/api` 到 `http://127.0.0.1:8000`。
