# 🔍 自动扫描项目功能

**版本**: v0.2.0-dev  
**日期**: 2026-04-07  
**状态**: ✅ 已实现

---

## 📋 功能概述

SkillStack 现在支持**自动扫描**目录并批量注册项目，无需手动逐个添加！

### 核心优势

- ✅ **批量注册** - 一次扫描注册多个项目
- ✅ **智能识别** - 自动识别包含 `.{tool}/skills/` 的目录
- ✅ **多工具支持** - 支持 Claude、Cursor 等不同工具
- ✅ **防重复** - 自动跳过已注册的项目
- ✅ **递归扫描** - 最多扫描3层子目录

---

## 🚀 使用方法

### 基本用法

```bash
# 扫描工作区目录，注册所有 Claude 项目
skillstack project scan /path/to/workspace

# 扫描 Cursor 项目
skillstack project scan /path/to/workspace --tool cursor
```

### 命令语法

```bash
skillstack project scan <directory> [OPTIONS]

Arguments:
  <directory>    要扫描的目录路径

Options:
  --tool <tool>  工具类型 [default: claude]
                 可选值: claude, cursor, ...
```

---

## 📊 工作原理

### 扫描逻辑

1. **递归遍历** - 扫描指定目录及其子目录（最多3层）
2. **识别项目** - 检查是否存在 `.{tool}/skills/` 子目录
3. **自动命名** - 使用目录名作为项目名称
4. **批量注册** - 自动调用注册逻辑
5. **跳过重复** - 已注册的项目会被自动跳过

### 识别规则

对于工具 `claude`，识别条件：
```
project-directory/
  └── .claude/
      └── skills/   ← 必须存在此目录
```

对于工具 `cursor`，识别条件：
```
project-directory/
  └── .cursor/
      └── skills/   ← 必须存在此目录
```

---

## 🎯 使用场景

### 场景 1: 初次使用（批量导入现有项目）

```bash
# 工作区结构
~/workspace/
  ├── project-web/
  │   └── .claude/skills/
  ├── project-api/
  │   └── .claude/skills/
  ├── project-mobile/
  │   └── .claude/skills/
  └── docs/  (无 skills 目录，会跳过)

# 一键扫描注册
$ skillstack project scan ~/workspace

🔍 Scanning '/Users/xxx/workspace' for claude projects...

✅ Registered 3 project(s):
  📂 project-web
  📂 project-api
  📂 project-mobile

💡 Next steps:
  - skillstack project list
  - skillstack install <skill> --project <name>
```

### 场景 2: 多工具混合环境

```bash
# 工作区包含不同工具的项目
~/workspace/
  ├── claude-project-1/.claude/skills/
  ├── claude-project-2/.claude/skills/
  └── cursor-project-1/.cursor/skills/

# 分别扫描
$ skillstack project scan ~/workspace --tool claude
✅ Registered 2 project(s): claude-project-1, claude-project-2

$ skillstack project scan ~/workspace --tool cursor
✅ Registered 1 project(s): cursor-project-1
```

### 场景 3: 新增项目后重新扫描

```bash
# 初次扫描
$ skillstack project scan ~/workspace
✅ Registered 3 project(s)

# 几天后，新增了一个项目
$ mkdir -p ~/workspace/new-project/.claude/skills

# 重新扫描（自动跳过已注册的）
$ skillstack project scan ~/workspace
✅ Registered 1 project(s):
  📂 new-project
```

---

## 💡 实用技巧

### 1. 验证注册结果

```bash
# 扫描后查看所有项目
skillstack project list

# 输出示例
NAME            PATH                        SKILLS
-------------------------------------------------
project-web     ~/workspace/project-web     0
project-api     ~/workspace/project-api     0
project-mobile  ~/workspace/project-mobile  0
```

### 2. 批量安装 Skills

```bash
# 扫描注册后，批量安装 skill
skillstack install debugging --project project-web
skillstack install debugging --project project-api
skillstack install debugging --project project-mobile

# 或者使用脚本
for proj in project-web project-api project-mobile; do
  skillstack install debugging --project $proj
done
```

### 3. 与现有命令结合

```bash
# 1. 扫描注册项目
skillstack project scan ~/workspace

# 2. 创建全局 skill
skillstack add my-skill

# 3. 批量同步到所有项目
skillstack project sync --all-projects

# 4. 检测 override
skillstack project detect-overrides --all-projects
```

