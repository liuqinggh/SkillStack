# SkillStack MVP 详细设计文档

**版本**: v1.0-MVP  
**日期**: 2026-04-03  
**状态**: 已批准  
**目标**: 2周完成MVP核心功能

---

## 1. 项目概述

### 1.1 产品定位

**SkillStack** 是一个专为 Claude Code 用户设计的 Skill 集中管理工具，解决"Skill分散、手动复制、版本混乱"的核心痛点。

### 1.2 MVP范围

**包含功能**:
- ✅ 全局Skill的集中式管理（中央仓库）
- ✅ 完整的CRUD操作（创建、读取、编辑、删除）
- ✅ 自动同步到Claude Code（symlink机制）
- ✅ 现有Skill的导入
- ✅ 健康检查和状态追踪
- ✅ CLI命令行界面

**不包含**:
- ❌ 项目级Skill管理（阶段2）
- ❌ 版本管理和历史回滚（阶段3）
- ❌ GUI图形界面（阶段3）
- ❌ 云同步和团队共享（阶段4）

### 1.3 技术选型

| 层级 | 技术选型 | 理由 |
|------|---------|------|
| CLI | Rust + Clap | 性能好、单二进制、跨平台 |
| 存储 | 文件系统 + JSON | 无需额外DB，Git友好 |
| 同步 | 目录级Symlink | macOS原生支持，实时同步 |
| Hash | SHA256 | 文件完整性校验 |

### 1.4 目标平台

**MVP优先**: macOS  
**后续扩展**: Linux, Windows

---

## 2. 总体架构

### 2.1 架构图

```
┌─────────────────────────────────────────┐
│  CLI Commands (Clap)                    │
│  init/list/add/edit/delete/sync/...     │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Core Library (Rust)                    │
│  ├─ Repository Manager                  │
│  ├─ Skill CRUD                          │
│  ├─ Sync Engine                         │
│  └─ Manifest Manager                    │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  File System                            │
│  ~/.skillstack/repository/              │
│  ~/.skillstack/manifest.json            │
│  ~/.claude/skills/ (symlink)            │
└─────────────────────────────────────────┘
```

### 2.2 核心概念

- **中央仓库**: `~/.skillstack/repository/` - 所有Skill的单源真相
- **Manifest**: `~/.skillstack/manifest.json` - 状态追踪和元数据
- **Symlink**: `~/.claude/skills/` → `~/.skillstack/repository/` - 实时同步
- **Skill**: 包含SKILL.md的目录单元

---

## 3. 数据结构设计

### 3.1 目录结构

```
~/.skillstack/
├── repository/              # 中央仓库（单源真相）
│   ├── skill-commit-helper/
│   │   └── SKILL.md
│   ├── skill-code-review/
│   │   └── SKILL.md
│   └── skill-debugging/
│       └── SKILL.md
├── manifest.json           # 状态追踪
└── config.json            # 用户配置

~/.claude/skills/          # symlink -> ~/.skillstack/repository/
```

### 3.2 manifest.json 结构

```json
{
  "version": "1.0",
  "skills": {
    "skill-commit-helper": {
      "name": "skill-commit-helper",
      "created_at": "2026-04-03T10:00:00Z",
      "updated_at": "2026-04-03T12:30:00Z",
      "hash": "sha256:abc123...",
      "path": "repository/skill-commit-helper"
    },
    "skill-code-review": {
      "name": "skill-code-review",
      "created_at": "2026-04-03T11:00:00Z",
      "updated_at": "2026-04-03T11:00:00Z",
      "hash": "sha256:def456...",
      "path": "repository/skill-code-review"
    }
  },
  "sync_status": {
    "claude_skills_path": "/Users/username/.claude/skills",
    "last_sync": "2026-04-03T12:30:00Z",
    "sync_method": "symlink"
  }
}
```

**字段说明**:
- `version`: manifest格式版本
- `skills`: 所有Skill的记录
  - `name`: Skill名称（唯一标识）
  - `created_at`: 创建时间（ISO 8601）
  - `updated_at`: 最后修改时间
  - `hash`: SKILL.md的SHA256哈希值（用于漂移检测）
  - `path`: 相对于 `~/.skillstack/` 的路径
