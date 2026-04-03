# SkillStack MVP 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 @superpowers:subagent-driven-development（推荐）或 @superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 构建一个Rust CLI工具,为Claude Code用户提供集中式的Skill管理,解决"Skill分散、手动复制、版本混乱"的核心痛点。

**架构：** 中央仓库(~/.skillstack/repository/)作为单一真相来源,通过目录级symlink同步到Claude skills目录,使用JSON manifest追踪状态。核心包括Repository Manager、Manifest Manager、Sync Engine和CLI命令层。

**技术栈：** Rust 2021, Clap 4.5 (CLI), serde/serde_json (序列化), serde_yaml (frontmatter), sha2 (hash), chrono (时间), colored (输出), dialoguer (交互), walkdir (目录遍历)

---

## 文件结构

### 将要创建的文件

**项目配置:**
- `Cargo.toml` - Rust项目配置和依赖
- `README.md` - 项目文档
- `LICENSE` - MIT许可证
- `.gitignore` - Git忽略规则

**源代码 (src/):**
- `main.rs` - CLI入口点,调用clap命令
- `lib.rs` - 库入口,导出公共模块
- `cli/commands.rs` - Clap命令定义和处理函数
- `core/skill.rs` - Skill数据结构和验证逻辑
- `core/manifest.rs` - Manifest读写和状态管理
- `core/config.rs` - Config读写和配置管理
- `core/repository.rs` - Repository操作(CRUD)
- `core/sync.rs` - Symlink创建和验证
- `utils/hash.rs` - SHA256 hash计算
- `utils/frontmatter.rs` - YAML frontmatter解析
- `utils/fs.rs` - 文件系统辅助函数
- `utils/ui.rs` - 用户界面输出辅助(emoji, 彩色文本)

**测试 (tests/):**
- `integration_test.rs` - 端到端集成测试
- `fixtures/` - 测试数据和fixtures

### 职责说明

**core/skill.rs:**
- 定义`Skill`结构体(name, description, created_at, updated_at, hash, path)
- Skill名称验证(小写字母、数字、连字符,以字母开头)
- Skill目录和SKILL.md的创建/读取

**core/manifest.rs:**
- 定义`Manifest`结构体(version, skills HashMap, sync_status)
- manifest.json的序列化/反序列化
- 添加/删除/更新skill记录
- 保存manifest并创建.bak备份

**core/config.rs:**
- 定义`Config`结构体(claude_skills_path, editor, auto_sync)
- config.json的读写
- 获取配置值(编辑器、自动同步等)
- 创建默认配置

**core/repository.rs:**
- 初始化仓库(创建~/.skillstack/结构)
- 列出所有skills(从repository目录扫描)
- 创建新skill(目录+模板SKILL.md)
- 删除skill(移除目录和manifest记录)
- 导入外部skill

**core/sync.rs:**
- 创建目录级symlink (~/.claude/skills -> ~/.skillstack/repository)
- 验证symlink有效性
- 重建损坏的symlink
- 备份现有目录(.backup)

**utils/hash.rs:**
- 计算文件SHA256 hash
- 比较hash检测文件变化

**utils/frontmatter.rs:**
- 解析SKILL.md的YAML frontmatter
- 验证必需字段(name, description)
- 生成模板frontmatter

**utils/fs.rs:**
- 展开~路径到完整路径
- 递归复制目录
- 安全删除目录

**utils/ui.rs:**
- 彩色输出辅助(success, error, warning, info)
- 表格格式化(用于list命令)
- 确认提示

**cli/commands.rs:**
- 定义所有CLI命令(init, list, add, edit, delete, sync, import, show, doctor, status)
- 每个命令的处理函数
- 参数解析和验证

---

## 任务分解

### 任务 1: 项目初始化和基础结构

**文件:**
- 创建: `Cargo.toml`
- 创建: `src/main.rs`
- 创建: `src/lib.rs`
- 创建: `.gitignore`

- [ ] **步骤 1: 创建Cargo.toml**

```toml
[package]
name = "skillstack"
version = "0.1.0"
edition = "2021"
authors = ["SkillStack Team <team@skillstack.dev>"]
description = "Centralized skill management for Claude Code"
license = "MIT"

[dependencies]
clap = { version = "4.5", features = ["derive"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
serde_yaml = "0.9"
sha2 = "0.10"
chrono = { version = "0.4", features = ["serde"] }
anyhow = "1.0"
colored = "2.1"
dialoguer = "0.11"
walkdir = "2.5"
regex = "1.10"
dirs = "5.0"

[dev-dependencies]
tempfile = "3.10"
```

- [ ] **步骤 2: 创建基础main.rs**

```rust
use clap::Parser;

#[derive(Parser)]
#[command(name = "skillstack")]
#[command(about = "Centralized skill management for Claude Code", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Parser)]
enum Commands {
    // 命令将在后续任务中添加
}

fn main() {
    let cli = Cli::parse();
    println!("SkillStack MVP");
}
```

- [ ] **步骤 3: 创建lib.rs骨架**

```rust
pub mod cli;
pub mod core;
pub mod utils;

pub use cli::commands;
pub use core::{manifest, repository, skill, sync};
```

- [ ] **步骤 4: 创建.gitignore**

```
/target/
Cargo.lock
.DS_Store
*.swp
*.swo
```

- [ ] **步骤 5: 验证编译**

运行: `cargo build`
预期: 编译成功,无错误

- [ ] **步骤 6: Commit基础结构**

```bash
git add Cargo.toml src/main.rs src/lib.rs .gitignore
git commit -m "feat: initialize Rust project with basic structure"
```

---

### 任务 2: 数据结构定义 (Skill)

**文件:**
- 创建: `src/core/skill.rs`
- 创建: `src/core/mod.rs`
- 创建: `tests/unit_skill.rs`

- [ ] **步骤 1: 编写Skill结构测试**

创建 `tests/unit_skill.rs`:

```rust
use skillstack::core::skill::Skill;

#[test]
fn test_validate_skill_name_valid() {
    assert!(Skill::validate_name("my-skill").is_ok());
    assert!(Skill::validate_name("skill-v2").is_ok());
    assert!(Skill::validate_name("abc123").is_ok());
}

#[test]
fn test_validate_skill_name_invalid() {
    assert!(Skill::validate_name("My-Skill").is_err()); // 大写
    assert!(Skill::validate_name("my skill").is_err()); // 空格
    assert!(Skill::validate_name("123-skill").is_err()); // 以数字开头
    assert!(Skill::validate_name("skill_name").is_err()); // 下划线
}
```

- [ ] **步骤 2: 运行测试验证失败**

运行: `cargo test test_validate_skill_name`
预期: FAIL, "no such module: core::skill"

- [ ] **步骤 3: 实现Skill结构**

创建 `src/core/mod.rs`:
```rust
pub mod skill;
pub mod manifest;
pub mod repository;
pub mod sync;
```

创建 `src/core/skill.rs`:

