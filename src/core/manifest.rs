use anyhow::Result;
use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use super::skill::Skill;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillOverride {
    pub hash: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Project {
    pub name: String,
    pub path: String,
    pub tool: String,
    pub registered_at: String,
    pub installed_skills: Vec<String>,
    pub overrides: HashMap<String, SkillOverride>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Manifest {
    pub version: String,
    pub skills: HashMap<String, Skill>,
    pub sync_status: SyncStatus,
    #[serde(default)]
    pub projects: HashMap<String, Project>,
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
            projects: HashMap::new(),
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

    // Project management methods
    pub fn add_project(&mut self, project: Project) {
        self.projects.insert(project.name.clone(), project);
    }

    pub fn remove_project(&mut self, name: &str) -> Option<Project> {
        self.projects.remove(name)
    }

    pub fn get_project(&self, name: &str) -> Option<&Project> {
        self.projects.get(name)
    }

    pub fn get_project_mut(&mut self, name: &str) -> Option<&mut Project> {
        self.projects.get_mut(name)
    }

    pub fn list_projects(&self) -> Vec<&Project> {
        self.projects.values().collect()
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
        assert!(m.projects.is_empty());
    }

    #[test]
    fn test_manifest_save_load() {
        let temp_dir = TempDir::new().unwrap();
        let path = temp_dir.path().join("manifest.json");

        let m = Manifest::new("/test");
        m.save(&path).unwrap();

        let loaded = Manifest::load(&path).unwrap();
        assert_eq!(loaded.version, "1.0");
        assert!(loaded.projects.is_empty());
    }

    #[test]
    fn test_add_remove_project() {
        let mut m = Manifest::new("/test");

        let project = Project {
            name: "test-project".to_string(),
            path: "/test/path".to_string(),
            tool: "claude".to_string(),
            registered_at: Utc::now().to_rfc3339(),
            installed_skills: vec![],
            overrides: HashMap::new(),
        };

        m.add_project(project);
        assert_eq!(m.projects.len(), 1);
        assert!(m.get_project("test-project").is_some());

        m.remove_project("test-project");
        assert!(m.projects.is_empty());
    }

    #[test]
    fn test_project_save_load() {
        let temp_dir = TempDir::new().unwrap();
        let path = temp_dir.path().join("manifest.json");

        let mut m = Manifest::new("/test");
        let project = Project {
            name: "my-app".to_string(),
            path: "/path/to/app".to_string(),
            tool: "claude".to_string(),
            registered_at: Utc::now().to_rfc3339(),
            installed_skills: vec!["skill-a".to_string()],
            overrides: HashMap::new(),
        };
        m.add_project(project);

        m.save(&path).unwrap();
        let loaded = Manifest::load(&path).unwrap();

        assert_eq!(loaded.projects.len(), 1);
        let proj = loaded.get_project("my-app").unwrap();
        assert_eq!(proj.path, "/path/to/app");
        assert_eq!(proj.installed_skills.len(), 1);
    }
}
