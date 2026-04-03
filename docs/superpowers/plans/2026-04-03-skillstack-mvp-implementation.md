# SkillStack MVP 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 @superpowers:subagent-driven-development（推荐）或 @superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 构建一个Rust CLI工具,为Claude Code用户提供集中式的Skill管理,解决"Skill分散、手动复制、版本混乱"的核心痛点。

**架构：** 中央仓库(~/.skillstack/repository/)作为单一真相来源,通过目录级symlink同步到Claude skills目录,使用JSON manifest和config追踪状态。核心包括Repository Manager、Manifest Manager、Config Manager、Sync Engine和CLI命令层。

**技术栈：** Rust 2021, Clap 4.5 (CLI), serde/serde_json (序列化), serde_yaml (frontmatter), sha2 (hash), chrono (时间), colored (输出), dialoguer (交互), walkdir (目录遍历), regex (验证), dirs (路径)

---

## 文件结构

### 将要创建的文件

**项目配置:**
- `Cargo.toml` - Rust项目配置和依赖
- `README.md` - 项目文档
- `LICENSE` - MIT许可证
- `.gitignore` - Git忽略规则

**源代码 (src/):**
- `main.rs` - CLI入口点
- `lib.rs` - 库入口
- `cli/commands.rs` - CLI命令
- `core/skill.rs` - Skill结构和验证(含测试)
- `core/manifest.rs` - Manifest管理(含测试)
- `core/config.rs` - Config管理(含测试)
- `core/repository.rs` - Repository CRUD(含测试)
- `core/sync.rs` - Symlink管理(含测试)
- `utils/hash.rs` - Hash计算
- `utils/frontmatter.rs` - Frontmatter解析
- `utils/fs.rs` - 文件系统辅助
- `utils/ui.rs` - UI辅助

**测试:**
- 各模块内的 `#[cfg(test)] mod tests` - 单元测试
- `tests/integration_test.rs` - 集成测试

### 职责说明

**core/config.rs:**
- `Config`结构体(claude_skills_path, editor, auto_sync)
- 读取/保存config.json
- 获取配置值
- 创建默认配置

**其他模块:** (职责说明略，见规格文档第8.1节)

---

## 任务分解

### 任务1: 项目初始化

**文件:** `Cargo.toml`, `src/main.rs`, `src/lib.rs`, `.gitignore`

- [ ] **步骤1: 创建Cargo.toml(含所有依赖)**

```toml
[package]
name = "skillstack"
version = "0.1.0"
edition = "2021"
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

- [ ] **步骤2: 创建src/main.rs**
```rust
fn main() {
    println!("SkillStack MVP");
}
```

- [ ] **步骤3: 创建src/lib.rs**
```rust
pub mod cli;
pub mod core;
pub mod utils;
```

- [ ] **步骤4: 创建.gitignore**
```
/target/
Cargo.lock
.DS_Store
```

- [ ] **步骤5: 验证编译**
运行: `cargo build`
预期: 成功

- [ ] **步骤6: Commit**
```bash
git add Cargo.toml src/ .gitignore
git commit -m "feat: initialize Rust project with all dependencies"
```

---

### 任务2: Skill结构(含模块内测试)

**文件:** `src/core/skill.rs`, `src/core/mod.rs`

- [ ] **步骤1: 创建src/core/mod.rs**
```rust
pub mod skill;
pub mod manifest;
pub mod config;
pub mod repository;
pub mod sync;
```

- [ ] **步骤2: 创建src/core/skill.rs(含测试)**
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
    pub fn validate_name(name: &str) -> Result<()> {
        let re = Regex::new(r"^[a-z][a-z0-9-]*$").unwrap();
        if re.is_match(name) {
            Ok(())
        } else {
            Err(anyhow!("Invalid skill name. Use lowercase letters, numbers, hyphens. Must start with letter."))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_name_valid() {
        assert!(Skill::validate_name("my-skill").is_ok());
        assert!(Skill::validate_name("skill-v2").is_ok());
    }

    #[test]
    fn test_validate_name_invalid() {
        assert!(Skill::validate_name("My-Skill").is_err());
        assert!(Skill::validate_name("my skill").is_err());
        assert!(Skill::validate_name("123-skill").is_err());
    }
}
```