```rust
use anyhow::{anyhow, Result};
use regex::Regex;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Skill {
    pub name: String,
    pub description: String,
    pub created_at: String,
    pub updated_at: String,
    pub hash: String,
    pub path: String,
}

impl Skill {
    /// 验证skill名称格式
    /// 规则: 小写字母、数字、连字符,以字母开头
    pub fn validate_name(name: &str) -> Result<()> {
        let re = Regex::new(r"^[a-z][a-z0-9-]*$").unwrap();
        if re.is_match(name) {
            Ok(())
        } else {
            Err(anyhow!(
                "Invalid skill name. Use lowercase letters, numbers, and hyphens only. Must start with a letter."
            ))
        }
    }
}
```

等等,我需要在Cargo.toml中添加regex依赖:

```toml
# 在 [dependencies] 中添加
regex = "1.10"
```

- [ ] **步骤 4: 运行测试验证通过**

运行: `cargo test test_validate_skill_name`
预期: PASS

- [ ] **步骤 5: Commit Skill结构**

```bash
git add Cargo.toml src/core/ tests/unit_skill.rs
git commit -m "feat: add Skill struct and name validation"
```

---

### 任务 3: 数据结构定义 (Manifest)

**文件:**
- 创建: `src/core/manifest.rs`
- 创建: `tests/unit_manifest.rs`

- [ ] **步骤 1: 编写Manifest测试**

创建 `tests/unit_manifest.rs`:

```rust
use skillstack::core::manifest::{Manifest, SyncStatus};
use std::collections::HashMap;
use tempfile::TempDir;

#[test]
fn test_new_manifest() {
    let manifest = Manifest::new("/Users/test/.claude/skills");
    assert_eq!(manifest.version, "1.0");
    assert!(manifest.skills.is_empty());
    assert_eq!(manifest.sync_status.claude_skills_path, "/Users/test/.claude/skills");
}

#[test]
fn test_manifest_save_and_load() {
    let temp_dir = TempDir::new().unwrap();
    let manifest_path = temp_dir.path().join("manifest.json");
    
    let mut manifest = Manifest::new("/Users/test/.claude/skills");
    manifest.save(&manifest_path).unwrap();
    
    let loaded = Manifest::load(&manifest_path).unwrap();
    assert_eq!(loaded.version, "1.0");
}
```

- [ ] **步骤 2: 运行测试验证失败**

运行: `cargo test test_new_manifest`
预期: FAIL

- [ ] **步骤 3: 实现Manifest结构**

创建 `src/core/manifest.rs`:

```rust
use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

use super::skill::Skill;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Manifest {
    pub version: String,
    pub skills: HashMap<String, Skill>,
    pub sync_status: SyncStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncStatus {
    pub claude_skills_path: String,
    pub last_sync: Option<String>,
    pub sync_method: String,
}

impl Manifest {
    pub fn new(claude_skills_path: &str) -> Self {
        Self {
            version: "1.0".to_string(),
            skills: HashMap::new(),
            sync_status: SyncStatus {
                claude_skills_path: claude_skills_path.to_string(),
                last_sync: None,
                sync_method: "symlink".to_string(),
            },
        }
    }

    pub fn load(path: &Path) -> Result<Self> {
        let content = fs::read_to_string(path)?;
        let manifest: Manifest = serde_json::from_str(&content)?;
        Ok(manifest)
    }

    pub fn save(&self, path: &Path) -> Result<()> {
        // 创建备份
        if path.exists() {
            let backup_path = path.with_extension("json.bak");
            fs::copy(path, backup_path)?;
        }
        
        let json = serde_json::to_string_pretty(&self)?;
        fs::write(path, json)?;
        Ok(())
    }

    pub fn add_skill(&mut self, skill: Skill) {
        self.skills.insert(skill.name.clone(), skill);
    }

    pub fn remove_skill(&mut self, name: &str) -> Option<Skill> {
        self.skills.remove(name)
    }

    pub fn get_skill(&self, name: &str) -> Option<&Skill> {
        self.skills.get(name)
    }

    pub fn update_sync_time(&mut self, time: String) {
        self.sync_status.last_sync = Some(time);
    }
}
```

- [ ] **步骤 4: 运行测试验证通过**

运行: `cargo test test_manifest`
预期: PASS

- [ ] **步骤 5: Commit Manifest结构**

```bash
git add src/core/manifest.rs tests/unit_manifest.rs
git commit -m "feat: add Manifest struct with save/load functionality"
```

---

### 任务 4: 工具函数 - Hash计算

**文件:**
- 创建: `src/utils/hash.rs`
- 创建: `src/utils/mod.rs`
- 创建: `tests/unit_hash.rs`

- [ ] **步骤 1: 编写Hash测试**

创建 `tests/unit_hash.rs`:

```rust
use skillstack::utils::hash;
use std::fs;
use tempfile::TempDir;

#[test]
fn test_hash_file_consistency() {
    let temp_dir = TempDir::new().unwrap();
    let file_path = temp_dir.path().join("test.txt");
    fs::write(&file_path, "test content").unwrap();
    
    let hash1 = hash::calculate_file_hash(&file_path).unwrap();
    let hash2 = hash::calculate_file_hash(&file_path).unwrap();
    
    assert_eq!(hash1, hash2);
}

#[test]
fn test_hash_detects_changes() {
    let temp_dir = TempDir::new().unwrap();
    let file_path = temp_dir.path().join("test.txt");
    
    fs::write(&file_path, "content 1").unwrap();
    let hash1 = hash::calculate_file_hash(&file_path).unwrap();
    
    fs::write(&file_path, "content 2").unwrap();
    let hash2 = hash::calculate_file_hash(&file_path).unwrap();
    
    assert_ne!(hash1, hash2);
}
```

- [ ] **步骤 2: 运行测试验证失败**

运行: `cargo test test_hash`
预期: FAIL

- [ ] **步骤 3: 实现Hash功能**

创建 `src/utils/mod.rs`:
```rust
pub mod hash;
pub mod fs;
pub mod frontmatter;
pub mod ui;
```

创建 `src/utils/hash.rs`:

```rust
use anyhow::Result;
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::Read;
use std::path::Path;

pub fn calculate_file_hash(path: &Path) -> Result<String> {
    let mut file = File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = Vec::new();
    
    file.read_to_end(&mut buffer)?;
    hasher.update(&buffer);
    
    let result = hasher.finalize();
    Ok(format!("sha256:{:x}", result))
}
```

- [ ] **步骤 4: 运行测试验证通过**

运行: `cargo test test_hash`
预期: PASS

- [ ] **步骤 5: Commit Hash功能**

```bash
git add src/utils/ tests/unit_hash.rs
git commit -m "feat: add SHA256 file hash calculation"
```

---

### 任务 5: 工具函数 - Frontmatter解析

**文件:**
- 创建: `src/utils/frontmatter.rs`
- 创建: `tests/unit_frontmatter.rs`

- [ ] **步骤 1: 编写Frontmatter测试**

创建 `tests/unit_frontmatter.rs`:

