# SkillStack 项目级管理设计方案

**阶段 2 核心功能**：从全局管理扩展到项目级管理

---

## 📋 当前状态（MVP v0.1.0）

### 现有功能
- ✅ 全局 skill 管理（`~/.skillstack/repository`）
- ✅ 通过 symlink 同步到 `~/.claude/skills`
- ✅ 所有项目共享相同的 skills

### 限制
- ❌ 无法为不同项目配置不同的 skills
- ❌ 无法在项目级别 override 全局 skill
- ❌ 无法追踪 skill 在哪些项目中被使用

---

## 🎯 项目级管理的核心概念

### 什么是项目级管理？

允许你为不同的项目配置不同的 skills，同时保持中央仓库作为单一真相来源。

**核心原理**：三层优先级体系（符合 Claude Code 官方设计）

```
Project-level skills    (最高优先级 - 项目特定)
    ↓ 如果没有，则查找
User-level skills       (中等优先级 - 全局共享)
    ↓ 如果没有，则查找  
Bundled skills          (最低优先级 - 系统内置)
```

### 架构设计

```
~/.skillstack/
├── repository/                    # 全局 skills（单一真相源）
│   ├── skill-a/
│   ├── skill-b/
│   └── skill-c/
├── projects.json                  # 项目注册表
├── manifest.json                  # 全局状态
└── config.json                    # 全局配置

/path/to/project-1/.claude/skills/  # 项目级 skills
├── skill-a/                        # override 全局 skill-a
└── skill-d/                        # 项目特有 skill

/path/to/project-2/.claude/skills/  # 另一个项目
└── skill-b/                        # override 全局 skill-b
```

### 使用场景示例

**场景 1：不同项目需要不同的 skills**

```bash
# 项目 A（后端项目）只需要数据库相关的 skills
skillstack project use project-a --skills db-migration,api-design

# 项目 B（前端项目）只需要 UI 相关的 skills  
skillstack project use project-b --skills react-component,css-design

# 项目 C（全栈项目）需要所有 skills
skillstack project use project-c --all
```

**场景 2：项目级 override**

```bash
# 全局有一个通用的 "commit-helper" skill
# 但项目 A 需要特殊的 commit 规范（比如 Jira ticket）

# 为项目 A 创建特殊版本的 commit-helper
skillstack project override project-a commit-helper
# 编辑器打开，修改内容...

# 现在：
# - 在项目 A 中，Claude 使用项目级的 commit-helper
# - 在其他项目中，Claude 使用全局的 commit-helper
```

**场景 3：实验性 skill**

```bash
# 在项目 A 中测试一个新的 skill，不影响其他项目
skillstack project add project-a experimental-skill

# 测试通过后，提升为全局 skill
skillstack promote project-a experimental-skill
```

---

## 🏗️ 核心功能设计

### 1. 项目注册与管理

#### 添加项目
```bash
# 手动添加单个项目
skillstack project add /path/to/my-project --name my-project

# 自动扫描并添加所有子项目
skillstack project scan /path/to/workspace

# 示例输出：
# 🔍 Found 3 projects:
#   📁 /workspace/backend-api
#   📁 /workspace/frontend-app
#   📁 /workspace/mobile-app
# Add all? (yes/no): yes
# ✅ Added 3 projects
```

#### 列出所有项目
```bash
skillstack project list

# 输出示例：
# NAME              PATH                          SKILLS    LAST SYNC
# -------------------------------------------------------------------------
# backend-api       /workspace/backend-api        5         2h ago
# frontend-app      /workspace/frontend-app       3         1d ago
# mobile-app        /workspace/mobile-app         0         never
#
# Total: 3 projects
```

#### 查看项目详情
```bash
skillstack project show backend-api

# 输出示例：
# Project: backend-api
# Path: /workspace/backend-api
# Skills (5):
#   - db-migration (override)    [项目级，覆盖全局]
#   - api-design (global)        [来自全局]
#   - test-runner (global)       [来自全局]
#   - commit-helper (override)   [项目级，覆盖全局]
#   - backend-only (local)       [项目独有]
# Last Sync: 2h ago
# Status: ✅ All synced
```

---

### 2. 项目级 Skill 管理

#### 为项目安装 skill（从全局仓库）
```bash
# 安装单个 skill
skillstack project install backend-api db-migration

# 安装多个 skills
skillstack project install backend-api db-migration,api-design,test-runner

# 安装所有全局 skills
skillstack project install backend-api --all
```

#### 为项目创建特有 skill
```bash
# 创建仅在该项目中使用的 skill
skillstack project create backend-api backend-specific-skill

# 这会在项目的 .claude/skills/ 下创建
# 同时记录到 projects.json 中
```

#### Override 全局 skill
```bash
# 为项目创建全局 skill 的覆盖版本
skillstack project override backend-api commit-helper

# 流程：
# 1. 从全局仓库复制 commit-helper 到项目目录
# 2. 打开编辑器让你修改
# 3. 标记为 override（在 projects.json 中记录）
```