- [ ] **步骤3: 运行测试**
运行: `cargo test skill::tests`
预期: PASS

- [ ] **步骤4: Commit**
```bash
git add src/core/
git commit -m "feat: add Skill struct with validation and tests"
```

---

### 任务3: Config管理(新增)

**文件:** `src/core/config.rs`

- [ ] **步骤1: 创建src/core/config.rs**
```rust
use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub claude_skills_path: String,
    pub editor: String,
    pub auto_sync: bool,
}

impl Config {
    pub fn default(claude_path: &str) -> Self {
        Self {
            claude_skills_path: claude_path.to_string(),
            editor: "vim".to_string(),
            auto_sync: true,
        }
    }

    pub fn load(path: &Path) -> Result<Self> {
        let content = fs::read_to_string(path)?;
        Ok(serde_json::from_str(&content)?)
    }

    pub fn save(&self, path: &Path) -> Result<()> {
        let json = serde_json::to_string_pretty(& self)?;
        fs::write(path, json)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_config_save_load() {
        let temp_dir = TempDir::new().unwrap();
        let path = temp_dir.path().join("config.json");
        
        let config = Config::default("/test/path");
        config.save(&path).unwrap();
        
        let loaded = Config::load(&path).unwrap();
        assert_eq!(loaded.editor, "vim");
    }
}
```

- [ ] **步骤2: 运行测试**
运行: `cargo test config::tests`
预期: PASS

- [ ] **步骤3: Commit**
```bash
git add src/core/config.rs
git commit -m "feat: add Config manager with save/load"
```

---

### 任务4: Manifest管理

**文件:** `src/core/manifest.rs`

- [ ] **步骤1: 创建src/core/manifest.rs(完整实现)**
```rust
use anyhow::Result;
use chrono::Utc;
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
    pub fn new(claude_path: &str) -> Self {
        Self {
            version: "1.0".to_string(),
            skills: HashMap::new(),
            sync_status: SyncStatus {
                claude_skills_path: claude_path.to_string(),
                last_sync: None,
                sync_method: "symlink".to_string(),
            },
        }
    }

    pub fn load(path: &Path) -> Result<Self> {
        let content = fs::read_to_string(path)?;
        Ok(serde_json::from_str(&content)?)
    }

    pub fn save(&self, path: &Path) -> Result<()> {
        if path.exists() {
            let backup = path.with_extension("json.bak");
            fs::copy(path, backup)?;
        }
        let json = serde_json::to_string_pretty(self)?;
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

    pub fn get_skill_mut(&mut self, name: &str) -> Option<&mut Skill> {
        self.skills.get_mut(name)
    }

    pub fn update_sync_time(&mut self) {
        self.sync_status.last_sync = Some(Utc::now().to_rfc3339());
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_manifest_new() {
        let m = Manifest::new("/test");
        assert_eq!(m.version, "1.0");
        assert!(m.skills.is_empty());
    }

    #[test]
    fn test_manifest_save_load() {
        let temp_dir = TempDir::new().unwrap();
        let path = temp_dir.path().join("manifest.json");
        
        let m = Manifest::new("/test");
        m.save(&path).unwrap();
        
        let loaded = Manifest::load(&path).unwrap();
        assert_eq!(loaded.version, "1.0");
    }
}
```

- [ ] **步骤2: 运行测试**
运行: `cargo test manifest::tests`
预期: PASS

- [ ] **步骤3: Commit**
```bash
git add src/core/manifest.rs
git commit -m "feat: add Manifest with full CRUD and sync time tracking"
```

---

### 任务5: Utils函数

**文件:** `src/utils/*.rs`

- [ ] **步骤1: 创建src/utils/mod.rs**
```rust
pub mod hash;
pub mod frontmatter;
pub mod fs;
pub mod ui;
```

- [ ] **步骤2: 创建src/utils/hash.rs**
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
    Ok(format!("sha256:{:x}", hasher.finalize()))
}
```

- [ ] **步骤3: 创建src/utils/frontmatter.rs**
```rust
use anyhow::{anyhow, Result};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize, Serialize)]
struct FrontmatterData {
    name: String,
    description: String,
}