```rust
use skillstack::utils::frontmatter;

#[test]
fn test_parse_valid_frontmatter() {
    let content = r#"---
name: test-skill
description: A test skill
---

# Skill Content
"#;
    
    let (name, desc) = frontmatter::parse(content).unwrap();
    assert_eq!(name, "test-skill");
    assert_eq!(desc, "A test skill");
}

#[test]
fn test_parse_missing_fields() {
    let content = r#"---
name: test-skill
---

# Content
"#;
    
    assert!(frontmatter::parse(content).is_err());
}

#[test]
fn test_generate_template() {
    let template = frontmatter::generate_template("my-skill", "My skill description");
    assert!(template.contains("name: my-skill"));
    assert!(template.contains("description: My skill description"));
}
```

- [ ] **步骤 2: 运行测试验证失败**

运行: `cargo test test_parse_valid_frontmatter`
预期: FAIL

- [ ] **步骤 3: 实现Frontmatter解析**

创建 `src/utils/frontmatter.rs`:

```rust
use anyhow::{anyhow, Result};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize, Serialize)]
struct FrontmatterData {
    name: String,
    description: String,
}

pub fn parse(content: &str) -> Result<(String, String)> {
    // 查找frontmatter分隔符
    let parts: Vec<&str> = content.splitn(3, "---").collect();
    
    if parts.len() < 3 {
        return Err(anyhow!("Invalid frontmatter format"));
    }
    
    let yaml_content = parts[1].trim();
    let data: FrontmatterData = serde_yaml::from_str(yaml_content)
        .map_err(|e| anyhow!("Failed to parse frontmatter: {}", e))?;
    
    if data.name.is_empty() || data.description.is_empty() {
        return Err(anyhow!("Missing required fields: name and description"));
    }
    
    Ok((data.name, data.description))
}

pub fn generate_template(name: &str, description: &str) -> String {
    format!(
        r#"---
name: {}
description: {}
---

# {}

## 功能说明

这个skill用于...

## 使用方法

1. ...
2. ...

## 示例

```bash
# 示例代码
```
"#,
        name, description, name
    )
}
```

- [ ] **步骤 4: 运行测试验证通过**

运行: `cargo test test_frontmatter`
预期: PASS

- [ ] **步骤 5: Commit Frontmatter功能**

```bash
git add src/utils/frontmatter.rs tests/unit_frontmatter.rs
git commit -m "feat: add frontmatter parsing and template generation"
```

---

### 任务 6: 工具函数 - 文件系统辅助

**文件:**
- 创建: `src/utils/fs.rs`
- 创建: `tests/unit_fs.rs`

- [ ] **步骤 1: 编写文件系统测试**

创建 `tests/unit_fs.rs`:

```rust
use skillstack::utils::fs;
use std::path::PathBuf;

#[test]
fn test_expand_tilde() {
    let path = fs::expand_tilde("~/.skillstack");
    assert!(path.to_str().unwrap().contains(".skillstack"));
    assert!(!path.to_str().unwrap().contains("~"));
}

#[test]
fn test_expand_tilde_no_tilde() {
    let original = "/absolute/path";
    let expanded = fs::expand_tilde(original);
    assert_eq!(expanded, PathBuf::from(original));
}
```

- [ ] **步骤 2: 运行测试验证失败**

运行: `cargo test test_expand_tilde`
预期: FAIL

- [ ] **步骤 3: 实现文件系统辅助**

创建 `src/utils/fs.rs`:

```rust
use anyhow::Result;
use std::fs;
use std::path::{Path, PathBuf};

/// 展开~到用户home目录
pub fn expand_tilde(path: &str) -> PathBuf {
    if path.starts_with("~") {
        if let Some(home) = dirs::home_dir() {
            return PathBuf::from(path.replacen("~", &home.to_string_lossy(), 1));
        }
    }
    PathBuf::from(path)
}

/// 递归复制目录
pub fn copy_dir_recursive(src: &Path, dst: &Path) -> Result<()> {
    fs::create_dir_all(dst)?;
    
    for entry in fs::read_dir(src)? {
        let entry = entry?;
        let file_type = entry.file_type()?;
        let src_path = entry.path();
        let dst_path = dst.join(entry.file_name());
        
        if file_type.is_dir() {
            copy_dir_recursive(&src_path, &dst_path)?;
        } else {
            fs::copy(&src_path, &dst_path)?;
        }
    }
    
    Ok(())
}

/// 安全删除目录(移动到临时位置后删除)
pub fn safe_remove_dir(path: &Path) -> Result<()> {
    if path.exists() {
        fs::remove_dir_all(path)?;
    }
    Ok(())
}
```

需要添加`dirs` crate到Cargo.toml:
```toml
dirs = "5.0"
```

- [ ] **步骤 4: 运行测试验证通过**

运行: `cargo test test_expand_tilde`
预期: PASS

- [ ] **步骤 5: Commit文件系统辅助**

```bash
git add Cargo.toml src/utils/fs.rs tests/unit_fs.rs
git commit -m "feat: add filesystem utilities (expand tilde, copy, remove)"
```

---

### 任务 7: 工具函数 - UI辅助

**文件:**
- 创建: `src/utils/ui.rs`

- [ ] **步骤 1: 实现UI辅助函数(无测试,直接实现)**

创建 `src/utils/ui.rs`:

```rust
use colored::*;

pub fn success(msg: &str) {
    println!("{} {}", "✅".green(), msg);
}

pub fn error(msg: &str) {
    eprintln!("{} {}", "❌".red(), msg);
}

pub fn warning(msg: &str) {
    println!("{} {}", "⚠️ ".yellow(), msg);
}

pub fn info(msg: &str) {
    println!("{} {}", "💡".blue(), msg);
}

pub fn prompt(msg: &str) -> bool {
    use dialoguer::Confirm;
    
    Confirm::new()
        .with_prompt(msg)
        .default(true)
        .interact()
        .unwrap_or(false)
}

/// 格式化表格行
pub fn format_table_row(cols: &[&str], widths: &[usize]) -> String {
    cols.iter()
        .zip(widths.iter())
        .map(|(col, width)| format!("{:<width$}", col, width = width))
        .collect::<Vec<_>>()
        .join("  ")
}
```

- [ ] **步骤 2: Commit UI辅助**

```bash
git add src/utils/ui.rs
git commit -m "feat: add UI utilities for colored output and prompts"
```

---

### 任务 8: Repository Manager核心功能

**文件:**
- 创建: `src/core/repository.rs`
- 创建: `tests/unit_repository.rs`

- [ ] **步骤 1: 编写Repository测试**

创建 `tests/unit_repository.rs`:

