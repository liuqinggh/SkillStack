# CS-Bot API 接口说明

本文档基于当前代码实现整理，适用于本地开发与联调。  
默认后端地址：`http://127.0.0.1:8000`

## 1. 认证与通用约定

- 认证方式：`Bearer Token`
- 登录后从响应字段 `accessToken` 读取令牌
- 绝大多数 `/api/*` 接口都需要请求头：
  - `Authorization: Bearer <accessToken>`
- 时间字段使用 ISO8601 字符串（示例：`2026-05-03T07:05:56.938298+00:00`）

### 1.1 登录

- **POST** `/api/auth/login`
- 请求体：

```json
{
  "email": "admin@admin.com",
  "password": "123456"
}
```

- 成功响应：

```json
{
  "id": "admin",
  "email": "admin@admin.com",
  "name": "Admin",
  "accessToken": "..."
}
```

### 1.2 当前用户

- **GET** `/api/auth/token`
- 响应：

```json
{
  "id": "admin",
  "email": "admin@admin.com",
  "name": "Admin"
}
```

### 1.3 登出

- **DELETE** `/api/auth/logout`
- 响应：`204 No Content`

### 1.4 健康检查（无需认证）

- **GET** `/health`
- 响应：

```json
{
  "status": "ok",
  "service": "demo-csbot-runtime",
  "runtime": "ready",
  "version": "0.2.0"
}
```

---

## 2. Agent 相关

前端主入口：`/api/agent`  
当前实现中，Agent 来源于运行时配置，创建未知 profile 会报错。

### 2.1 查询 Agent 列表

- **GET** `/api/agent`
- 响应：

```json
{
  "total": 3,
  "items": [
    {
      "_id": "default",
      "name": "Default Agent",
      "hermesProfile": "default",
      "createdAt": "...",
      "updatedAt": "...",
      "model": "gemini-2.5-flash",
      "exists": true,
      "dailyCapUsd": null,
      "monthlyCapUsd": null,
      "allTimeCapUsd": null
    }
  ]
}
```

### 2.2 查询单个 Agent

- **GET** `/api/agent/{agent_id}`

### 2.3 创建 Agent（受 profile 约束）

- **POST** `/api/agent`
- 请求体：

```json
{
  "name": "My Agent",
  "hermesProfile": "default"
}
```

- 若 `hermesProfile` 不在已配置 profile 中，会返回 `400`

### 2.4 更新 Agent

- **PATCH** `/api/agent/{agent_id}`
- 支持字段：`name`, `dailyCapUsd`, `monthlyCapUsd`, `allTimeCapUsd`

### 2.5 删除 Agent

- **DELETE** `/api/agent/{agent_id}`

### 2.6 会话设置（按 Agent + Conversation）

- **GET** `/api/agent/{agent_id}/conversation/{conversation_id}/session-settings`
- **PATCH** `/api/agent/{agent_id}/conversation/{conversation_id}/session-settings`

---

## 3. Conversation（会话）相关

### 3.1 列出全部会话

- **GET** `/api/conversation`

### 3.2 按 Agent 列会话

- **GET** `/api/conversation/agent/{agent_id}`

### 3.3 创建会话

- **POST** `/api/conversation`
- 请求体：

```json
{
  "agentId": "default"
}
```

- 响应：

```json
{
  "_id": "0375bfb6-ee57-4738-8715-8ab1abf2a357",
  "agentId": "default",
  "title": null,
  "sessionKey": "0375bfb6-ee57-4738-8715-8ab1abf2a357",
  "createdAt": "...",
  "updatedAt": "...",
  "session_settings": {}
}
```

### 3.4 修改会话标题

- **PATCH** `/api/conversation/{conversation_id}`
- 请求体：

```json
{
  "title": "新的会话标题"
}
```

### 3.5 删除会话

- **DELETE** `/api/conversation/{conversation_id}`
- 同时会删除对应 transcript

---

## 4. Message（消息）相关

### 4.1 查询会话消息