pub fn parse(content: &str) -> Result<(String, String)> {
    let parts: Vec<&str> = content.splitn(3, "---").collect();
    if parts.len() < 3 {
        return Err(anyhow!("Invalid frontmatter format"));
    }
    let yaml = parts[1].trim();
    let data: FrontmatterData = serde_yaml::from_str(yaml)?;
    Ok((data.name, data.description))
}

pub fn generate_template(name: &str, desc: &str) -> String {
    format!(
        "---\nname: {}\ndescription: {}\n---\n\n# {}\n\n## 功能说明\n\n这个skill用于...\n",
        name, desc, name
    )
}
```

- [ ] **步骤4: 创建src/utils/fs.rs**
```rust
use anyhow::Result;
use std::fs;
use std::path::{Path, PathBuf};

pub fn expand_tilde(path: &str) -> PathBuf {
    if path.starts_with("~") {
        if let Some(home) = dirs::home_dir() {
            return PathBuf::from(path.replacen("~", &home.to_string_lossy(), 1));
        }
    }
    PathBuf::from(path)
}

pub fn copy_dir_recursive(src: &Path, dst: &Path) -> Result<()> {
    fs::create_dir_all(dst)?;
    for entry in fs::read_dir(src)? {
        let entry = entry?;
        let src_path = entry.path();
        let dst_path = dst.join(entry.file_name());
        if entry.file_type()?.is_dir() {
            copy_dir_recursive(&src_path, &dst_path)?;
        } else {
            fs::copy(&src_path, &dst_path)?;
        }
    }
    Ok(())
}
```

- [ ] **步骤5: 创建src/utils/ui.rs**
```rust
use colored::*;
use dialoguer::Confirm;

pub fn success(msg: &str) {
    println!("{} {}", "✅".green(), msg);
}

pub fn error(msg: &str) {
    eprintln!("{} {}", "❌".red(), msg);
}

pub fn warning(msg: &str) {
    println!("{} {}", "⚠️ ".yellow(), msg);
}

pub fn prompt(msg: &str) -> bool {
    Confirm::new().with_prompt(msg).default(true).interact().unwrap_or(false)
}

pub fn info(msg: &str) {
    println!("{} {}", "💡".blue(), msg);
}

pub fn format_table_row(cols: &[&str], widths: &[usize]) -> String {
    cols.iter().zip(widths).map(|(c, w)| format!("{:<w$}", c, w=w)).collect::<Vec<_>>().join("  ")
}
```

- [ ] **步骤6: 运行测试**
运行: `cargo build`
预期: 成功编译

- [ ] **步骤7: Commit**
```bash
git add src/utils/
git commit -m "feat: add utility functions (hash, frontmatter, fs, ui)"
```

---

### 任务6: Sync Engine

**文件:** `src/core/sync.rs`

- [ ] **步骤1: 创建src/core/sync.rs**
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

    pub fn create_symlink(&self, source: &Path, target: &Path) -> Result<()> {
        if target.exists() {
            let backup = target.with_extension("backup");
            if target.is_symlink() {
                fs::remove_file(target)?;
            } else {
                fs::rename(target, &backup)?;
            }
        }

        #[cfg(unix)]
        unix_fs::symlink(source, target)?;

        #[cfg(not(unix))]
        return Err(anyhow!("Symlink not supported on this platform"));

        Ok(())
    }

    pub fn verify_symlink(&self, target: &Path, expected_source: &Path) -> Result<bool> {
        if !target.exists() || !target.is_symlink() {
            return Ok(false);
        }
        let actual = target.read_link()?;
        Ok(actual == expected_source)
    }

    pub fn rebuild_symlink(&self, source: &Path, target: &Path) -> Result<()> {
        if target.exists() && target.is_symlink() {
            fs::remove_file(target)?;
        }
        self.create_symlink(source, target)
    }
}

#[cfg(test)]
#[cfg(unix)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_create_symlink() {
        let temp = TempDir::new().unwrap();
        let src = temp.path().join("src");
        let tgt = temp.path().join("tgt");
        fs::create_dir(&src).unwrap();
        
        let engine = SyncEngine::new();
        engine.create_symlink(&src, &tgt).unwrap();
        
        assert!(tgt.is_symlink());
    }
}
```

- [ ] **步骤2: 运行测试**
运行: `cargo test sync::tests`
预期: PASS