- `sync_status`: 同步状态
  - `claude_skills_path`: Claude skills目录的绝对路径
  - `last_sync`: 最后同步时间
  - `sync_method`: 同步方式（symlink或copy）

### 3.3 config.json 结构

```json
{
  "claude_skills_path": "/Users/username/.claude/skills",
  "editor": "code",
  "auto_sync": true
}
```

**字段说明**:
- `claude_skills_path`: Claude skills目录路径
- `editor`: 默认编辑器（code/vim/nano等）
- `auto_sync`: 修改后是否自动同步

### 3.4 SKILL.md Frontmatter

```yaml
---
name: skill-commit-helper
description: Git提交辅助工具
---

# Skill内容
...
```

**MVP必需字段**:
- `name`: Skill名称（必须与目录名一致）
- `description`: 简短描述

**命名规则**:
- 只能包含小写字母、数字、连字符
- 必须以字母开头
- 示例: `skill-commit`, `my-skill-v2`

---

## 4. CLI命令规范

### 4.1 P0核心命令（必须实现）

#### 4.1.1 skillstack init

**功能**: 初始化中央仓库，导入现有skills

**语法**:
```bash
skillstack init [OPTIONS]
```

**选项**:
- `--force`: 强制重新初始化（覆盖现有仓库）
- `--no-import`: 跳过导入现有skills

**执行流程**:
1. 检查 `~/.skillstack/` 是否已存在
2. 创建目录结构和配置文件
3. 检测 `~/.claude/skills/` 中的现有skills
4. 提示用户是否导入
5. 导入skills到中央仓库
6. 创建symlink

**输出示例**:
```
🔍 发现 5 个现有 skills
📋 skill-commit, skill-review, skill-debug, skill-test, skill-docs
❓ 是否导入到中央仓库？(Y/n) y
✅ 已导入 5 个 skills
🔗 Symlink 创建: ~/.claude/skills -> ~/.skillstack/repository
✅ SkillStack 初始化完成！

Next steps:
  - skillstack list          查看所有skills
  - skillstack add <name>    创建新skill
```

#### 4.1.2 skillstack list

**功能**: 列出所有skills

**语法**:
```bash
skillstack list [OPTIONS]
```

**选项**:
- `--sort <FIELD>`: 排序字段（name/created/updated，默认name）
- `--reverse`: 反向排序

**输出示例**:
```
NAME                    DESCRIPTION                      UPDATED
skill-commit-helper     Git提交辅助工具                  2h ago
skill-code-review       代码审查工具                     1d ago
skill-debugging         系统调试工具                     3d ago

Total: 3 skills
```

#### 4.1.3 skillstack add

**功能**: 创建新skill

**语法**:
```bash
skillstack add <NAME> [OPTIONS]
```

**选项**:
- `--editor <EDITOR>`: 指定编辑器（覆盖config）
- `--no-edit`: 创建后不打开编辑器

**执行流程**:
1. 验证skill名称格式
2. 检查名称是否已存在
3. 创建skill目录
4. 生成模板SKILL.md（含frontmatter）
5. 打开编辑器
6. 更新manifest.json
7. 自动sync（如果auto_sync=true）

**输出示例**:
```
✅ Skill 'my-new-skill' 创建成功
📝 正在打开编辑器...
(编辑器关闭后)
✅ 已保存并同步
```

#### 4.1.4 skillstack edit

**功能**: 编辑现有skill

**语法**:
```bash
skillstack edit <NAME> [OPTIONS]
```

**选项**:
- `--editor <EDITOR>`: 指定编辑器

**执行流程**:
1. 检查skill是否存在
2. 打开SKILL.md
3. 编辑后计算新hash
4. 更新manifest（hash, updated_at）
5. 自动sync

**输出示例**:
```
📝 正在编辑 'skill-commit-helper'...
(编辑器关闭后)
✅ 已保存并同步
```

#### 4.1.5 skillstack delete

**功能**: 删除skill

**语法**:
```bash
skillstack delete <NAME> [OPTIONS]
```

**选项**:
- `--force, -f`: 跳过确认提示

**执行流程**:
1. 检查skill是否存在
2. 提示确认（除非--force）
3. 删除skill目录
4. 从manifest移除记录
5. 自动sync