---

## 🔍 扫描规则详解

### 目录深度限制

最多扫描 **3 层**子目录，避免扫描过深导致性能问题。

```
workspace/           ← 第 0 层（扫描起点）
├── level1/          ← 第 1 层 ✅
│   └── level2/      ← 第 2 层 ✅
│       └── level3/  ← 第 3 层 ✅
│           └── level4/  ← 第 4 层 ❌ 不扫描
```

### 跳过规则

以下目录会被**跳过**：
- ❌ 没有 `.{tool}/skills/` 子目录的
- ❌ 已经注册过的项目
- ❌ 扫描起点目录本身
- ❌ 无法访问的目录（权限不足）

### 项目命名

自动使用**目录名**作为项目名称：

```
/path/to/my-awesome-project/.claude/skills/
                ↓
        项目名: my-awesome-project
```

---

## 📈 性能数据

| 项目数量 | 扫描时间 | 状态 |
|---------|---------|------|
| 1-5个   | < 1s    | ✅   |
| 5-20个  | < 2s    | ✅   |
| 20-50个 | < 5s    | ✅   |

测试环境：macOS, SSD

---

## 🧪 测试验证

### 单元测试

```bash
# 运行项目扫描测试
cargo test project::tests::test_scan_and_register
cargo test project::tests::test_scan_skip_already_registered
```

**测试覆盖**:
- ✅ 正确识别项目
- ✅ 跳过无 skills 目录
- ✅ 跳过已注册项目
- ✅ 项目名称正确推断

### 手动测试场景

```bash
# 1. 创建测试工作区
mkdir -p /tmp/test-workspace/{proj1,proj2,proj3}/.claude/skills

# 2. 扫描
skillstack project scan /tmp/test-workspace
# 预期: 注册 3 个项目

# 3. 验证
skillstack project list
# 预期: 显示 proj1, proj2, proj3

# 4. 重复扫描
skillstack project scan /tmp/test-workspace
# 预期: No new projects found

# 5. 清理
rm -rf /tmp/test-workspace
```

---

## 🔧 技术实现

### 核心函数

```rust
// src/core/project.rs
pub fn scan_and_register(
    &mut self,
    scan_dir: &str,
    tool: &str
) -> Result<Vec<String>>
```

**实现要点**:
1. 使用 `walkdir` 递归遍历（max_depth=3）
2. 检查 `.{tool}/skills/` 目录是否存在
3. 调用 `register_project()` 批量注册
4. 捕获并跳过重复注册错误
5. 返回成功注册的项目列表

### CLI 命令

```rust
// src/cli/commands.rs
fn cmd_project_scan(directory: &str, tool: &str) -> Result<()>
```

**输出格式**:
- 扫描提示
- 注册结果列表
- 操作建议

---

## 📝 与手动注册对比

### 手动注册（传统方式）

```bash
skillstack project add /path/to/proj1 --name proj1
skillstack project add /path/to/proj2 --name proj2
skillstack project add /path/to/proj3 --name proj3
# ... 重复 N 次
```

**缺点**:
- ❌ 需要逐个添加
- ❌ 容易遗漏项目
- ❌ 路径需要手动输入

### 自动扫描（新方式）⭐

```bash
skillstack project scan /path/to/workspace
```

**优点**:
- ✅ 一次扫描全部注册
- ✅ 自动发现所有项目
- ✅ 防止重复注册
- ✅ 节省时间和精力

---

## 🎉 总结

**自动扫描功能**让项目管理变得更加高效：

1. **批量注册** - 一键完成，不再逐个添加
2. **智能识别** - 自动发现项目，无需手动查找
3. **防重复** - 跳过已注册，安全可靠
4. **多工具** - 支持 Claude、Cursor 等

**推荐工作流**:

```bash
# Step 1: 扫描注册所有项目
skillstack project scan ~/workspace

# Step 2: 创建全局 skills
skillstack add debugging
skillstack add testing

# Step 3: 批量同步
skillstack project sync --all-projects

# Step 4: 查看结果
skillstack project list
```

**一键搞定项目管理！** 🚀

---

**文档结束**

最后更新: 2026-04-07  
作者: SkillStack Team