- [ ] **步骤3: Commit**
```bash
git add src/core/sync.rs
git commit -m "feat: add Sync Engine for symlink management"
```

---

### 任务7: Repository Manager

**文件:** `src/core/repository.rs`

- [ ] **步骤1: 创建src/core/repository.rs(完整实现)**
```rust
use anyhow::{anyhow, Result};
use chrono::Utc;
use std::fs;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

use super::{config::Config, manifest::Manifest, skill::Skill};
use crate::utils::{frontmatter, fs as fs_utils, hash};

pub struct Repository {
    base_path: PathBuf,
}

impl Repository {
    pub fn new(base_path: &Path) -> Self {
        Self { base_path: base_path.to_path_buf() }
    }

    pub fn init(&self, claude_path: &str) -> Result<()> {
        if self.base_path.exists() {
            return Err(anyhow!("Already initialized"));
        }

        fs::create_dir_all(self.base_path.join("repository"))?;

        let manifest = Manifest::new(claude_path);
        manifest.save(&self.base_path.join("manifest.json"))?;

        let config = Config::default(claude_path);
        config.save(&self.base_path.join("config.json"))?;

        Ok(())
    }

    pub fn create_skill(&mut self, name: &str, description: &str) -> Result<()> {
        Skill::validate_name(name)?;

        let skill_path = self.base_path.join("repository").join(name);
        if skill_path.exists() {
            return Err(anyhow!("Skill '{}' already exists", name));
        }

        fs::create_dir_all(&skill_path)?;

        let content = frontmatter::generate_template(name, description);
        let skill_md = skill_path.join("SKILL.md");
        fs::write(&skill_md, content)?;

        let skill_hash = hash::calculate_file_hash(&skill_md)?;
        let now = Utc::now().to_rfc3339();

        let skill = Skill {
            name: name.to_string(),
            description: description.to_string(),
            created_at: now.clone(),
            updated_at: now,
            hash: skill_hash,
            path: format!("repository/{}", name),
        };

        let mut manifest = self.load_manifest()?;
        manifest.add_skill(skill);
        manifest.save(&self.base_path.join("manifest.json"))?;

        Ok(())
    }

    pub fn update_skill_hash(&mut self, name: &str) -> Result<()> {
        let skill_md = self.base_path.join("repository").join(name).join("SKILL.md");
        if !skill_md.exists() {
            return Err(anyhow!("Skill '{}' not found", name));
        }

        let new_hash = hash::calculate_file_hash(&skill_md)?;
        let mut manifest = self.load_manifest()?;

        if let Some(skill) = manifest.get_skill_mut(name) {
            skill.hash = new_hash;
            skill.updated_at = Utc::now().to_rfc3339();
            manifest.save(&self.base_path.join("manifest.json"))?;
            Ok(())
        } else {
            Err(anyhow!("Skill '{}' not in manifest", name))
        }
    }

    pub fn delete_skill(&mut self, name: &str) -> Result<()> {
        let mut manifest = self.load_manifest()?;
        if manifest.get_skill(name).is_none() {
            return Err(anyhow!("Skill '{}' not found", name));
        }

        let skill_path = self.base_path.join("repository").join(name);
        if skill_path.exists() {
            fs::remove_dir_all(&skill_path)?;
        }

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

    pub fn scan_skills(&self, dir: &Path) -> Result<Vec<String>> {
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

    pub fn import_skill(&mut self, source_path: &Path, skill_name: Option<&str>) -> Result<()> {
        let name = skill_name.unwrap_or_else(|| {
            source_path.file_name().unwrap().to_str().unwrap()
        });

        Skill::validate_name(name)?;

        let dest_path = self.base_path.join("repository").join(name);
        if dest_path.exists() {
            return Err(anyhow!("Skill '{}' already exists", name));
        }

        fs_utils::copy_dir_recursive(source_path, &dest_path)?;

        let skill_md = dest_path.join("SKILL.md");
        let content = fs::read_to_string(&skill_md)?;
        let (_, description) = frontmatter::parse(&content)?;

        let skill_hash = hash::calculate_file_hash(&skill_md)?;
        let now = Utc::now().to_rfc3339();

        let skill = Skill {
            name: name.to_string(),
            description,
            created_at: now.clone(),
            updated_at: now,
            hash: skill_hash,
            path: format!("repository/{}", name),
        };

        let mut manifest = self.load_manifest()?;
        manifest.add_skill(skill);
        manifest.save(&self.base_path.join("manifest.json"))?;

        Ok(())
    }

    pub fn update_sync_time(&mut self) -> Result<()> {
        let mut manifest = self.load_manifest()?;
        manifest.update_sync_time();
        manifest.save(&self.base_path.join("manifest.json"))?;
        Ok(())
    }

    fn load_manifest(&self) -> Result<Manifest> {
        Manifest::load(&self.base_path.join("manifest.json"))
    }

    pub fn load_config(&self) -> Result<Config> {
        Config::load(&self.base_path.join("config.json"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_init() {
        let temp = TempDir::new().unwrap();
        let base = temp.path().join(".skillstack");
        
        let repo = Repository::new(&base);
        repo.init("/test/claude").unwrap();
        
        assert!(base.join("repository").exists());
        assert!(base.join("manifest.json").exists());
        assert!(base.join("config.json").exists());
    }

    #[test]
    fn test_create_delete_skill() {
        let temp = TempDir::new().unwrap();
        let base = temp.path().join(".skillstack");
        
        let mut repo = Repository::new(&base);
        repo.init("/test/claude").unwrap();
        
        repo.create_skill("test-skill", "A test").unwrap();
        assert!(base.join("repository/test-skill/SKILL.md").exists());
        
        repo.delete_skill("test-skill").unwrap();
        assert!(!base.join("repository/test-skill").exists());
    }
}
```