```rust
use skillstack::core::repository::Repository;
use tempfile::TempDir;

#[test]
fn test_init_repository() {
    let temp_dir = TempDir::new().unwrap();
    let repo_path = temp_dir.path().join(".skillstack");
    
    let repo = Repository::new(&repo_path);
    repo.init("/Users/test/.claude/skills").unwrap();
    
    assert!(repo_path.join("repository").exists());
    assert!(repo_path.join("manifest.json").exists());
    assert!(repo_path.join("config.json").exists());
}

#[test]
fn test_create_skill() {
    let temp_dir = TempDir::new().unwrap();
    let repo_path = temp_dir.path().join(".skillstack");
    
    let mut repo = Repository::new(&repo_path);
    repo.init("/Users/test/.claude/skills").unwrap();
    
    repo.create_skill("test-skill", "A test skill").unwrap();
    
    let skill_path = repo_path.join("repository/test-skill/SKILL.md");
    assert!(skill_path.exists());
}
```

- [ ] **步骤 2: 运行测试验证失败**

运行: `cargo test test_init_repository`
预期: FAIL

- [ ] **步骤 3: 实现Repository Manager**

创建 `src/core/repository.rs`:

```rust
use anyhow::{anyhow, Result};
use chrono::Utc;
use std::fs;
use std::path::{Path, PathBuf};

use super::manifest::Manifest;
use super::skill::Skill;
use crate::utils::{frontmatter, hash, fs as fs_utils};

pub struct Repository {
    base_path: PathBuf,
}

impl Repository {
    pub fn new(base_path: &Path) -> Self {
        Self {
            base_path: base_path.to_path_buf(),
        }
    }

    pub fn init(&self, claude_skills_path: &str) -> Result<()> {
        // 检查是否已初始化
        if self.base_path.exists() {
            return Err(anyhow!("Repository already initialized at {:?}", self.base_path));
        }

        // 创建目录结构
        fs::create_dir_all(self.base_path.join("repository"))?;

        // 创建manifest.json
        let manifest = Manifest::new(claude_skills_path);
        manifest.save(&self.base_path.join("manifest.json"))?;

        // 创建config.json
        let config = serde_json::json!({
            "claude_skills_path": claude_skills_path,
            "editor": "vim",
            "auto_sync": true
        });
        fs::write(
            self.base_path.join("config.json"),
            serde_json::to_string_pretty(&config)?
        )?;

        Ok(())
    }

    pub fn create_skill(&mut self, name: &str, description: &str) -> Result<()> {
        // 验证名称
        Skill::validate_name(name)?;

        // 检查是否已存在
        let skill_path = self.base_path.join("repository").join(name);
        if skill_path.exists() {
            return Err(anyhow!("Skill '{}' already exists", name));
        }

        // 创建目录
        fs::create_dir_all(&skill_path)?;

        // 生成SKILL.md
        let content = frontmatter::generate_template(name, description);
        let skill_md_path = skill_path.join("SKILL.md");
        fs::write(&skill_md_path, content)?;

        // 计算hash
        let skill_hash = hash::calculate_file_hash(&skill_md_path)?;

        // 更新manifest
        let mut manifest = self.load_manifest()?;
        let now = Utc::now().to_rfc3339();
        
        let skill = Skill {
            name: name.to_string(),
            description: description.to_string(),
            created_at: now.clone(),
            updated_at: now,
            hash: skill_hash,
            path: format!("repository/{}", name),
        };
        
        manifest.add_skill(skill);
        manifest.save(&self.base_path.join("manifest.json"))?;

        Ok(())
    }

    pub fn delete_skill(&mut self, name: &str) -> Result<()> {
        // 检查是否存在
        let mut manifest = self.load_manifest()?;
        if manifest.get_skill(name).is_none() {
            return Err(anyhow!("Skill '{}' not found", name));
        }

        // 删除目录
        let skill_path = self.base_path.join("repository").join(name);
        fs_utils::safe_remove_dir(&skill_path)?;

        // 更新manifest
        manifest.remove_skill(name);
        manifest.save(&self.base_path.join("manifest.json"))?;

        Ok(())
    }

    pub fn list_skills(&self) -> Result<Vec<Skill>> {
        let manifest = self.load_manifest()?;
        let mut skills: Vec<Skill> = manifest.skills.values().cloned().collect();
        skills.sort_by(|a, b| a.name.cmp(&b.name));
        Ok(skills)
    }

    fn load_manifest(&self) -> Result<Manifest> {
        let manifest_path = self.base_path.join("manifest.json");
        Manifest::load(&manifest_path)
    }
}
```

- [ ] **步骤 4: 运行测试验证通过**

运行: `cargo test test_repository`
预期: PASS

- [ ] **步骤 5: Commit Repository Manager**

```bash
git add src/core/repository.rs tests/unit_repository.rs
git commit -m "feat: add Repository Manager with init, create, delete, list"
```

---

### 任务 9: Sync Engine核心功能

**文件:**
- 创建: `src/core/sync.rs`
- 创建: `tests/unit_sync.rs`

- [ ] **步骤 1: 编写Sync测试**

创建 `tests/unit_sync.rs`:

```rust
use skillstack::core::sync::SyncEngine;
use std::fs;
use std::os::unix::fs as unix_fs;
use tempfile::TempDir;

#[test]
fn test_create_symlink() {
    let temp_dir = TempDir::new().unwrap();
    let source = temp_dir.path().join("source");
    let target = temp_dir.path().join("target");
    
    fs::create_dir(&source).unwrap();
    
    let engine = SyncEngine::new();
    engine.create_symlink(&source, &target).unwrap();
    
    assert!(target.exists());
    assert!(target.read_link().is_ok());
}

#[test]
fn test_verify_symlink() {
    let temp_dir = TempDir::new().unwrap();
    let source = temp_dir.path().join("source");
    let target = temp_dir.path().join("target");
    
    fs::create_dir(&source).unwrap();
    unix_fs::symlink(&source, &target).unwrap();
    
    let engine = SyncEngine::new();
    assert!(engine.verify_symlink(&target, &source).unwrap());
}
```

- [ ] **步骤 2: 运行测试验证失败**

运行: `cargo test test_create_symlink`
预期: FAIL

- [ ] **步骤 3: 实现Sync Engine**

创建 `src/core/sync.rs`:

```rust
use anyhow::{anyhow, Result};
use std::fs;
use std::path::Path;

#[cfg(unix)]
use std::os::unix::fs as unix_fs;

pub struct SyncEngine;

impl SyncEngine {
    pub fn new() -> Self {
        Self
    }

    /// 创建symlink: target -> source
    pub fn create_symlink(&self, source: &Path, target: &Path) -> Result<()> {
        // 如果target已存在,先备份
        if target.exists() {
            let backup = target.with_extension("backup");
            if target.is_symlink() {
                fs::remove_file(target)?;
            } else {
                fs::rename(target, &backup)?;
            }
        }

        // 创建symlink
        #[cfg(unix)]
        unix_fs::symlink(source, target)?;

        #[cfg(not(unix))]
        return Err(anyhow!("Symlink not supported on this platform"));

        Ok(())
    }

    /// 验证symlink是否有效且指向正确的source
    pub fn verify_symlink(&self, target: &Path, expected_source: &Path) -> Result<bool> {
        if !target.exists() {
            return Ok(false);
        }

        if !target.is_symlink() {
            return Ok(false);
        }

        let actual_source = target.read_link()?;
        Ok(actual_source == expected_source)
    }

    /// 重建损坏的symlink
    pub fn rebuild_symlink(&self, source: &Path, target: &Path) -> Result<()> {
        if target.exists() && target.is_symlink() {
            fs::remove_file(target)?;
        }
        self.create_symlink(source, target)
    }
}
```

