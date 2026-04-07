# SkillStack 功能测试指南

**版本**: v0.2.0-dev  
**日期**: 2026-04-07  

本指南将演示 SkillStack 的所有核心功能。

---

## 测试环境准备

```bash
# 1. 清理环境
rm -rf ~/.skillstack ~/.claude/skills

# 2. 构建项目
cargo build --release

# 3. 创建测试项目目录
mkdir -p /tmp/demo-project-web/.claude/skills
mkdir -p /tmp/demo-project-api/.claude/skills
mkdir -p /tmp/demo-project-mobile/.claude/skills
```

---

## 测试流程

按照以下步骤逐一测试所有功能...