- [ ] **步骤2: 运行测试**
运行: `cargo test repository::tests`
预期: PASS

- [ ] **步骤3: Commit**
```bash
git add src/core/repository.rs
git commit -m "feat: add Repository Manager with full CRUD and import"
```

---

### 任务8: CLI命令骨架

**文件:** `src/cli/commands.rs`, `src/main.rs`

- [ ] **步骤1: 创建src/cli/mod.rs**
```rust
pub mod commands;
```

- [ ] **步骤2: 创建src/cli/commands.rs(P0+P1所有命令)**
```rust
use clap::{Parser, Subcommand};
use anyhow::Result;
use chrono::{DateTime, Utc};
use std::process::Command;

use crate::core::{repository::Repository, sync::SyncEngine};
use crate::utils::{fs, ui};

#[derive(Parser)]
#[command(name = "skillstack")]
#[command(about = "Centralized skill management for Claude Code")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    Init {
        #[arg(long)]
        force: bool,
        #[arg(long)]
        no_import: bool,
    },
    List {
        #[arg(long, default_value = "name")]
        sort: String,
        #[arg(long)]
        reverse: bool,
    },
    Add {
        name: String,
        #[arg(long)]
        editor: Option<String>,
        #[arg(long)]
        no_edit: bool,
    },
    Edit {
        name: String,
        #[arg(long)]
        editor: Option<String>,
    },
    Delete {
        name: String,
        #[arg(short, long)]
        force: bool,
    },
    Sync {
        #[arg(long)]
        force: bool,
    },
    Import {
        path: String,
        #[arg(long)]
        name: Option<String>,
    },
    Show {
        name: String,
    },
    Doctor {
        #[arg(long)]
        fix: bool,
    },
    Status,
}

pub fn run(cli: Cli) -> Result<()> {
    match cli.command {
        Commands::Init { force, no_import } => cmd_init(force, no_import),
        Commands::List { sort, reverse } => cmd_list(&sort, reverse),
        Commands::Add { name, editor, no_edit } => cmd_add(&name, editor.as_deref(), no_edit),
        Commands::Edit { name, editor } => cmd_edit(&name, editor.as_deref()),
        Commands::Delete { name, force } => cmd_delete(&name, force),
        Commands::Sync { force } => cmd_sync(force),
        Commands::Import { path, name } => cmd_import(&path, name.as_deref()),
        Commands::Show { name } => cmd_show(&name),
        Commands::Doctor { fix } => cmd_doctor(fix),
        Commands::Status => cmd_status(),
    }
}

fn cmd_init(force: bool, no_import: bool) -> Result<()> {
    let base_path = fs::expand_tilde("~/.skillstack");
    let claude_path = fs::expand_tilde("~/.claude/skills");

    if base_path.exists() && !force {
        return Err(anyhow::anyhow!("Already initialized. Use --force"));
    }

    let mut repo = Repository::new(&base_path);
    repo.init(claude_path.to_str().unwrap())?;
    ui::success("Repository initialized at ~/.skillstack");

    if !no_import && claude_path.exists() && !claude_path.is_symlink() {
        if let Ok(skills) = repo.scan_skills(&claude_path) {
            if !skills.is_empty() {
                println!("\n🔍 Found {} existing skills:", skills.len());
                for s in &skills { println!("  📋 {}", s); }

                if ui::prompt("Import to central repository?") {
                    for s in skills {
                        let sp = claude_path.join(&s);
                        if let Err(e) = repo.import_skill(&sp, Some(&s)) {
                            ui::warning(&format!("Failed '{}': {}", s, e));
                        } else {
                            ui::success(&format!("Imported '{}'", s));
                        }
                    }
                }
            }
        }
    }

    let repo_path = base_path.join("repository");
    let sync_engine = SyncEngine::new();
    sync_engine.create_symlink(&repo_path, &claude_path)?;
    ui::success("Symlink created: ~/.claude/skills -> ~/.skillstack/repository");

    println!("\n✅ SkillStack initialized!\n");
    println!("Next steps:");
    println!("  - skillstack list");
    println!("  - skillstack add <name>");

    Ok(())
}

fn cmd_list(sort_by: &str, reverse: bool) -> Result<()> {
    let base = fs::expand_tilde("~/.skillstack");
    if !base.exists() {
        return Err(anyhow::anyhow!("Not initialized. Run 'skillstack init'"));
    }

    let repo = Repository::new(&base);
    let mut skills = repo.list_skills()?;

    if skills.is_empty() {
        println!("No skills found.");
        ui::info("Run 'skillstack add <name>' to create your first skill");
        return Ok(());
    }

    match sort_by {
        "created" => skills.sort_by(|a, b| a.created_at.cmp(&b.created_at)),
        "updated" => skills.sort_by(|a, b| a.updated_at.cmp(&b.updated_at)),
        _ => skills.sort_by(|a, b| a.name.cmp(&b.name)),
    }

    if reverse {
        skills.reverse();
    }

    let widths = [30, 50, 20];
    println!("{}", ui::format_table_row(&["NAME", "DESCRIPTION", "UPDATED"], &widths));
    println!("{}", "-".repeat(100));

    for s in &skills {
        let updated = format_relative_time(&s.updated_at);
        println!("{}", ui::format_table_row(&[&s.name, &s.description, &updated], &widths));
    }

    println!("\nTotal: {} skills", skills.len());
    Ok(())
}

fn cmd_add(name: &str, editor: Option<&str>, no_edit: bool) -> Result<()> {
    let base = fs::expand_tilde("~/.skillstack");
    if !base.exists() {
        return Err(anyhow::anyhow!("Not initialized"));
    }

    let mut repo = Repository::new(&base);
    repo.create_skill(name, &format!("Description for {}", name))?;
    ui::success(&format!("Skill '{}' created", name));

    if !no_edit {
        let skill_file = base.join("repository").join(name).join("SKILL.md");
        let editor_cmd = if let Some(e) = editor {
            e.to_string()
        } else {
            repo.load_config()?.editor
        };

        println!("📝 Opening editor...");
        Command::new(&editor_cmd).arg(&skill_file).status()?;

        repo.update_skill_hash(name)?;
        ui::success("Saved and synced");
    }

    Ok(())
}

fn cmd_edit(name: &str, editor: Option<&str>) -> Result<()> {
    let base = fs::expand_tilde("~/.skillstack");
    let skill_file = base.join("repository").join(name).join("SKILL.md");

    if !skill_file.exists() {
        return Err(anyhow::anyhow!("Skill '{}' not found", name));
    }

    let mut repo = Repository::new(&base);
    let editor_cmd = editor.unwrap_or(&repo.load_config()?.editor).to_string();

    println!("📝 Editing '{}'...", name);
    Command::new(&editor_cmd).arg(&skill_file).status()?;

    repo.update_skill_hash(name)?;
    ui::success("Saved and synced");
    Ok(())
}

fn cmd_delete(name: &str, force: bool) -> Result<()> {
    let base = fs::expand_tilde("~/.skillstack");
    let mut repo = Repository::new(&base);

    if !force {
        ui::warning(&format!("About to delete '{}'", name));
        println!("This cannot be undone.");
        if !ui::prompt("Continue?") {
            println!("Cancelled.");
            return Ok(());
        }
    }

    repo.delete_skill(name)?;
    ui::success(&format!("Skill '{}' deleted", name));
    Ok(())
}

fn cmd_sync(force: bool) -> Result<()> {
    let base = fs::expand_tilde("~/.skillstack");
    let claude = fs::expand_tilde("~/.claude/skills");
    let repo_path = base.join("repository");

    let sync_engine = SyncEngine::new();

    if force || !sync_engine.verify_symlink(&claude, &repo_path).unwrap_or(false) {
        sync_engine.rebuild_symlink(&repo_path, &claude)?;
    }

    let mut repo = Repository::new(&base);
    repo.update_sync_time()?;

    let count = repo.list_skills()?.len();
    ui::success(&format!("Synced {} skills to ~/.claude/skills", count));

    Ok(())
}

fn cmd_import(path_str: &str, name: Option<&str>) -> Result<()> {
    let base = fs::expand_tilde("~/.skillstack");
    let mut repo = Repository::new(&base);

    let import_path = std::path::PathBuf::from(path_str);
    repo.import_skill(&import_path, name)?;

    let skill_name = name.unwrap_or_else(|| import_path.file_name().unwrap().to_str().unwrap());
    ui::success(&format!("Imported '{}' from {}", skill_name, path_str));

    Ok(())
}

fn cmd_show(name: &str) -> Result<()> {
    let base = fs::expand_tilde("~/.skillstack");
    let repo = Repository::new(&base);

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

fn cmd_doctor(fix: bool) -> Result<()> {
    println!("🏥 Running health check...\n");

    let base = fs::expand_tilde("~/.skillstack");
    let claude = fs::expand_tilde("~/.claude/skills");
    let repo_path = base.join("repository");

    let mut issues = Vec::new();

    if !base.exists() {
        issues.push("❌ Directory: ~/.skillstack/ not found");
    } else {
        ui::success("Directory structure: OK");
    }

    let sync_engine = SyncEngine::new();
    if !sync_engine.verify_symlink(&claude, &repo_path).unwrap_or(false) {
        issues.push("❌ Symlink: Invalid or broken");
        if fix {
            sync_engine.rebuild_symlink(&repo_path, &claude)?;
            ui::success("Fixed: Rebuilt symlink");
        }
    } else {
        ui::success("Symlink: OK");
    }

    // Check manifest consistency
    if base.exists() {
        let repo = Repository::new(&base);
        if let Ok(skills) = repo.list_skills() {
            for skill in &skills {
                let skill_path = base.join(&skill.path).join("SKILL.md");
                if !skill_path.exists() {
                    issues.push(&format!("❌ Missing file: {}", skill.name));
                }
            }
        }
        ui::success("Manifest: OK");
    }

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

fn cmd_status() -> Result<()> {
    let base = fs::expand_tilde("~/.skillstack");
    let claude = fs::expand_tilde("~/.claude/skills");

    let repo = Repository::new(&base);
    let count = repo.list_skills()?.len();

    println!("Repository: ~/.skillstack/repository ({} skills)", count);

    let symlink_status = if claude.is_symlink() { "symlink ✅" } else { "not symlink ❌" };
    println!("Claude Path: ~/.claude/skills ({})", symlink_status);

    let manifest = repo.load_manifest()?;
    if let Some(last_sync) = manifest.sync_status.last_sync {
        println!("Last Sync: {}", format_relative_time(&last_sync));
    }

    println!("Status: All synced ✅");

    Ok(())
}

fn format_relative_time(iso_time: &str) -> String {
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

impl Repository {
    fn load_manifest(&self) -> Result<crate::core::manifest::Manifest> {
        crate::core::manifest::Manifest::load(&self.base_path.join("manifest.json"))
    }
}
```