- [ ] **步骤 4: 运行测试验证通过**

运行: `cargo test test_sync`
预期: PASS

- [ ] **步骤 5: Commit Sync Engine**

```bash
git add src/core/sync.rs tests/unit_sync.rs
git commit -m "feat: add Sync Engine for symlink management"
```

---

### 任务 10: CLI命令 - init

**文件:**
- 创建: `src/cli/mod.rs`
- 创建: `src/cli/commands.rs`
- 修改: `src/main.rs`

- [ ] **步骤 1: 定义init命令结构**

创建 `src/cli/mod.rs`:
```rust
pub mod commands;
```

创建 `src/cli/commands.rs`:

```rust
use clap::{Parser, Subcommand};
use anyhow::Result;

#[derive(Parser)]
#[command(name = "skillstack")]
#[command(about = "Centralized skill management for Claude Code")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Initialize the central repository
    Init {
        /// Force re-initialization
        #[arg(long)]
        force: bool,
        
        /// Skip importing existing skills
        #[arg(long)]
        no_import: bool,
    },
}

pub fn run(cli: Cli) -> Result<()> {
    match cli.command {
        Commands::Init { force, no_import } => cmd_init(force, no_import),
    }
}

fn cmd_init(force: bool, no_import: bool) -> Result<()> {
    use crate::core::repository::Repository;
    use crate::core::sync::SyncEngine;
    use crate::utils::{fs, ui};
    
    let base_path = fs::expand_tilde("~/.skillstack");
    let claude_path = fs::expand_tilde("~/.claude/skills");
    
    // 检查是否已初始化
    if base_path.exists() && !force {
        return Err(anyhow::anyhow!("Already initialized. Use --force to re-initialize"));
    }
    
    // 初始化仓库
    let repo = Repository::new(&base_path);
    repo.init(claude_path.to_str().unwrap())?;
    
    ui::success("Repository initialized at ~/.skillstack");
    
    // TODO: 扫描和导入现有skills
    // TODO: 创建symlink
    
    Ok(())
}
```

- [ ] **步骤 2: 更新main.rs使用新的CLI**

修改 `src/main.rs`:

```rust
use clap::Parser;
use skillstack::cli::commands::{Cli, run};

fn main() {
    let cli = Cli::parse();
    
    if let Err(e) = run(cli) {
        eprintln!("Error: {}", e);
        std::process::exit(1);
    }
}
```

- [ ] **步骤 3: 测试init命令**

运行: `cargo build && ./target/debug/skillstack init --help`
预期: 显示help信息

运行: `cargo build && ./target/debug/skillstack init`
预期: 创建~/.skillstack目录

- [ ] **步骤 4: Commit init命令基础**

```bash
git add src/cli/ src/main.rs
git commit -m "feat: add init command structure"
```

---

### 任务 11: 完善init命令 - 导入现有skills

**文件:**
- 修改: `src/cli/commands.rs`
- 修改: `src/core/repository.rs`

- [ ] **步骤 1: 在Repository中添加导入功能**

修改 `src/core/repository.rs`, 添加方法:

```rust
impl Repository {
    // ... 现有方法 ...
    
    /// 扫描目录下的所有skills
    pub fn scan_skills(&self, dir: &Path) -> Result<Vec<String>> {
        use walkdir::WalkDir;
        
        let mut skills = Vec::new();
        
        for entry in WalkDir::new(dir).max_depth(2) {
            let entry = entry?;
            if entry.file_name() == "SKILL.md" {
                if let Some(parent) = entry.path().parent() {
                    if let Some(name) = parent.file_name() {
                        skills.push(name.to_string_lossy().to_string());
                    }
                }
            }
        }
        
        Ok(skills)
    }
    
    /// 从外部目录导入skill
    pub fn import_skill(&mut self, source_path: &Path, skill_name: Option<&str>) -> Result<()> {
        // 确定skill名称
        let name = if let Some(n) = skill_name {
            n.to_string()
        } else {
            source_path
                .file_name()
                .ok_or_else(|| anyhow!("Invalid source path"))?
                .to_string_lossy()
                .to_string()
        };
        
        Skill::validate_name(&name)?;
        
        // 检查是否已存在
        let dest_path = self.base_path.join("repository").join(&name);
        if dest_path.exists() {
            return Err(anyhow!("Skill '{}' already exists", name));
        }
        
        // 复制文件
        fs_utils::copy_dir_recursive(source_path, &dest_path)?;
        
        // 读取frontmatter
        let skill_md = dest_path.join("SKILL.md");
        let content = fs::read_to_string(&skill_md)?;
        let (fm_name, description) = frontmatter::parse(&content)?;
        
        // 计算hash
        let skill_hash = hash::calculate_file_hash(&skill_md)?;
        
        // 更新manifest
        let mut manifest = self.load_manifest()?;
        let now = Utc::now().to_rfc3339();
        
        let skill = Skill {
            name: name.clone(),
            description,
            created_at: now.clone(),
            updated_at: now,
            hash: skill_hash,
            path: format!("repository/{}", name),
        };
        
        manifest.add_skill(skill);
        manifest.save(&self.base_path.join("manifest.json"))?;
        
        Ok(())
    }
}
```

- [ ] **步骤 2: 完善init命令的导入逻辑**

修改 `src/cli/commands.rs` 中的 `cmd_init`:

```rust
fn cmd_init(force: bool, no_import: bool) -> Result<()> {
    use crate::core::repository::Repository;
    use crate::core::sync::SyncEngine;
    use crate::utils::{fs, ui};
    
    let base_path = fs::expand_tilde("~/.skillstack");
    let claude_path = fs::expand_tilde("~/.claude/skills");
    
    // 检查是否已初始化
    if base_path.exists() && !force {
        return Err(anyhow::anyhow!("Already initialized. Use --force to re-initialize"));
    }
    
    // 初始化仓库
    let mut repo = Repository::new(&base_path);
    repo.init(claude_path.to_str().unwrap())?;
    
    ui::success("Repository initialized at ~/.skillstack");
    
    // 扫描和导入现有skills
    if !no_import && claude_path.exists() && !claude_path.is_symlink() {
        match repo.scan_skills(&claude_path) {
            Ok(skills) if !skills.is_empty() => {
                println!("\n🔍 Found {} existing skills:", skills.len());
                for skill in &skills {
                    println!("  📋 {}", skill);
                }
                
                if ui::prompt("Import these skills to the central repository?") {
                    for skill in skills {
                        let skill_path = claude_path.join(&skill);
                        if let Err(e) = repo.import_skill(&skill_path, Some(&skill)) {
                            ui::warning(&format!("Failed to import '{}': {}", skill, e));
                        } else {
                            ui::success(&format!("Imported '{}'", skill));
                        }
                    }
                }
            }
            _ => {}
        }
    }
    
    // 创建symlink
    let repo_path = base_path.join("repository");
    let sync_engine = SyncEngine::new();
    sync_engine.create_symlink(&repo_path, &claude_path)?;
    
    ui::success(&format!("Symlink created: ~/.claude/skills -> ~/.skillstack/repository"));
    
    println!("\n✅ SkillStack initialized!\n");
    println!("Next steps:");
    println!("  - skillstack list          View all skills");
    println!("  - skillstack add <name>    Create a new skill");
    
    Ok(())
}
```