**输出示例**:
```
⚠️  即将删除 'old-skill'
此操作不可撤销。
继续？(y/N) y
✅ Skill 'old-skill' 已删除
```

#### 4.1.6 skillstack sync

**功能**: 同步到Claude skills目录

**语法**:
```bash
skillstack sync [OPTIONS]
```

**选项**:
- `--force`: 强制重建symlink

**执行流程**:
1. 验证symlink有效性
2. 如果损坏，重新创建
3. 更新manifest的last_sync
4. 输出同步结果

**输出示例**:
```
✅ 已同步 5 个 skills 到 ~/.claude/skills
```

#### 4.1.7 skillstack import

**功能**: 导入外部skill

**语法**:
```bash
skillstack import <PATH> [OPTIONS]
```

**参数**:
- `PATH`: 文件路径或目录路径

**选项**:
- `--name <NAME>`: 指定skill名称（默认从文件名推断）

**执行流程**:
1. 读取目标路径
2. 验证是否为有效skill（有SKILL.md和frontmatter）
3. 复制到repository
4. 更新manifest
5. 自动sync

**输出示例**:
```
✅ 已导入 'external-skill' 从 /path/to/skill
```

### 4.2 P1增强命令（时间允许）

#### 4.2.1 skillstack show

**功能**: 查看skill详细信息

**语法**:
```bash
skillstack show <NAME>
```

**输出示例**:
```
Name: skill-commit-helper
Description: Git提交辅助工具
Created: 2026-04-03 10:00:00
Updated: 2026-04-03 12:30:00
Path: ~/.skillstack/repository/skill-commit-helper
Hash: sha256:abc123def456...
```

#### 4.2.2 skillstack doctor

**功能**: 健康检查和诊断

**语法**:
```bash
skillstack doctor [OPTIONS]
```

**选项**:
- `--fix`: 自动修复检测到的问题

**检查项**:
1. 目录结构完整性
2. Symlink有效性
3. Manifest一致性（文件vs记录）
4. Hash匹配（检测手动修改）
5. Frontmatter格式

**输出示例**:
```
🏥 健康检查中...

✅ 目录结构: OK
✅ Symlink: OK
✅ Manifest: OK
⚠️  检测到 1 个问题:
  - skill-modified: hash不匹配（检测到手动修改）

建议: 运行 'skillstack sync' 更新hash
```

#### 4.2.3 skillstack status

**功能**: 显示同步状态

**语法**:
```bash
skillstack status
```

**输出示例**:
```
Repository: ~/.skillstack/repository (5 skills)
Claude Path: ~/.claude/skills (symlink ✅)
Last Sync: 2026-04-03 12:30:00 (2 hours ago)
Status: All synced ✅
```

### 4.3 通用选项

所有命令支持:
- `--help, -h`: 显示帮助
- `--version, -v`: 显示版本
- `--verbose`: 详细输出
- `--quiet, -q`: 静默模式（仅错误）

---

## 5. 核心流程设计

### 5.1 初始化流程（skillstack init）

```
1. 检查 ~/.skillstack/ 是否已存在
   ├─ 存在 → 报错："Already initialized"
   └─ 不存在 → 继续

2. 创建目录结构
   ├─ mkdir -p ~/.skillstack/repository/
   └─ 生成默认 config.json

3. 检测现有 skills
   ├─ 检查 ~/.claude/skills/ 是否存在
   ├─ 扫描目录下所有 SKILL.md 文件
   └─ 列出发现的 skills

4. 提示用户导入
   "🔍 发现 5 个现有 skills，是否导入？(Y/n)"
   ├─ Y → 继续导入
   └─ n → 跳过导入

5. 导入 skills
   ├─ 复制每个 skill 到 repository/
   ├─ 计算文件 hash (SHA256)
   ├─ 验证 frontmatter 格式
   └─ 更新 manifest.json

6. 创建 symlink
   ├─ 备份原目录 ~/.claude/skills.backup/
   ├─ rm -rf ~/.claude/skills/
   └─ ln -s ~/.skillstack/repository/ ~/.claude/skills

7. 完成输出
```

### 5.2 同步引擎（skillstack sync）

MVP阶段的sync非常简单（因为使用目录级symlink）：