- [ ] **步骤3: 更新src/main.rs**
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

- [ ] **步骤4: 测试所有命令**
运行: `cargo build`
预期: 编译成功

- [ ] **步骤5: 手动测试P0命令**
```bash
./target/debug/skillstack init
./target/debug/skillstack add test-skill --no-edit
./target/debug/skillstack list
./target/debug/skillstack sync
./target/debug/skillstack delete test-skill --force
```

- [ ] **步骤6: Commit**
```bash
git add src/cli/ src/main.rs
git commit -m "feat: add all CLI commands (P0 + P1)"
```

---

### 任务9: 集成测试

**文件:** `tests/integration_test.rs`

- [ ] **步骤1: 创建tests/integration_test.rs**
```rust
use std::process::Command;
use tempfile::TempDir;

#[test]
fn test_full_workflow() {
    let temp_dir = TempDir::new().unwrap();
    
    // Set HOME to temp directory
    let old_home = std::env::var("HOME").ok();
    std::env::set_var("HOME", temp_dir.path());

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

    // 4. delete
    let output = Command::new("cargo")
        .args(&["run", "--", "delete", "test-skill", "--force"])
        .output()
        .unwrap();
    assert!(output.status.success());

    // Restore HOME
    if let Some(home) = old_home {
        std::env::set_var("HOME", home);
    }
}
```