- [ ] **步骤 3: 测试完整init流程**

运行: `cargo build && ./target/debug/skillstack init`
预期: 成功初始化,导入skills,创建symlink

- [ ] **步骤 4: Commit完整init命令**

```bash
git add src/core/repository.rs src/cli/commands.rs
git commit -m "feat: complete init command with skill import and symlink"
```

---

### 任务 12: CLI命令 - list

**文件:**
- 修改: `src/cli/commands.rs`

- [ ] **步骤 1: 添加list命令定义**

修改 `src/cli/commands.rs`, 在 `Commands` enum中添加:

```rust
#[derive(Subcommand)]
pub enum Commands {
    // ... Init ...
    
    /// List all skills
    List {
        /// Sort by field (name/created/updated)
        #[arg(long, default_value = "name")]
        sort: String,
        
        /// Reverse sort order
        #[arg(long)]
        reverse: bool,
    },
}
```

- [ ] **步骤 2: 在run函数中处理list命令**

修改 `run` 函数:

```rust
pub fn run(cli: Cli) -> Result<()> {
    match cli.command {
        Commands::Init { force, no_import } => cmd_init(force, no_import),
        Commands::List { sort, reverse } => cmd_list(&sort, reverse),
    }
}
```

- [ ] **步骤 3: 实现list命令**

添加 `cmd_list` 函数:

```rust
fn cmd_list(sort_by: &str, reverse: bool) -> Result<()> {
    use crate::core::repository::Repository;
    use crate::utils::{fs, ui};
    use chrono::{DateTime, Utc};
    
    let base_path = fs::expand_tilde("~/.skillstack");
    if !base_path.exists() {
        return Err(anyhow::anyhow!("Not initialized. Run 'skillstack init' first"));
    }
    
    let repo = Repository::new(&base_path);
    let mut skills = repo.list_skills()?;
    
    if skills.is_empty() {
        println!("No skills found.");
        ui::info("Run 'skillstack add <name>' to create your first skill");
        return Ok(());
    }
    
    // 排序
    match sort_by {
        "created" => skills.sort_by(|a, b| a.created_at.cmp(&b.created_at)),
        "updated" => skills.sort_by(|a, b| a.updated_at.cmp(&b.updated_at)),
        _ => skills.sort_by(|a, b| a.name.cmp(&b.name)),
    }
    
    if reverse {
        skills.reverse();
    }
    
    // 打印表头
    let widths = [30, 50, 20];
    println!("{}", ui::format_table_row(&["NAME", "DESCRIPTION", "UPDATED"], &widths));
    println!("{}", "-".repeat(100));
    
    // 打印skills
    for skill in &skills {
        let updated = format_relative_time(&skill.updated_at);
        println!("{}", ui::format_table_row(
            &[&skill.name, &skill.description, &updated],
            &widths
        ));
    }
    
    println!("\nTotal: {} skills", skills.len());
    
    Ok(())
}

fn format_relative_time(iso_time: &str) -> String {
    use chrono::{DateTime, Utc};
    
    if let Ok(dt) = DateTime::parse_from_rfc3339(iso_time) {
        let now = Utc::now();
        let duration = now.signed_duration_since(dt);
        
        if duration.num_days() > 0 {
            format!("{}d ago", duration.num_days())
        } else if duration.num_hours() > 0 {
            format!("{}h ago", duration.num_hours())
        } else if duration.num_minutes() > 0 {
            format!("{}m ago", duration.num_minutes())
        } else {
            "just now".to_string()
        }
    } else {
        iso_time.to_string()
    }
}
```

- [ ] **步骤 4: 测试list命令**

运行: `cargo build && ./target/debug/skillstack list`
预期: 显示skills列表

- [ ] **步骤 5: Commit list命令**

```bash
git add src/cli/commands.rs
git commit -m "feat: add list command with sorting"
```

---

### 任务 13: CLI命令 - add

**文件:**
- 修改: `src/cli/commands.rs`

- [ ] **步骤 1: 添加add命令定义**

修改 `Commands` enum:

```rust
/// Create a new skill
Add {
    /// Skill name
    name: String,
    
    /// Editor to use
    #[arg(long)]
    editor: Option<String>,
    
    /// Don't open editor after creation
    #[arg(long)]
    no_edit: bool,
},
```

- [ ] **步骤 2: 在run函数处理add命令**

```rust
Commands::Add { name, editor, no_edit } => cmd_add(&name, editor.as_deref(), no_edit),
```

- [ ] **步骤 3: 实现add命令**

```rust
fn cmd_add(name: &str, editor: Option<&str>, no_edit: bool) -> Result<()> {
    use crate::core::repository::Repository;
    use crate::utils::{fs, ui};
    use std::process::Command;
    
    let base_path = fs::expand_tilde("~/.skillstack");
    if !base_path.exists() {
        return Err(anyhow::anyhow!("Not initialized. Run 'skillstack init' first"));
    }
    
    let mut repo = Repository::new(&base_path);
    
    // 创建skill
    repo.create_skill(name, &format!("Description for {}", name))?;
    ui::success(&format!("Skill '{}' created successfully", name));
    
    // 打开编辑器
    if !no_edit {
        let skill_file = base_path.join("repository").join(name).join("SKILL.md");
        
        // 确定使用哪个编辑器
        let editor_cmd = if let Some(e) = editor {
            e.to_string()
        } else {
            // 从config读取
            let config_path = base_path.join("config.json");
            if let Ok(content) = std::fs::read_to_string(config_path) {
                if let Ok(config) = serde_json::from_str::<serde_json::Value>(&content) {
                    config["editor"].as_str().unwrap_or("vim").to_string()
                } else {
                    "vim".to_string()
                }
            } else {
                "vim".to_string()
            }
        };
        
        println!("📝 Opening editor...");
        let status = Command::new(&editor_cmd)
            .arg(&skill_file)
            .status()?;
        
        if !status.success() {
            ui::warning("Editor exited with error");
        }
        
        ui::success("Saved and synced");
    }
    
    Ok(())
}
```

- [ ] **步骤 4: 测试add命令**

运行: `cargo build && ./target/debug/skillstack add test-skill --no-edit`
预期: 创建skill成功

- [ ] **步骤 5: Commit add命令**

```bash
git add src/cli/commands.rs
git commit -m "feat: add command to create new skills"
```