```
1. 验证 symlink 有效性
   ├─ 检查 ~/.claude/skills 是否是 symlink
   ├─ 检查指向是否正确（→ ~/.skillstack/repository/）
   └─ 如果损坏 → 重新创建

2. 更新 manifest.json
   └─ 设置 sync_status.last_sync = 当前时间

3. 输出结果
   "✅ Synced X skills to ~/.claude/skills"

注: 因为是symlink，实际上不需要复制文件。
    阶段2加入项目级管理后，sync会变复杂。
```

### 5.3 漂移检测（skillstack doctor）

```
1. 检查目录结构
   ├─ ~/.skillstack/repository/ 存在？
   ├─ ~/.skillstack/manifest.json 存在？
   └─ ~/.skillstack/config.json 存在？

2. 检查 symlink
   ├─ ~/.claude/skills 是 symlink？
   ├─ 指向正确？
   └─ 有读写权限？

3. 检查 manifest 一致性
   对每个 skill：
   ├─ manifest 中有记录但文件不存在
   │  → "❌ Missing: skill-xxx"
   ├─ 文件存在但 manifest 无记录
   │  → "⚠️  Untracked: skill-yyy"
   └─ hash 不匹配
      → "⚠️  Modified: skill-zzz"

4. 检查 SKILL.md 格式
   对每个 skill：
   ├─ frontmatter 存在？
   ├─ name 字段存在且匹配目录名？
   └─ description 字段存在？

5. 输出报告 + 修复建议
```

---

## 6. 错误处理和边界情况

### 6.1 用户输入错误

**Skill不存在**:
```
$ skillstack edit non-existent
❌ Error: Skill 'non-existent' not found
💡 Tip: Run 'skillstack list' to see all skills
```

**重复的skill名称**:
```
$ skillstack add existing-skill
❌ Error: Skill 'existing-skill' already exists
💡 Tip: Use 'skillstack edit existing-skill' to modify it
```

**无效的skill名称**:
```
$ skillstack add "my skill"
❌ Error: Invalid skill name
💡 Use lowercase letters, numbers, and hyphens only
   Example: my-skill, skill-v2
```

### 6.2 文件系统错误

**权限不足**:
```
❌ Error: Permission denied: cannot create ~/.skillstack/
💡 Tip: Check directory permissions
```

**磁盘空间不足**:
```
❌ Error: No space left on device
💡 Tip: Free up disk space and try again
```

**Symlink创建失败**:
```
❌ Error: Failed to create symlink
💡 Tip: Your filesystem may not support symlinks
```

### 6.3 数据完整性错误

**manifest.json损坏**:
```
❌ Error: Cannot parse manifest.json (invalid JSON)
💡 Tip: Run 'skillstack doctor --fix' to attempt recovery
```

**SKILL.md frontmatter格式错误**:
```
❌ Error: Invalid frontmatter in SKILL.md
  - Missing required field: 'name'
  - Missing required field: 'description'
💡 Tip: Check the frontmatter format
```

### 6.4 边界情况处理

**首次运行未初始化**:
```
$ skillstack list
❌ Error: SkillStack not initialized
💡 Run 'skillstack init' first
```

**Claude skills目录已存在但不是symlink**:
```
$ skillstack init
⚠️  ~/.claude/skills/ already exists
Options:
  1) Import and replace with symlink (recommended)
  2) Cancel initialization
Your choice (1/2):
```

**空仓库操作**:
```
$ skillstack list
No skills found.
💡 Run 'skillstack add <name>' to create your first skill
```

**删除确认**:
```
$ skillstack delete important-skill
⚠️  即将删除 'important-skill'
此操作不可撤销。
继续？(y/N): n
已取消
```

---

## 7. 测试策略

### 7.1 单元测试范围

**Repository Manager测试**:
- `test_create_skill()`: 创建skill，验证目录和文件生成
- `test_delete_skill()`: 删除skill，验证清理干净
- `test_list_skills()`: 列表功能，验证排序

**Manifest Manager测试**:
- `test_add_skill_to_manifest()`: 添加skill记录
- `test_update_skill_hash()`: 更新hash和时间戳
- `test_manifest_corruption_recovery()`: 损坏恢复

**Sync Engine测试**:
- `test_create_symlink()`: 创建symlink
- `test_recreate_broken_symlink()`: 修复损坏symlink