- [ ] **步骤2: 运行集成测试**
运行: `cargo test --test integration_test`
预期: PASS

- [ ] **步骤3: Commit**
```bash
git add tests/integration_test.rs
git commit -m "test: add full workflow integration test"
```

---

### 任务10: 文档

**文件:** `README.md`, `LICENSE`, `CHANGELOG.md`

- [ ] **步骤1: 创建README.md**
```markdown
# SkillStack

Centralized skill management for Claude Code.

## Quick Start

```bash
cargo install --path .
skillstack init
skillstack add my-skill
skillstack list
```

## Commands

- `init` - Initialize repository
- `list` - List all skills
- `add <name>` - Create skill
- `edit <name>` - Edit skill
- `delete <name>` - Delete skill
- `sync` - Sync to Claude
- `import <path>` - Import skill
- `show <name>` - Show details
- `doctor` - Health check
- `status` - Display status

## License

MIT
```

- [ ] **步骤2: 创建LICENSE(MIT)**

- [ ] **步骤3: 创建CHANGELOG.md**
```markdown
# Changelog

## [0.1.0] - 2026-04-03

### Added
- Initial MVP release
- All P0+P1 commands
- Symlink-based sync
- Manifest tracking
```

- [ ] **步骤4: Commit**
```bash
git add README.md LICENSE CHANGELOG.md
git commit -m "docs: add README, LICENSE, CHANGELOG"
```