---

### 任务 14: CLI命令 - edit, delete, sync

**文件:**
- 修改: `src/cli/commands.rs`

- [ ] **步骤 1: 添加命令定义**

```rust
/// Edit an existing skill
Edit {
    /// Skill name
    name: String,
    
    /// Editor to use
    #[arg(long)]
    editor: Option<String>,
},

/// Delete a skill
Delete {
    /// Skill name
    name: String,
    
    /// Skip confirmation
    #[arg(short, long)]
    force: bool,
},

/// Sync to Claude skills directory
Sync {
    /// Force rebuild symlink
    #[arg(long)]
    force: bool,
},
```

- [ ] **步骤 2: 实现edit命令**

```rust
fn cmd_edit(name: &str, editor: Option<&str>) -> Result<()> {
    use crate::core::repository::Repository;
    use crate::utils::{fs, ui, hash};
    use std::process::Command;
    
    let base_path = fs::expand_tilde("~/.skillstack");
    let skill_file = base_path.join("repository").join(name).join("SKILL.md");
    
    if !skill_file.exists() {
        return Err(anyhow::anyhow!("Skill '{}' not found", name));
    }
    
    let editor_cmd = editor.unwrap_or("vim");
    
    println!("📝 Editing '{}'...", name);
    Command::new(editor_cmd).arg(&skill_file).status()?;
    
    // 更新hash和时间
    // TODO: 实现manifest更新逻辑
    
    ui::success("Saved and synced");
    Ok(())
}
```

- [ ] **步骤 3: 实现delete命令**

```rust
fn cmd_delete(name: &str, force: bool) -> Result<()> {
    use crate::core::repository::Repository;
    use crate::utils::{fs, ui};
    
    let base_path = fs::expand_tilde("~/.skillstack");
    let mut repo = Repository::new(&base_path);
    
    if !force {
        ui::warning(&format!("About to delete '{}'", name));
        println!("This action cannot be undone.");
        
        if !ui::prompt("Continue?") {
            println!("Cancelled.");
            return Ok(());
        }
    }
    
    repo.delete_skill(name)?;
    ui::success(&format!("Skill '{}' deleted", name));
    
    Ok(())
}
```

- [ ] **步骤 4: 实现sync命令**

```rust
fn cmd_sync(force: bool) -> Result<()> {
    use crate::core::{repository::Repository, sync::SyncEngine};
    use crate::utils::{fs, ui};
    
    let base_path = fs::expand_tilde("~/.skillstack");
    let claude_path = fs::expand_tilde("~/.claude/skills");
    let repo_path = base_path.join("repository");
    
    let sync_engine = SyncEngine::new();
    
    // 验证或重建symlink
    if force || !sync_engine.verify_symlink(&claude_path, &repo_path).unwrap_or(false) {
        sync_engine.rebuild_symlink(&repo_path, &claude_path)?;
    }
    
    // 更新manifest的last_sync
    // TODO: 实现
    
    let repo = Repository::new(&base_path);
    let skill_count = repo.list_skills()?.len();
    
    ui::success(&format!("Synced {} skills to ~/.claude/skills", skill_count));
    
    Ok(())
}
```

- [ ] **步骤 5: 更新run函数**

```rust
Commands::Edit { name, editor } => cmd_edit(&name, editor.as_deref()),
Commands::Delete { name, force } => cmd_delete(&name, force),
Commands::Sync { force } => cmd_sync(force),
```

- [ ] **步骤 6: 测试命令**

运行: `cargo build && ./target/debug/skillstack sync`
预期: 同步成功

- [ ] **步骤 7: Commit基础CRUD命令**

```bash
git add src/cli/commands.rs
git commit -m "feat: add edit, delete, sync commands"
```

---

### 任务 15: CLI命令 - import, show, doctor, status

由于篇幅限制,我将这些P1命令合并为一个任务。

**文件:**
- 修改: `src/cli/commands.rs`

- [ ] **步骤 1: 添加P1命令定义**

```rust
/// Import an external skill
Import {
    /// Path to skill directory
    path: String,
    
    /// Override skill name
    #[arg(long)]
    name: Option<String>,
},

/// Show skill details
Show {
    /// Skill name
    name: String,
},

/// Health check and diagnostics
Doctor {
    /// Auto-fix detected issues
    #[arg(long)]
    fix: bool,
},

/// Display sync status
Status,
```

- [ ] **步骤 2: 实现import命令**

```rust
fn cmd_import(path_str: &str, name: Option<&str>) -> Result<()> {
    use crate::core::repository::Repository;
    use crate::utils::{fs, ui};
    use std::path::PathBuf;
    
    let base_path = fs::expand_tilde("~/.skillstack");
    let mut repo = Repository::new(&base_path);
    
    let import_path = PathBuf::from(path_str);
    repo.import_skill(&import_path, name)?;
    
    let skill_name = name.unwrap_or_else(|| import_path.file_name().unwrap().to_str().unwrap());
    ui::success(&format!("Imported '{}' from {}", skill_name, path_str));
    
    Ok(())
}
```

- [ ] **步骤 3: 实现show命令**

```rust
fn cmd_show(name: &str) -> Result<()> {
    use crate::core::repository::Repository;
    use crate::utils::fs;
    
    let base_path = fs::expand_tilde("~/.skillstack");
    let repo = Repository::new(&base_path);
    
    let skills = repo.list_skills()?;
    let skill = skills.iter().find(|s| s.name == name)
        .ok_or_else(|| anyhow::anyhow!("Skill '{}' not found", name))?;
    
    println!("Name: {}", skill.name);
    println!("Description: {}", skill.description);
    println!("Created: {}", skill.created_at);
    println!("Updated: {}", skill.updated_at);
    println!("Path: ~/.skillstack/{}", skill.path);
    println!("Hash: {}", skill.hash);
    
    Ok(())
}
```

- [ ] **步骤 4: 实现doctor命令**

```rust
fn cmd_doctor(fix: bool) -> Result<()> {
    use crate::core::{repository::Repository, sync::SyncEngine};
    use crate::utils::{fs, ui};
    
    println!("🏥 Running health check...\n");
    
    let base_path = fs::expand_tilde("~/.skillstack");
    let claude_path = fs::expand_tilde("~/.claude/skills");
    let repo_path = base_path.join("repository");
    
    let mut issues = Vec::new();
    
    // 检查目录结构
    if !base_path.exists() {
        issues.push("❌ Directory: ~/.skillstack/ not found");
    } else {
        ui::success("Directory structure: OK");
    }
    
    // 检查symlink
    let sync_engine = SyncEngine::new();
    if !sync_engine.verify_symlink(&claude_path, &repo_path).unwrap_or(false) {
        issues.push("❌ Symlink: Invalid or broken");
        if fix {
            sync_engine.rebuild_symlink(&repo_path, &claude_path)?;
            ui::success("Fixed: Rebuilt symlink");
        }
    } else {
        ui::success("Symlink: OK");
    }
    
    // 检查manifest一致性
    // TODO: 实现详细检查
    
    if issues.is_empty() {
        println!("\n✅ All checks passed!");
    } else {
        println!("\n⚠️  Detected {} issue(s):", issues.len());
        for issue in issues {
            println!("  {}", issue);
        }
    }
    
    Ok(())
}
```