#### 移除项目的 skill
```bash
# 移除项目级 skill（不影响全局）
skillstack project remove backend-api backend-specific-skill

# 移除 override（恢复使用全局版本）
skillstack project restore backend-api commit-helper
```

---

### 3. 同步管理

#### 同步单个项目
```bash
# 同步指定项目（从全局仓库更新）
skillstack project sync backend-api

# 强制同步（覆盖本地修改，除了 override）
skillstack project sync backend-api --force
```

#### 同步所有项目
```bash
# 同步所有已注册项目
skillstack project sync --all

# 输出示例：
# Syncing 3 projects...
# ✅ backend-api: 5 skills synced
# ✅ frontend-app: 3 skills synced
# ⚠️  mobile-app: Skipped (no skills configured)
```

#### 检查同步状态
```bash
skillstack project status

# 输出示例：
# PROJECT           GLOBAL    OVERRIDE    LOCAL    DRIFT
# ---------------------------------------------------------------
# backend-api       3         2           1        0
# frontend-app      3         0           0        1 ⚠️
# mobile-app        0         0           0        0
#
# Legend:
# - GLOBAL: 使用全局 skill 的数量
# - OVERRIDE: 覆盖全局 skill 的数量
# - LOCAL: 项目特有 skill 的数量
# - DRIFT: 与全局版本不一致的数量（需要同步）
```

---

### 4. 冲突解决与 Diff

#### 检测漂移（drift）
```bash
# 检测哪些项目的 skills 与全局不一致
skillstack project drift

# 输出示例：
# Project: frontend-app
#   Skill: api-design
#     Global hash: sha256:abc123...
#     Project hash: sha256:def456...
#     Status: MODIFIED ⚠️
#     Action: Run 'skillstack project sync frontend-app' to update
```

#### 查看差异
```bash
# 对比项目 skill 与全局版本的差异
skillstack project diff frontend-app api-design

# 输出类似 git diff：
# --- Global: ~/.skillstack/repository/api-design/SKILL.md
# +++ Project: /workspace/frontend-app/.claude/skills/api-design/SKILL.md
# @@ -5,7 +5,7 @@
# -description: Generic API design patterns
# +description: REST API design for this project
```

#### 选择性同步
```bash
# 仅同步有漂移的 skills
skillstack project sync backend-api --drift-only

# 交互式选择要同步的 skills
skillstack project sync backend-api --interactive

# 示例：
# Found 3 skills with updates:
#   [ ] api-design (1 day old)
#   [x] db-migration (3 days old)  
#   [x] test-runner (1 week old)
# Sync selected? (yes/no): yes
```

---

### 5. Skill 使用追踪

#### 查看 skill 被哪些项目使用
```bash
skillstack show commit-helper --usage

# 输出示例：
# Skill: commit-helper
# Description: Git commit helper with conventions
# 
# Used by 5 projects:
#   ✅ backend-api (override)
#   ✅ frontend-app (global)
#   ✅ mobile-app (global)
#   ✅ data-pipeline (override)
#   ❌ legacy-project (disabled)
```

#### 删除全局 skill 时的影响分析
```bash
skillstack delete api-design --dry-run

# 输出示例：
# ⚠️  This skill is used by 3 projects:
#   - backend-api (global)
#   - frontend-app (global)
#   - mobile-app (override - will keep project version)
# 
# If deleted:
#   - backend-api will lose this skill ❌
#   - frontend-app will lose this skill ❌
#   - mobile-app will keep override version ✅
# 
# Continue? (yes/no):
```

---

## 📊 数据结构设计

### projects.json（项目注册表）

```json
{
  "version": "1.0",
  "projects": {
    "backend-api": {
      "name": "backend-api",
      "path": "/workspace/backend-api",
      "tool": "claude",
      "skills_path": ".claude/skills",
      "created_at": "2026-04-07T10:00:00Z",
      "last_sync": "2026-04-07T12:30:00Z",
      "skills": {
        "db-migration": {
          "type": "override",
          "source": "global",
          "hash": "sha256:abc123...",
          "synced_at": "2026-04-07T12:30:00Z"
        },
        "api-design": {
          "type": "global",
          "hash": "sha256:def456...",
          "synced_at": "2026-04-07T12:30:00Z"
        },
        "backend-only": {
          "type": "local",
          "hash": "sha256:ghi789...",
          "created_at": "2026-04-06T15:00:00Z"
        }
      }
    },
    "frontend-app": {
      "name": "frontend-app",
      "path": "/workspace/frontend-app",
      "tool": "claude",
      "skills_path": ".claude/skills",
      "skills": {
        "react-component": {
          "type": "global",
          "hash": "sha256:jkl012..."
        }
      }
    }
  }
}
```

### Skill 类型说明