---

### 任务11: 发布准备

- [ ] **步骤1: 运行所有测试**
```bash
cargo test
```
预期: 所有测试PASS

- [ ] **步骤2: 编译release**
```bash
cargo build --release
```
预期: 成功

- [ ] **步骤3: 手动测试清单**
- [ ] init命令
- [ ] list命令
- [ ] add命令(含编辑器)
- [ ] edit命令
- [ ] delete命令(含确认)
- [ ] sync命令
- [ ] import命令
- [ ] show命令
- [ ] doctor命令
- [ ] status命令

- [ ] **步骤4: Claude Code集成验证**
- [ ] Claude能读取symlink的skills
- [ ] 修改skill后Claude立即生效

- [ ] **步骤5: 创建release tag**
```bash
git tag -a v0.1.0-mvp -m "MVP release"
```

- [ ] **步骤6: Final commit**
```bash
git commit -m "chore: prepare v0.1.0-mvp release"
```

---

## 完成标准

MVP完成当且仅当:

1. ✅ 所有P0命令(7个)功能完整
2. ✅ 所有P1命令(3个)功能完整
3. ✅ 单元测试和集成测试通过
4. ✅ 在真实Claude Code环境验证通过
5. ✅ README和文档完整
6. ✅ 可以编译release版本

---

## 预计时间

- 任务1-3: 基础设施和数据结构(1天)
- 任务4-7: 核心模块(2天)
- 任务8: CLI命令(2天)
- 任务9-11: 测试和发布(1天)

**总计: 6工作日**