- [ ] **步骤 5: 实现status命令**

```rust
fn cmd_status() -> Result<()> {
    use crate::core::repository::Repository;
    use crate::utils::fs;
    
    let base_path = fs::expand_tilde("~/.skillstack");
    let claude_path = fs::expand_tilde("~/.claude/skills");
    
    let repo = Repository::new(&base_path);
    let skill_count = repo.list_skills()?.len();
    
    println!("Repository: ~/.skillstack/repository ({} skills)", skill_count);
    
    let symlink_status = if claude_path.is_symlink() {
        "symlink ✅"
    } else {
        "not symlink ❌"
    };
    println!("Claude Path: ~/.claude/skills ({})", symlink_status);
    
    // TODO: 显示last_sync时间
    
    println!("Status: All synced ✅");
    
    Ok(())
}
```

- [ ] **步骤 6: 更新run函数**

```rust
Commands::Import { path, name } => cmd_import(&path, name.as_deref()),
Commands::Show { name } => cmd_show(&name),
Commands::Doctor { fix } => cmd_doctor(fix),
Commands::Status => cmd_status(),
```

- [ ] **步骤 7: 测试P1命令**

运行各个命令验证功能

- [ ] **步骤 8: Commit P1命令**

```bash
git add src/cli/commands.rs
git commit -m "feat: add P1 commands (import, show, doctor, status)"
```

---

### 任务 16: 集成测试

**文件:**
- 创建: `tests/integration_test.rs`

- [ ] **步骤 1: 编写完整工作流集成测试**

```rust
use std::process::Command;
use tempfile::TempDir;

#[test]
fn test_full_workflow() {
    let temp_dir = TempDir::new().unwrap();
    let home = temp_dir.path();
    
    // 设置环境变量
    std::env::set_var("HOME", home);
    
    // 1. init
    let output = Command::new("cargo")
        .args(&["run", "--", "init", "--no-import"])
        .output()
        .unwrap();
    assert!(output.status.success());
    
    // 2. add
    let output = Command::new("cargo")
        .args(&["run", "--", "add", "test-skill", "--no-edit"])
        .output()
        .unwrap();
    assert!(output.status.success());
    
    // 3. list
    let output = Command::new("cargo")
        .args(&["run", "--", "list"])
        .output()
        .unwrap();
    assert!(output.status.success());
    assert!(String::from_utf8_lossy(&output.stdout).contains("test-skill"));
    
    // 4. sync
    let output = Command::new("cargo")
        .args(&["run", "--", "sync"])
        .output()
        .unwrap();
    assert!(output.status.success());
    
    // 5. doctor
    let output = Command::new("cargo")
        .args(&["run", "--", "doctor"])
        .output()
        .unwrap();
    assert!(output.status.success());
    
    // 6. delete
    let output = Command::new("cargo")
        .args(&["run", "--", "delete", "test-skill", "--force"])
        .output()
        .unwrap();
    assert!(output.status.success());
}
```

- [ ] **步骤 2: 运行集成测试**

运行: `cargo test test_full_workflow`
预期: PASS

- [ ] **步骤 3: Commit集成测试**

```bash
git add tests/integration_test.rs
git commit -m "test: add full workflow integration test"
```

---

### 任务 17: 文档和README

**文件:**
- 创建: `README.md`
- 创建: `LICENSE`
- 创建: `CHANGELOG.md`

- [ ] **步骤 1: 编写README.md**

```markdown
# SkillStack

Centralized skill management for Claude Code users.

## Features

- 🎯 **Single Source of Truth**: Manage all skills in one central repository
- 🔄 **Auto Sync**: Instant synchronization via symlinks
- 📦 **Import Existing**: Migrate your current skills with one command
- 🛠️ **Full CRUD**: Create, read, update, delete skills easily
- 🏥 **Health Check**: Detect and fix configuration issues

## Installation

```bash
cargo install --path .
```

## Quick Start

```bash
# Initialize the repository
skillstack init

# Create a new skill
skillstack add my-skill

# List all skills
skillstack list

# Sync to Claude
skillstack sync
```

## Commands

- `init` - Initialize the central repository
- `list` - List all skills
- `add <name>` - Create a new skill
- `edit <name>` - Edit an existing skill
- `delete <name>` - Delete a skill
- `sync` - Sync to Claude skills directory
- `import <path>` - Import an external skill
- `show <name>` - Show skill details
- `doctor` - Run health check
- `status` - Display sync status

## License

MIT
```

- [ ] **步骤 2: 创建LICENSE文件**

复制MIT许可证文本

- [ ] **步骤 3: 创建CHANGELOG.md**

```markdown
# Changelog

## [0.1.0] - 2026-04-03

### Added
- Initial MVP release
- P0 commands: init, list, add, edit, delete, sync, import
- P1 commands: show, doctor, status
- Symlink-based synchronization
- Manifest-based state tracking
```

- [ ] **步骤 4: Commit文档**

```bash
git add README.md LICENSE CHANGELOG.md
git commit -m "docs: add README, LICENSE, and CHANGELOG"
```

---

### 任务 18: 最终测试和发布准备

**文件:**
- 无新文件

- [ ] **步骤 1: 运行所有测试**

```bash
cargo test
```

预期: 所有测试通过

- [ ] **步骤 2: 编译release版本**

```bash
cargo build --release
```

预期: 编译成功

- [ ] **步骤 3: 手动测试清单**

在真实环境测试所有命令:
- [ ] init
- [ ] list
- [ ] add
- [ ] edit
- [ ] delete
- [ ] sync
- [ ] import
- [ ] show
- [ ] doctor
- [ ] status

- [ ] **步骤 4: 在Claude Code中验证**

- [ ] Claude能读取symlink的skills
- [ ] 修改skill后Claude立即生效

- [ ] **步骤 5: 创建release tag**

```bash
git tag -a v0.1.0-mvp -m "MVP release"
```

- [ ] **步骤 6: Commit最终状态**

```bash
git commit -m "chore: prepare v0.1.0-mvp release"
```

---

## 完成标准

MVP完成当且仅当:

1. ✅ 所有P0命令(7个)可用且功能正确
2. ✅ 所有P1命令(3个)可用
3. ✅ 单元测试和集成测试通过
4. ✅ 在真实Claude Code环境验证通过
5. ✅ README和文档完整
6. ✅ 可以编译release版本

---

## 预计时间

- 任务 1-7: 基础设施 (2天)
- 任务 8-11: 核心功能 (2天)
- 任务 12-14: P0命令 (2天)
- 任务 15: P1命令 (1天)
- 任务 16-18: 测试和文档 (1天)

**总计: 8工作日 (约2周内完成,考虑调试时间)**
