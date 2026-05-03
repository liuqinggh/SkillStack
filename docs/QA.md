# demo-csbot 常见问题（QA）

本文档汇总与“多条消息合并”“流式接口体验”相关的常见问题与建议方案。

---

## Q1. 用户多条消息如何合并后给到后端？

### 当前行为

- **前端**：每次只发**一条**用户消息 + `thread_id`（`POST /api/v1/chat` 或 `/api/v1/chat/stream`，body: `{ message, thread_id }`）。
- **后端**：用 LangGraph 的 **checkpointer**（如 `MemorySaver()`）按 `thread_id` 存对话状态；每次请求的 `input_state` 会和该 thread 已有 state **自动合并**（新 HumanMessage 追加到历史后一起进图）。
- **多轮对话**已成立：不需要前端传历史，后端自己带状态。

### “多条消息合并”的几种含义与做法

#### 1）用户一次输入多段内容（批量输入）

**场景**：用户在输入框里一次输入多段（多行/多段），希望当作**一条**请求发给后端。

| 做法 | 说明 | 适用 |
|------|------|------|
| **前端合并成一条字符串** | 把多行用 `\n` 或自定义分隔符拼成一个大 `message`，仍调用现有接口一次。 | 简单、无需改后端；适合“多段一起当一条用户消息”的语义。 |
| **后端支持 `messages[]`** | 前端传 `messages: [{role:"user", content:"第一段"}, ...]`，后端按顺序处理或拼成一条再进 agent。 | 需要改 API 和 backend；适合要区分“多条独立 user 消息”的场景。 |

**推荐**：若语义是“用户一次性发了多段话”，前端合并成**一个字符串**即可：

```js
const message = inputEl.value.trim().replace(/\n{2,}/g, '\n\n');
await fetch('/api/v1/chat', { body: JSON.stringify({ message, thread_id }) });
```

无需改后端。

#### 2）前端持有完整历史，希望“整段历史”交给后端

**场景**：历史在前端（或别的存储），希望一次请求把**整段对话**发给后端，而不是依赖后端 checkpointer。

| 做法 | 说明 |
|------|------|
| **后端增加 `messages` 入参** | 请求体支持 `messages: [{role, content}, ...]`，作为该次调用的完整上下文或重放后再追一条新消息。 |
| **仍用当前接口，不传历史** | 继续只传最新一条 `message` + `thread_id`，依赖后端 checkpointer。 |

**推荐**：当前架构下**不合并、不传历史**最简单；只有在需要“前端为真相源”“跨端同步历史”或“无状态后端”时，再考虑后端支持 `messages[]`。

#### 3）多条“独立消息”合并成一次 API 调用

**场景**：用户连续发了好几条消息，希望合并成一次请求，减少请求次数或做“批量理解”。

| 做法 | 说明 |
|------|------|
| **合并成一条 user 消息** | 前端把最近 N 条 user 消息用分隔符拼成一个大字符串（如 `"消息1\n---\n消息2"`），作为单次 `message` 发送。 |
| **后端支持 messages[]** | 请求体为 `messages: [{role:"user", content:"1"}, ...]`，后端整段当作多轮或拼成一条再调 agent。 |
| **不合并，保持多次请求** | 每条消息一次请求，依靠 `thread_id` 和 checkpointer 保持上下文。语义最清晰，已支持。 |

**推荐**：若只为少请求次数，可前端做**短时间窗口内合并**（如 2 秒内多条合成一条），或接受“每条一发”。若业务需要“这 N 条必须作为整体被模型理解”，更适合后端支持 `messages[]`。

### 后端若支持 `messages[]` 的接口形态示例

可在现有接口上做**兼容**：

```yaml
# 现有（不变）
message: str
thread_id: str | null

# 可选扩展
messages: [{role: "user"|"assistant", content: string}] | null  # 若存在则优先用 messages 作为本次上下文
```

- 带 **`messages`**：本次可用 `messages` 作为对话历史（或拼成一条再跑 agent），可选是否写回 checkpointer。
- 只带 **`message`**：行为与现在一致，历史从 checkpointer 读。合并逻辑放在后端更稳妥。

### 小结

| 需求 | 建议 |
|------|------|
| 用户一次输入多行/多段，当一条消息 | **前端**：多行 trim 后作为一条 `message` 发送即可，无需改后端。 |
| 多轮对话已有、只是展示 | **不合并**：只发当前这条 `message` + `thread_id`，由后端 checkpointer 维护历史。 |
| 前端为历史真相源、或需要整段历史一次提交 | **后端**支持可选 `messages[]`，由后端做合并/截断等策略。 |
| 希望减少请求次数 | 可前端做**时间窗口内合并**，或保持“每条一发”依赖后端状态。 |

---

## Q2. 流式接口（/api/v1/chat/stream）为什么慢？

### 现象