**Frontmatter Parser测试**:
- `test_parse_valid_frontmatter()`: 解析正确格式
- `test_reject_invalid_frontmatter()`: 拒绝无效格式

**Hash Calculator测试**:
- `test_file_hash_consistency()`: hash一致性
- `test_detect_file_changes()`: 检测文件变化

### 7.2 集成测试场景

**完整工作流测试**:
```rust
#[test]
fn test_full_workflow() {
    // 1. init - 初始化空仓库
    // 2. add - 创建3个skills
    // 3. list - 验证列表正确
    // 4. edit - 修改一个skill
    // 5. sync - 验证同步成功
    // 6. doctor - 健康检查通过
    // 7. delete - 删除一个skill
    // 8. list - 验证删除后列表正确
}
```

**导入现有skills测试**:
```rust
#[test]
fn test_init_with_existing_skills() {
    // 1. 创建测试用的 ~/.claude/skills/ 含2个skills
    // 2. init - 导入现有skills
    // 3. 验证symlink创建
    // 4. 验证manifest正确
}
```

**故障恢复测试**:
```rust
#[test]
fn test_recovery_from_corruption() {
    // 1. 创建正常仓库
    // 2. 故意破坏manifest.json
    // 3. doctor - 检测问题
    // 4. 修复或重建manifest
}
```

### 7.3 手动测试清单（MVP发布前）

**基础功能**:
- [ ] `skillstack init` 首次初始化成功
- [ ] `skillstack init` 导入现有skills成功
- [ ] `skillstack list` 显示正确
- [ ] `skillstack add` 创建skill并打开编辑器
- [ ] `skillstack edit` 打开正确的文件
- [ ] `skillstack delete` 删除后文件消失
- [ ] `skillstack sync` symlink正确
- [ ] `skillstack show` 显示详细信息
- [ ] `skillstack doctor` 检测问题
- [ ] `skillstack status` 显示状态

**错误处理**:
- [ ] 未初始化时执行命令报错友好
- [ ] 不存在的skill报错友好
- [ ] 重复skill名称报错友好
- [ ] 损坏的manifest可恢复或报错
- [ ] 无效frontmatter报错清晰

**边界情况**:
- [ ] 空仓库操作正常
- [ ] Skill名称验证正确
- [ ] Symlink损坏后可修复

**Claude Code集成**:
- [ ] Claude能正常读取symlink的skills
- [ ] 在Claude中调用skill成功
- [ ] 修改skill后Claude立即生效

---

## 8. 项目结构

### 8.1 Rust项目结构

```
skillstack/
├── Cargo.toml
├── Cargo.lock
├── README.md
├── LICENSE
├── CHANGELOG.md
├── src/
│   ├── main.rs              # CLI入口
│   ├── lib.rs               # 库入口
│   ├── cli/
│   │   └── commands.rs      # Clap命令定义
│   ├── core/
│   │   ├── repository.rs    # Repository Manager
│   │   ├── manifest.rs      # Manifest Manager
│   │   ├── skill.rs         # Skill结构和操作
│   │   └── sync.rs          # Sync Engine
│   └── utils/
│       ├── hash.rs          # Hash计算
│       ├── frontmatter.rs   # YAML解析
│       └── fs.rs            # 文件系统辅助
└── tests/
    ├── integration_test.rs  # 集成测试
    └── fixtures/            # 测试fixtures
```

### 8.2 依赖清单（Cargo.toml）

```toml
[package]
name = "skillstack"
version = "0.1.0"
edition = "2021"
authors = ["Your Name <your.email@example.com>"]
description = "Centralized skill management for Claude Code"
license = "MIT"
repository = "https://github.com/yourusername/skillstack"

[dependencies]
clap = { version = "4.5", features = ["derive"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
serde_yaml = "0.9"
sha2 = "0.10"
chrono = "0.4"
anyhow = "1.0"
colored = "2.1"
dialoguer = "0.11"
walkdir = "2.5"

[dev-dependencies]
tempfile = "3.10"
```

---

## 9. 开发路线图

### 9.1 Week 1: 核心基础设施

**Day 1-2: 项目搭建 + 数据结构**
- [ ] 初始化Rust项目（Cargo.toml, 依赖）
- [ ] 创建项目模块结构
- [ ] 实现数据结构（Manifest, Skill, Config的struct）
- [ ] 实现manifest.json的读写

