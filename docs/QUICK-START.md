# SkillStack 快速上手指南

**5 分钟学会使用 SkillStack 管理 Claude Code Skills**

---

## 🚀 安装

```bash
# 在项目目录下
cd /path/to/SkillStack
cargo install --path .

# 或者直接使用 cargo bin（如果 PATH 已配置）
# 如果 ~/.cargo/bin 不在 PATH，添加以下行到 ~/.zshrc 或 ~/.bashrc：
# export PATH="$HOME/.cargo/bin:$PATH"
```

---

## 📦 初始化

**首次使用**（会自动导入现有 skills）：
```bash
skillstack init
```

输出示例：
```
🔍 Found 3 existing skills:
  📋 my-old-skill
  📋 another-skill
  📋 legacy-skill
Import to central repository? (yes/no): yes
✅ Imported 'my-old-skill'
✅ Imported 'another-skill'
✅ Imported 'legacy-skill'
✅ Symlink created: ~/.claude/skills -> ~/.skillstack/repository

✅ SkillStack initialized!
```

**强制重新初始化**（谨慎使用）：
```bash
skillstack init --force
```

**跳过导入**：
```bash
skillstack init --no-import
```

---

## 📋 查看 Skills

**列出所有 skills**：
```bash
skillstack list
```

输出示例：
```
NAME                            DESCRIPTION                                         UPDATED             
----------------------------------------------------------------------------------------------------
chatbot-test                    对 Dify Chatflow 进行多轮对话自动化测试             just now            
auth-jwt                        获取 Igloo UCP JWT 的完整流程                        2h ago              
url-to-reading-notes            将 URL 转化为读书笔记                                1d ago              

Total: 3 skills
```

**按时间排序**：
```bash
skillstack list --sort updated        # 按更新时间
skillstack list --sort created        # 按创建时间
skillstack list --sort name           # 按名称（默认）
```

**反向排序**：
```bash
skillstack list --sort updated --reverse
```

---

## ➕ 创建 Skill

**创建并编辑**（会自动打开编辑器）：
```bash
skillstack add my-awesome-skill
```

流程：
1. 创建 `~/.skillstack/repository/my-awesome-skill/SKILL.md`
2. 自动生成模板（含 frontmatter）
3. 打开你配置的编辑器（默认 vim）
4. 保存后自动计算 hash 并更新 manifest
5. **Claude Code 立即可见！**

**仅创建不编辑**：
```bash
skillstack add my-skill --no-edit
```

**指定编辑器**：
```bash
skillstack add my-skill --editor code    # 使用 VS Code
skillstack add my-skill --editor vim     # 使用 Vim
```

**Skill 名称规则**：
- 必须以小写字母开头
- 只能包含小写字母、数字、连字符
- 示例：`my-skill`、`skill-v2`、`test-skill-123`
- ❌ 不允许：`My-Skill`、`my skill`、`123-skill`

---

## ✏️ 编辑 Skill

```bash
skillstack edit my-awesome-skill
```

- 打开编辑器
- 保存后自动更新 hash 和时间戳
- **Claude Code 立即看到更新！**

**指定编辑器**：
```bash
skillstack edit my-skill --editor code
```

---

## 🔍 查看 Skill 详情

```bash
skillstack show my-awesome-skill
```

输出示例：
```
Name: my-awesome-skill
Description: 这个 skill 用于...
Created: 2026-04-07T07:41:37.073974+00:00
Updated: 2026-04-07T08:15:22.123456+00:00
Path: ~/.skillstack/repository/my-awesome-skill
Hash: sha256:aab931e0dc4ce68a51851bfea87d42cd8538155275c5106b3e2d00d7bc31b0a9
```

---

## 🗑️ 删除 Skill

**删除（需确认）**：
```bash
skillstack delete my-skill
```

输出：
```
⚠️  About to delete 'my-skill'
This cannot be undone.
Continue? (yes/no): yes
✅ Skill 'my-skill' deleted
```

**强制删除（跳过确认）**：
```bash
skillstack delete my-skill --force
```

**注意**：删除后 Claude Code 立即移除该 skill！

---

## 📥 导入外部 Skill

**从外部目录导入**：
```bash
skillstack import /path/to/existing-skill
```

**指定名称**：
```bash
skillstack import /path/to/skill --name my-imported-skill
```

**要求**：
- 目录下必须有 `SKILL.md`
- SKILL.md 必须包含正确的 frontmatter（name、description）

示例 frontmatter：
```markdown
---
name: my-skill
description: 这个 skill 用于...
---

# My Skill

## 功能说明
...
```

---

## 🔄 同步 Skills

**通常不需要手动同步**（symlink 自动实时同步）

**强制重建 symlink**：
```bash
skillstack sync --force
```

使用场景：
- symlink 损坏时
- 切换到新的 Claude 路径时

---

## 📊 查看状态

```bash
skillstack status
```

