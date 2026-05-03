# skyro-chatbot 多轮对话回归脚本

这个目录用于组织“文本多轮 + 材料图片”的自动化回归场景。

## 1) 快速使用

先启动后端（默认 `http://127.0.0.1:8888`），然后运行：

```bash
uv run python tests/skyro-chatbot/run_multiturn_cases.py
```

如果要走 SSE 流式：

```bash
uv run python tests/skyro-chatbot/run_multiturn_cases.py --stream
```

## 2) 场景组织方式

支持两种结构：

### 方式 A：单场景（当前仓库默认）

```text
tests/skyro-chatbot/
  user-turns.txt
  materials/                # 可选，放图片/文档
  case.json                 # 可选，场景断言
```

### 方式 B：多场景（推荐）

```text
tests/skyro-chatbot/
  cases/
    basic-flow/
      user-turns.txt
      materials/
      case.json
    missing-material/
      user-turns.txt
      materials/
      case.json
```

## 3) user-turns.txt 规则

- 支持用标题分段（例如 `chronology：`、`personal info：`），每段作为一轮输入。
- 如果没有标题，就按空行分段，每段一轮。

## 4) case.json（可选）

示例：

```json
{
  "all_turns_must_succeed": true,
  "expected_final_status": "succeeded"
}
```

可用字段：

- `all_turns_must_succeed`：默认 `true`
- `expected_final_status`：可选，断言最后一轮状态（如 `"succeeded"`）

## 5) 常用参数

```bash
uv run python tests/skyro-chatbot/run_multiturn_cases.py \
  --base-url http://127.0.0.1:8888 \
  --cases-root tests/skyro-chatbot \
  --agent-id default \
  --model gpt-4 \
  --timeout 120 \
  --stream
```

说明：
- `--agent-id` 需与后端 `agent.default_profile_id` 一致（通常是 `default`）。
- `--model` 当前主要用于满足请求体结构，后端实际模型以配置为准。
- `--report-json` 可输出 JSON 报告。
- `--report-csv` 可输出 CSV 报告（每轮一行）。

示例（批跑并导出）：

```bash
uv run python tests/skyro-chatbot/run_multiturn_cases.py \
  --stream \
  --report-json tests/skyro-chatbot/reports/latest.json \
  --report-csv tests/skyro-chatbot/reports/latest.csv
```

## 6) 已内置样例

当前目录已内置两组样例：

- `cases/basic-claim-flow/`：纯文本多轮场景
- `cases/attachment-guided/`：多轮 + 材料上传场景（示例为 `txt`）

你可以在 `materials/` 里放真实图片（如 `.jpg/.jpeg/.png`）来覆盖 OCR 路径。
