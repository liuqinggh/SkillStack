# SkillStack

**Centralized skill management for Claude Code** - 通过 symlink 实现单源真相，一次编辑，处处生效。

## ✨ 核心特性

- 🎯 **单源真相**：所有 skills 集中管理在 `~/.skillstack/repository`
- ⚡ **实时同步**：通过 symlink，修改立即生效，无需手动同步
- 🔧 **完整 CRUD**：创建、编辑、删除、导入一键完成
- 🏥 **健康检查**：`doctor` 命令自动检测和修复问题
- 📊 **清晰视图**：表格化展示，支持多种排序方式

## 🚀 快速开始

```bash
# 1. 安装
cargo install --path .

# 2. 初始化（会自动导入现有 skills）
skillstack init

# 3. 创建新 skill
skillstack add my-awesome-skill

# 4. 查看所有 skills
skillstack list

# 5. 编辑 skill（会打开编辑器）
skillstack edit my-awesome-skill
```

## 📦 命令详解

### 核心命令 (P0)

- `init` - 初始化仓库，创建 symlink 到 `~/.claude/skills`
  - `--no-import` - 跳过导入现有 skills
  - `--force` - 强制重新初始化

- `list` - 列出所有 skills（表格格式）
  - `--sort <name|created|updated>` - 排序方式
  - `--reverse` - 反向排序

- `add <name>` - 创建新 skill（自动打开编辑器）
  - `--no-edit` - 不打开编辑器
  - `--editor <vim|code|...>` - 指定编辑器

- `edit <name>` - 编辑 skill（自动更新 hash）
  - `--editor <vim|code|...>` - 指定编辑器

- `delete <name>` - 删除 skill（需确认）
  - `--force` - 跳过确认

- `sync` - 重建 symlink（通常不需要手动执行）
  - `--force` - 强制重建

- `status` - 显示仓库状态（skills 数量、symlink 状态、最后同步时间）

### 高级命令 (P1)

- `import <path>` - 导入外部 skill
  - `--name <name>` - 指定 skill 名称

- `show <name>` - 显示 skill 详细信息（含 hash、时间戳）

- `doctor` - 健康检查（目录结构、symlink、manifest 一致性）
  - `--fix` - 自动修复问题

## 🏗️ 架构设计

```
~/.skillstack/
├── repository/           # 中央仓库（单源真相）
│   ├── skill-1/
│   │   └── SKILL.md
│   └── skill-2/
│       └── SKILL.md
├── manifest.json        # 状态跟踪（hash、时间戳）
└── config.json          # 配置（编辑器、自动同步）

~/.claude/skills -> ~/.skillstack/repository  # symlink
```

**核心原理**：通过目录级 symlink，Claude Code 直接读取中央仓库，实现零延迟同步。

## ✅ 测试状态

**MVP 完成度：100%**

- ✅ 10/10 命令全部通过手动测试
- ✅ 8/8 单元测试通过
- ✅ 1/1 集成测试通过
- ✅ Claude Code 集成验证通过
  - 新增 skill 立即可见
  - 修改 skill 立即生效
  - 删除 skill 立即消失
- ✅ Release 编译成功

## 📦 项目管理命令 (阶段2 ✅)

### 自动扫描（推荐）⭐

```bash
# 扫描工作区，自动注册所有项目
skillstack project scan /path/to/workspace

# 扫描 Cursor 项目
skillstack project scan /path/to/workspace --tool cursor
```

### 手动管理

- `project add <path>` - 手动注册单个项目
- `project list` - 列出所有注册的项目
- `project remove <name>` - 移除项目注册
- `project sync <name>` - 同步 skills 到项目
  - `--all-projects` - 同步到所有项目
  - `--force` - 强制覆盖 override
  - `--parallel` - 并行同步（多项目时更快）⚡
  - `--json` - JSON 格式输出（适合脚本）💻
  - `--dry-run` - 预览同步（不执行实际操作）
- `project detect-overrides` - 检测项目中被修改的 skills

### Skill 安装

- `install <skill> --project <name>` - 安装 skill 到项目
- `uninstall <skill> --project <name>` - 从项目卸载 skill
- `list --project <name>` - 查看项目的 skills（显示来源：override/global/local）
- `diff <skill> --project <name>` - 对比项目版本和全局版本差异

## 📝 开发计划

当前版本：**v0.2.0-dev** (2026-04-07)

已完成：
- ✅ 阶段1: 全局 Skill 管理（MVP）
- ✅ 阶段2: 项目级 Skill 管理
  - ✅ 项目注册和管理
  - ✅ **自动扫描批量注册** ⭐
  - ✅ Override 检测和保护
  - ✅ 批量同步
  - ✅ Diff 差异对比

下一步（阶段3）：
- [ ] 版本管理
- [ ] GUI 界面（可选）

详见 `docs/AUTO-SCAN-FEATURE.md`、`docs/PHASE2-PROGRESS.md` 和 `docs/TEST-REPORT.md`

## 🛠️ 技术栈

- Rust 2021
- Clap 4.5 (CLI)
- serde/serde_json (序列化)
- serde_yaml (frontmatter)
- sha2 (hash)
- chrono (时间)
- colored (输出)
- dialoguer (交互)

## 📄 License

MIT
