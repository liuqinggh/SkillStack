# SkillStack 安装指南

**版本**: v0.2.0-dev  
**日期**: 2026-04-07

---

## ✅ 安装完成

SkillStack 已成功安装到系统！

**安装位置**: `~/.cargo/bin/skillstack`  
**文件大小**: 3.3 MB

---

## 🚀 快速开始

### 方法 1: 使用完整路径（立即可用）

```bash
~/.cargo/bin/skillstack --help
~/.cargo/bin/skillstack init
~/.cargo/bin/skillstack list
```

### 方法 2: 添加到 PATH（推荐）

#### 对于 Zsh（当前 shell）

```bash
# 添加到 ~/.zshrc
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.zshrc

# 重新加载配置
source ~/.zshrc

# 测试（无需完整路径）
skillstack --help
```

#### 对于 Bash

```bash
# 添加到 ~/.bashrc 或 ~/.bash_profile
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

## 📋 验证安装

```bash
# 检查二进制文件
ls -lh ~/.cargo/bin/skillstack

# 测试命令
~/.cargo/bin/skillstack status

# 查看帮助
~/.cargo/bin/skillstack --help
```

---

## 🎯 初始化 SkillStack

如果这是首次使用，需要先初始化：

```bash
# 方法 1: 使用完整路径
~/.cargo/bin/skillstack init

# 方法 2: 添加 PATH 后
skillstack init
```

初始化后，SkillStack 会：
- 创建 `~/.skillstack/repository/` 目录
- 创建 `~/.skillstack/manifest.json` 和 `config.json`
- 创建 symlink `~/.claude/skills -> ~/.skillstack/repository`

---

## 📚 基本用法

```bash
# 创建 skill
skillstack add my-skill

# 列出所有 skills
skillstack list

# 注册项目
skillstack project add /path/to/project --name my-project

# 安装 skill 到项目
skillstack install my-skill --project my-project

# 查看项目 skills
skillstack list --project my-project

# 批量同步
skillstack project sync --all-projects
```

---

## 🔧 配置文件位置

- **全局配置**: `~/.skillstack/config.json`
- **状态追踪**: `~/.skillstack/manifest.json`
- **全局 Skills**: `~/.skillstack/repository/`
- **Claude Skills**: `~/.claude/skills` (symlink)

---

## 📖 完整文档

- **设计文档**: `docs/设计方案.md`
- **第一阶段报告**: `docs/MVP-COMPLETION-REPORT.md`
- **第二阶段进度**: `docs/PHASE2-PROGRESS.md`
- **测试报告**: `docs/TEST-REPORT.md`
- **快速开始**: `docs/QUICK-START.md`

---

## 🆘 常见问题

### Q: 为什么 `skillstack` 命令找不到？

A: 需要将 `~/.cargo/bin` 添加到 PATH：

```bash
# Zsh
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Bash  
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Q: 如何卸载？

```bash
# 删除二进制文件
rm ~/.cargo/bin/skillstack

# 删除数据（可选）
rm -rf ~/.skillstack
```

### Q: 如何更新？

```bash
# 拉取最新代码
cd /path/to/SkillStack
git pull

# 重新安装
cargo install --path . --force
```

---

## 🎉 安装完成后的下一步

1. **初始化系统**
   ```bash
   skillstack init
   ```

2. **创建第一个 skill**
   ```bash
   skillstack add my-first-skill
   ```

3. **注册项目**
   ```bash
   skillstack project add /path/to/your/project
   ```

4. **探索功能**
   ```bash
   skillstack --help
   skillstack project --help
   ```

---

## 📞 获取帮助

- 查看帮助: `skillstack --help`
- 查看子命令帮助: `skillstack <command> --help`
- 健康检查: `skillstack doctor`
- 系统状态: `skillstack status`

---

**安装成功！开始使用 SkillStack 管理你的 Skills 吧！** 🚀