**Day 3-4: P0核心命令（上半）**
- [ ] `skillstack init`
  - 创建目录结构
  - 扫描现有skills
  - 导入逻辑
  - 创建symlink
- [ ] `skillstack list`
  - 读取manifest
  - 格式化输出（表格）
- [ ] `skillstack add`
  - 创建skill目录
  - 生成模板SKILL.md
  - 打开编辑器
  - 更新manifest

**Day 5: P0核心命令（下半）**
- [ ] `skillstack edit`
  - 打开编辑器
  - 更新hash和时间戳
- [ ] `skillstack delete`
  - 确认提示
  - 删除文件
  - 更新manifest
- [ ] `skillstack sync`
  - 验证symlink
  - 重建symlink（如需）

### 9.2 Week 2: 增强功能 + 测试

**Day 6-7: P0收尾 + P1命令**
- [ ] `skillstack import`
  - 支持单文件和目录
  - 验证frontmatter
  - 复制到repository
- [ ] `skillstack show`
  - 显示详细信息
- [ ] `skillstack doctor`
  - 检查symlink
  - 检查manifest一致性
  - 检查frontmatter格式
- [ ] `skillstack status`
  - 显示同步状态

**Day 8-9: 完善和测试**
- [ ] 编写单元测试（覆盖核心模块）
- [ ] 编写集成测试（完整工作流）
- [ ] 错误处理完善
- [ ] 用户友好的错误消息
- [ ] 添加 --verbose 和 --quiet 支持
- [ ] 完善 --help 文档

**Day 10: 集成测试 + 文档**
- [ ] 在真实Claude Code环境测试
- [ ] 手动测试checklist全部通过
- [ ] 编写 README.md
- [ ] 编写 CHANGELOG.md
- [ ] 准备发布

---

## 10. 发布和后续规划

### 10.1 MVP发布清单

**代码质量**:
- [ ] 所有P0命令功能完整
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试通过
- [ ] 手动测试checklist全部通过
- [ ] 没有已知的critical bugs

**文档**:
- [ ] README.md（简介、安装、快速开始、命令参考、FAQ）
- [ ] CHANGELOG.md
- [ ] LICENSE（MIT或Apache 2.0）

**打包**:
```bash
# 编译发布版本
cargo build --release

# 生成二进制
target/release/skillstack

# 安装到系统
cargo install --path .
```

**发布渠道**:
- GitHub Release（v0.1.0-mvp）
- 提供 macOS 二进制下载
- 可选：发布到 Homebrew（后续）

### 10.2 MVP成功指标

1. **功能完整性**: 10个P0+P1命令全部可用
2. **稳定性**: 无critical bugs，基本错误处理覆盖
3. **用户体验**: 能完成"导入 → 创建 → 同步"的核心流程
4. **性能**: 扫描和同步操作 < 1秒（macOS）

### 10.3 阶段2规划（项目级管理）

在MVP成功后（约1个月用户反馈期），开始阶段2：

**新增功能**:
- 项目注册表（支持多项目）
- 项目级CRUD（per-project skills）
- Override机制（项目skill覆盖全局）
- 批量同步（sync到所有项目）

**数据结构变化**:
```json
// manifest.json 新增
{
  "projects": {
    "my-app": {
      "path": "/Users/xxx/projects/my-app",
      "skills": ["skill-a", "skill-b"],
      "overrides": {
        "skill-a": {
          "version_override": true,
          "hash": "xyz789..."
        }
      }
    }
  }
}
```

**新增命令**:
```bash
skillstack project add <path>
skillstack project list
skillstack project sync <name>
skillstack sync --all-projects
```

### 10.4 阶段3规划（版本管理 + GUI）

**版本管理**:
- 语义化版本号
- 版本历史和回滚
- 升级提示

**GUI（Tauri）**:
- 可视化skill列表
- 拖拽导入
- Diff对比
- 项目看板

---

## 11. 设计决策记录

### 11.1 为什么选择目录级symlink而不是每个skill单独symlink？

**决策**: 使用单个symlink（`~/.claude/skills/` → `~/.skillstack/repository/`）