输出示例：
```
Repository: ~/.skillstack/repository (5 skills)
Claude Path: ~/.claude/skills (symlink ✅)
Last Sync: 2h ago
Status: All synced ✅
```

---

## 🏥 健康检查

**检查系统健康**：
```bash
skillstack doctor
```

输出示例：
```
🏥 Running health check...

✅ Directory structure: OK
✅ Symlink: OK
✅ Manifest: OK

✅ All checks passed!
```

**自动修复问题**：
```bash
skillstack doctor --fix
```

检查项目：
- 目录结构是否完整
- symlink 是否有效
- manifest 与实际文件是否一致
- 损坏的 skill 文件

---

## 💡 常见场景

### 场景 1：我想创建一个新 skill

```bash
# 1. 创建 skill
skillstack add my-new-skill

# 2. 编辑器会自动打开，编写你的 skill 内容

# 3. 保存并退出编辑器

# 4. 完成！Claude 已经能看到你的新 skill 了
```

### 场景 2：我想修改现有 skill

```bash
# 1. 编辑 skill
skillstack edit my-skill

# 2. 修改内容并保存

# 3. Claude 立即看到更新
```

或者直接编辑文件（也行，但记得更新 hash）：
```bash
# 直接编辑
vim ~/.skillstack/repository/my-skill/SKILL.md

# 不需要手动同步！Claude 会立即看到变化
```

### 场景 3：我有一些旧的 skills 想导入

```bash
# 初始化时自动导入
skillstack init  # 会提示是否导入现有 skills

# 或者后续单独导入
skillstack import /path/to/old-skill
```

### 场景 4：我想查看所有 skills

```bash
# 简洁列表
skillstack list

# 按更新时间排序
skillstack list --sort updated

# 查看某个 skill 的详细信息
skillstack show my-skill
```

### 场景 5：我的 symlink 坏了

```bash
# 运行健康检查
skillstack doctor

# 如果发现问题，自动修复
skillstack doctor --fix

# 或者强制重建 symlink
skillstack sync --force
```

---

## 🎯 核心优势

### 对比传统手动管理

| 操作 | 传统方式 | SkillStack |
|------|----------|------------|
| 创建 skill | 手动创建目录和文件 | `skillstack add <name>` |
| 编辑 skill | 手动找到文件路径 | `skillstack edit <name>` |
| 查看所有 skills | `ls ~/.claude/skills` | `skillstack list` |
| 跨项目同步 | 手动复制粘贴 | 自动（symlink） |
| 版本管理 | 手动记录或依赖 git | 自动 hash + 时间戳 |
| 健康检查 | 无 | `skillstack doctor` |

### 核心价值

1. **单源真相**：所有 skills 集中在 `~/.skillstack/repository`，告别"到处都是、不知道哪个是最新的"
2. **实时同步**：通过 symlink，修改后 Claude 立即看到，无需手动复制
3. **完整管理**：CRUD、导入、查看、健康检查，一个工具搞定
4. **安全可靠**：自动备份、hash 验证、健康检查

---

## ⚙️ 配置

配置文件：`~/.skillstack/config.json`

```json
{
  "claude_skills_path": "/Users/you/.claude/skills",
  "editor": "vim",
  "auto_sync": true
}
```

**修改编辑器**：
```bash
# 方法1：直接编辑 config.json
vim ~/.skillstack/config.json

# 方法2：在命令中指定（临时）
skillstack add my-skill --editor code
```

---

## 🆘 故障排查

### 问题：Claude 看不到我的 skills

```bash
# 1. 检查 symlink
ls -la ~/.claude/skills
# 应该显示：skills -> /Users/you/.skillstack/repository

# 2. 运行健康检查
skillstack doctor

# 3. 如果 symlink 损坏，重建
skillstack sync --force
```

### 问题：命令找不到 (command not found)

```bash
# 检查 PATH
echo $PATH | grep cargo

# 如果没有，添加到 ~/.zshrc
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 问题：已经初始化过，想重新开始

```bash
# 谨慎！会删除所有 skills
rm -rf ~/.skillstack
skillstack init
```

或者保留 skills 重新初始化：
```bash
# 备份
cp -r ~/.skillstack ~/.skillstack.backup

# 强制重新初始化
skillstack init --force
```

---

## 📚 更多资源

- **完整设计方案**：`docs/设计方案.md`
- **实现计划**：`docs/superpowers/plans/2026-04-03-skillstack-mvp-implementation.md`
- **MVP 完成报告**：`docs/MVP-COMPLETION-REPORT.md`
- **README**：项目根目录 `README.md`

---

## 🎊 开始使用

```bash
# 1. 安装
cargo install --path .

# 2. 初始化
skillstack init

# 3. 创建第一个 skill
skillstack add hello-world

# 4. 查看列表
skillstack list

# 完成！🎉
```

Happy Skill Management! 🚀