- **首字慢**：点发送后要等几秒甚至十几秒才看到第一个字。
- **整体慢**：有时整段回复在最后一次性出现，像非流式。

### 原因

#### 1）图在 LLM 前还有很多步骤

`deepagents` 的图不是「一上来就调 LLM」，而是会先跑：

- **Skills 中间件**：按 thread 加载 skills 元数据、注入 system prompt。
- **其它节点**：如规划、文件等（若启用）。

只有这些跑完才会进到 **LLM 节点**。因此 **首 token 时间 = 前面所有步骤耗时 + LLM 首 token**，容易到数秒～十几秒。

#### 2）stream_mode="messages" 可能没有逐 token

使用 LangGraph 的 `stream_mode="messages"` 时：

- 不同图/版本下，chunk 结构可能不是「每个 token 一条」；
- 若中间件或图实现有缓冲，可能变成「整段再一起出」。

前端会长时间收不到 `delta`，体感像一直卡住。

#### 3）无 delta 时退化为整段 run_turn

在 `DeepAgentAdapter.run_stream` 里，若一轮 stream 下来**没有任何 delta**，会走：

```python
if not emitted_any:
    full = self.run_turn(user_input, thread_id)  # 整轮同步跑完
    if full:
        yield full
```

即用 **stream_mode="values"** 再跑一整轮，等整段回复生成完才 yield 一次，表现为：**长时间无输出 → 最后一次性返回整段**。

#### 4）LiteLLM / 模型侧缓冲

即使我们按 token 要流式，若 LiteLLM 或上游模型、网络/代理有缓冲，也可能变成「整段或大块」才到我们，首 token 延迟变大。

### 已做的缓解

1. **立即发 `started` 事件**：流式响应一建立就先发 `type: "started"`，前端可立刻显示「思考中…」。
2. **前端对 started 的展示**：收到 `started` 显示「思考中…」，收到第一个 `delta` 时替换为正文；若只有 `done` 没有 `delta`，用 `done.reply` 替换「思考中…」。

要真正缩短**首字时间**，需要从图/模型侧优化（见下）。

### 可选的进一步优化

| 方向 | 说明 |
|------|------|
| **简化图** | 若不需要 skills/规划，可做「纯 LLM」图或轻量图，减少首 token 前步骤。 |
| **确认流式链路** | 确认当前 deepagents 下 `stream_mode="messages"` 是否按 token 吐出；必要时看源码或打日志看 chunk 频率。 |
| **模型/代理** | 换用确认支持逐 token 的模型或 LiteLLM 配置，避免上游缓冲。 |
| **心跳** | 若首 token 仍很慢，可在等待期间每隔 N 秒发一条 SSE 心跳（如 `: heartbeat`），避免前端或代理认为连接死掉。 |

---

## Q3. 为何保留 `src/csbot` 一层，能否去掉？

当前代码放在 **`src/csbot/`** 下，入口通过 `sys.path.insert(0, "src")` 后使用 **`from csbot import create_app`**。曾有讨论：是否去掉 `csbot` 这一层，把内容直接放在 `src/` 下（即 `src/api/`、`src/services/` 等）。结论与取舍如下。

### 技术上能否去掉

可以。做法是：把 `src/csbot/` 下所有内容上移到 `src/`，把所有 `from csbot.xxx` 改为 `from xxx`，入口改为 `from app_factory import create_app`，并保证运行与测试时 `sys.path` 包含 `src`。

### 去掉后的代价

| 点 | 说明 |
|----|------|
| **失去单一顶层命名空间** | 当前所有代码在 `csbot` 下，不会与第三方包撞名。去掉后 `api`、`config`、`domain`、`services` 等会成为顶级包名，易与依赖中的同名包冲突（尤其 `api`、`config` 很常见）。 |
| **没有明确“包名”** | 入口变为“从某模块”导入（如 `from app_factory import create_app`），而非“从包 csbot 导入”。若将来要做成可安装包（`pip install -e .`），通常仍需一个顶层包名（如 `packages = ["csbot"]` 指向 `src/csbot`）。 |
| **依赖 path 约定** | 所有运行方式（pytest、uvicorn）都必须把 `src` 加入 `sys.path`，且无法再靠包名区分本项目与其它代码。 |

### 何时可考虑去掉

- 项目**仅作为单应用**运行，**不**打算作为库被 `import` 或 `pip install`；
- 能接受顶级包名为 `api`、`config`、`services` 等，并注意避免与依赖冲突；
- 更看重目录少一层、导入更短，且接受上述代价。

### 当前决策

**保留 `src/csbot/`**：保留单一包名、减少与第三方撞名、便于日后若需打包为库。若未来确定仅作单应用且不发布为包，再评估是否扁平化为 `src/` 直出模块。

---

*本文档由《调研-多条用户消息合并后给后端》与《流式接口为什么慢》合并而成，并纳入目录与包结构说明；后续 QA 可在此追加。*