| 类型 | 说明 | 示例 |
|------|------|------|
| `global` | 从全局仓库 symlink 或 copy | 大部分常用 skills |
| `override` | 覆盖全局版本的项目特定版本 | 项目特殊的 commit 规范 |
| `local` | 仅在该项目中使用的 skill | 实验性功能 |

---

## 🔄 同步策略

### 方案 A：Symlink（推荐）

**优点**：
- 实时同步，修改立即生效
- 节省磁盘空间
- 符合 MVP 已验证的方案

**缺点**：
- 无法 override（symlink 指向同一文件）
- Windows 支持有限

**适用场景**：全局 skills（`type: global`）

### 方案 B：Copy + Hash 追踪

**优点**：
- 支持 override
- 跨平台兼容
- 可独立修改

**缺点**：
- 需要手动同步
- 占用更多空间
- 可能产生漂移

**适用场景**：
- Override skills（`type: override`）
- Local skills（`type: local`）

### 混合策略（最终方案）

```
全局 skills (type: global)
  → 使用 symlink 到中央仓库
  → 实时同步，零延迟

Override skills (type: override)  
  → Copy 到项目目录
  → 允许独立修改
  → 通过 hash 检测漂移

Local skills (type: local)
  → 仅存在于项目目录
  → 不与全局仓库关联
```

---

## 🛠️ 实现步骤（阶段 2）

### 任务 1：项目注册表（1 天）

**文件**：
- `src/core/project.rs` - Project 结构和验证
- `src/core/project_registry.rs` - 项目注册表管理

**功能**：
- ✅ Project 结构定义
- ✅ 读取/保存 projects.json
- ✅ 添加/移除/列出项目
- ✅ 扫描项目目录

### 任务 2：项目级 Skill CRUD（2 天）

**文件**：
- `src/core/project_skill.rs` - 项目级 skill 管理

**功能**：
- ✅ 安装 global skill 到项目（symlink）
- ✅ 创建 override（copy + 标记）
- ✅ 创建 local skill
- ✅ 移除项目 skill
- ✅ 恢复到 global 版本

### 任务 3：同步引擎增强（1 天）

**文件**：
- `src/core/sync.rs` - 增强版同步引擎

**功能**：
- ✅ 同步单个项目
- ✅ 同步所有项目
- ✅ Hash 比对检测漂移
- ✅ 选择性同步

### 任务 4：CLI 命令（2 天）

**文件**：
- `src/cli/project_commands.rs` - 项目级命令

**命令**：
- `project add/remove/list/show`
- `project install/create/override/restore`
- `project sync/status/diff`

### 任务 5：测试与文档（1 天）

- 单元测试
- 集成测试
- 更新文档

**总计：7 工作日（约 1.5 周）**

---

## 🎯 MVP+1 完成标准

1. ✅ 可以注册和管理多个项目
2. ✅ 可以为项目安装/移除 global skills
3. ✅ 可以创建项目级 override
4. ✅ 可以创建项目特有的 local skills
5. ✅ 可以同步项目（检测漂移）
6. ✅ 可以查看 skill 在哪些项目中使用
7. ✅ 所有测试通过
8. ✅ 文档完整

---

## 💡 临时解决方案（当前可用）

如果你现在就需要项目级管理，可以手动操作：

### 方案 1：手动 symlink 特定 skills

```bash
# 假设你只想在项目 A 中使用 skill-a 和 skill-b
cd /path/to/project-a/.claude/skills

# 创建目录
mkdir -p .

# Symlink 特定 skills
ln -s ~/.skillstack/repository/skill-a ./skill-a
ln -s ~/.skillstack/repository/skill-b ./skill-b

# 不要 symlink 整个目录，否则会包含所有 skills
```

### 方案 2：使用 Git 分支管理不同配置

```bash
# 在全局仓库中为不同项目创建分支
cd ~/.skillstack/repository

git checkout -b project-a-config
# 删除不需要的 skills...

git checkout -b project-b-config  
# 删除不需要的 skills...

# 然后为每个项目 symlink 对应的分支
# （需要手动管理，不推荐）
```

### 方案 3：多个 skillstack 实例

```bash
# 为每个项目创建独立的 skillstack 实例
# 项目 A
export SKILLSTACK_HOME=~/.skillstack-project-a
skillstack init --path /project-a/.claude/skills

# 项目 B
export SKILLSTACK_HOME=~/.skillstack-project-b
skillstack init --path /project-b/.claude/skills

# （不推荐，违背单一真相源原则）
```

**结论**：临时方案都有明显缺点，建议等待阶段 2 实现。

---

## 🚀 立即开始实现？

如果你想立即开始实现项目级管理，我可以：

1. **编写详细的实现计划**（类似 MVP 的任务分解）
2. **逐步实现所有功能**（约 1.5 周）
3. **完整测试验证**

或者你可以：

- 先使用临时方案（手动 symlink）
- 等我后续实现阶段 2
- 根据实际需求调整优先级

你想怎么做？
