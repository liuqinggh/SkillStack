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