**理由**:
- ✅ 实现最简单
- ✅ 性能最好（只需维护一个symlink）
- ✅ macOS原生支持良好
- ❌ 劣势：用户无法在Claude目录临时测试skill（可接受，有workaround）

### 11.2 为什么MVP不包含版本管理？

**决策**: MVP阶段不实现版本管理

**理由**:
- ✅ 降低MVP复杂度，加快验证速度
- ✅ 用户可通过Git手动管理版本（中央仓库可以是Git repo）
- ✅ 为阶段3留出充足设计空间
- ⚠️  需要在frontmatter预留version字段（当前决策：不预留）

### 11.3 为什么使用JSON而不是YAML作为manifest格式？

**决策**: manifest使用JSON，skill frontmatter使用YAML

**理由**:
- ✅ JSON解析性能更好
- ✅ JSON在Rust中的serde支持更成熟
- ✅ Manifest是机器生成，不需要人工编辑
- ✅ YAML更适合用户手写的frontmatter

### 11.4 为什么CLI优先而不是GUI优先？

**决策**: MVP只做CLI，GUI放到阶段3

**理由**:
- ✅ CLI开发速度快，2周可完成MVP
- ✅ 目标用户（开发者）习惯使用CLI
- ✅ 可以先验证核心价值，再投入GUI开发
- ✅ CLI可作为GUI的底层实现

---

## 12. 风险与应对

### 12.1 技术风险

**风险1: Symlink在某些macOS环境不工作**
- 概率: 低
- 影响: 高
- 应对: 实现fallback到copy模式，通过config.json配置

**风险2: Manifest损坏导致数据丢失**
- 概率: 低
- 影响: 中
- 应对: 
  - 定期备份manifest（保留.bak文件）
  - doctor命令提供恢复功能（从repository重建manifest）

**风险3: 与Claude Code更新不兼容**
- 概率: 中
- 影响: 高
- 应对: 
  - 监控Claude Code的skills目录格式变化
  - 设计适配器层，易于调整

### 12.2 用户体验风险

**风险4: 用户不理解中央仓库概念**
- 概率: 中
- 影响: 中
- 应对: 
  - 提供清晰的README和教程
  - init命令输出详细说明
  - doctor命令帮助理解状态

**风险5: 迁移成本高，用户不愿采用**
- 概率: 中
- 影响: 高
- 应对: 
  - 自动导入现有skills，一键完成
  - 提供回滚方案（保留.backup目录）
  - 强调"零学习成本"

### 12.3 时间风险

**风险6: 2周无法完成所有P0+P1命令**
- 概率: 中
- 影响: 低
- 应对: 
  - P0命令优先级最高，确保核心流程
  - P1命令可推迟到MVP后
  - 明确最小可发布范围（只有P0也可发布）

---

## 13. 成功标准

MVP被认为成功，当且仅当：

1. ✅ **功能完整**: 至少P0的7个命令全部可用
2. ✅ **稳定性**: 能在真实Claude Code环境正常工作
3. ✅ **易用性**: 新用户5分钟内完成初始化和第一个skill创建
4. ✅ **性能**: 常用操作（list/sync）响应时间 < 1秒
5. ✅ **可靠性**: 无数据丢失风险，有备份和恢复机制

---

## 附录

### A. SKILL.md模板

```yaml
---
name: your-skill-name
description: 简短描述这个skill做什么
---

# Your Skill Title

## 功能说明

这个skill用于...

## 使用方法

1. ...
2. ...

## 示例

```bash
# 示例代码
```
```

### B. config.json默认值

```json
{
  "claude_skills_path": "~/.claude/skills",
  "editor": "vim",
  "auto_sync": true
}
```

### C. 术语表

- **中央仓库**: `~/.skillstack/repository/`，所有Skill的单一真相来源
- **Manifest**: 状态追踪文件，记录所有skills的元数据
- **Symlink**: 符号链接，使Claude透明访问中央仓库
- **Skill**: 包含SKILL.md的目录单元
- **Frontmatter**: SKILL.md顶部的YAML元数据块
- **Hash**: SHA256文件哈希，用于检测文件变化
- **Drift**: 漂移，指文件被外部修改导致与manifest不一致

---

**文档结束**

最后更新: 2026-04-03  
作者: SkillStack Team  
状态: 已批准，待实现