- **GET** `/api/message/conversation/{conversation_id}`
- 可选查询参数：`before`（按 `createdAt` 游标分页）
- 响应：

```json
{
  "total": 12,
  "items": [
    {
      "_id": "msg-id",
      "conversationId": "session-id",
      "text": "hello",
      "thinking": null,
      "files": [],
      "role": "user",
      "createdAt": "2026-05-03T07:05:56.938298+00:00",
      "agentId": "default"
    }
  ],
  "hasMore": false
}
```

### 4.2 拉取增量消息

- **GET** `/api/message/conversation/{conversation_id}/poll`
- 可选查询参数：`after`
- 响应：

```json
{
  "items": [],
  "synced": 0
}
```

### 4.3 手动写入消息（非流式）

- **POST** `/api/message`
- 请求体：

```json
{
  "conversationId": "session-id",
  "text": "hello"
}
```

### 4.4 删除消息

- **DELETE** `/api/message/{message_id}`

### 4.5 聊天主接口（SSE）

- **POST** `/api/message/chat`
- `Content-Type: multipart/form-data`
- 字段：
  - `conversationId`（必填）
  - `text`（可空，若有文件可仅上传文件）
  - `files`（可多文件）

- 返回：`text/event-stream`
- 典型事件：

```text
data: {"type":"response.output_text.delta","delta":"你好"}

data: [DONE]
```

---

## 5. Runtime API（新运行时）

前缀：`/api/runtime`

### 5.1 创建运行时 session

- **POST** `/api/runtime/sessions`
- 响应：

```json
{
  "session_id": "uuid",
  "latest_run_id": null
}
```

### 5.2 查询运行时 session

- **GET** `/api/runtime/sessions/{session_id}`

### 5.3 上传附件

- **POST** `/api/runtime/uploads`
- `multipart/form-data` 字段：
  - `session_id`
  - `ocr_mode`（默认 `auto`）
  - `file`

- 响应（节选）：

```json
{
  "attachment_id": "att-id",
  "session_id": "uuid",
  "filename": "xxx.pdf",
  "kind": "ocr",
  "extraction_status": "ready",
  "extractor": "skill:image-by-intent",
  "extraction_error": null
}
```

### 5.4 发起 run（流式或非流式）

- **POST** `/api/runtime/runs`
- 请求体：

```json
{
  "input": {
    "message": "你好",
    "attachments": []
  },
  "agent": {
    "id": "default",
    "mode": "chat"
  },
  "model": {
    "provider": "litellm",
    "model": "gemini-2.5-flash"
  },
  "session_id": "uuid-or-null",
  "stream": true,
  "metadata": null
}
```

- `stream=true`：返回 `text/event-stream`
- `stream=false`：返回摘要：

```json
{
  "run_id": "run-uuid",
  "status": "succeeded",
  "session_id": "uuid"
}
```

---

## 6. 兼容/占位接口（前端兼容）

以下接口已实现但多数为 mock/空数据，主要用于兼容 Hermes Client UI：

- `/api/user`（用户管理简化实现）
- `/api/plugin`（插件列表/开关）
- `/api/skill`（技能列表：当前返回空）
- `/api/cron`（任务管理：当前返回 mock）
- `/api/insights`（统计看板：当前返回占位结构）
- `/api/update/status`、`/api/update/apply`
- `/ws/pty`（WebSocket，返回 mock 文本后关闭）

---

## 7. 常见错误码

- `401 Unauthorized`：token 缺失或过期
- `404 Not Found`：会话、Agent、附件等不存在
- `400 Bad Request`：参数不合法、会话与 Agent 绑定冲突、附件归属不匹配
- `504 Gateway Timeout`：`/api/runtime/runs` 非流式执行超时

---

## 8. 联调建议

- 前端第一次发送前请确保已选择 `agentId`；会话可自动创建
- 多 Agent 场景下，同一个 session 不允许切换到不同 agent
- 技能配置/技能文档更新后，建议重启后端（避免 runtime cache 仍持有旧内容）

