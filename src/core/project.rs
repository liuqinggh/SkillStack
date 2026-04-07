use anyhow::{anyhow, Result};
use chrono::Utc;
use std::fs;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

use super::manifest::{Manifest, Project, SkillOverride};
use crate::utils::{fs as fs_utils, hash};

pub struct ProjectManager {
    base_path: PathBuf,
}

impl ProjectManager {
    pub fn new(base_path: &Path) -> Self {
        Self {
            base_path: base_path.to_path_buf(),
        }
    }

    /// Register a new project
    pub fn register_project(
        &mut self,
        path: &str,
        name: Option<&str>,
        tool: &str,
    ) -> Result<String> {
        let project_path = PathBuf::from(path);

        if !project_path.exists() {
            return Err(anyhow!("Project path does not exist: {}", path));
        }

        let project_name = if let Some(n) = name {
            n.to_string()
        } else {
            project_path
                .file_name()
                .and_then(|n| n.to_str())
                .ok_or_else(|| anyhow!("Cannot infer project name from path"))?
                .to_string()
        };

        let mut manifest = self.load_manifest()?;

        if manifest.get_project(&project_name).is_some() {
            return Err(anyhow!("Project '{}' already registered", project_name));
        }

        let project = Project {
            name: project_name.clone(),
            path: path.to_string(),
            tool: tool.to_string(),
            registered_at: Utc::now().to_rfc3339(),
            installed_skills: vec![],
            overrides: std::collections::HashMap::new(),
        };

        manifest.add_project(project);
        manifest.save(&self.base_path.join("manifest.json"))?;

        Ok(project_name)
    }

    /// Unregister a project
    pub fn unregister_project(&mut self, name: &str) -> Result<()> {
        let mut manifest = self.load_manifest()?;

        if manifest.get_project(name).is_none() {
            return Err(anyhow!("Project '{}' not found", name));
        }

        manifest.remove_project(name);
        manifest.save(&self.base_path.join("manifest.json"))?;

        Ok(())
    }

    /// List all registered projects
    pub fn list_projects(&self) -> Result<Vec<Project>> {
        let manifest = self.load_manifest()?;
        let mut projects: Vec<Project> = manifest.list_projects().into_iter().cloned().collect();
        projects.sort_by(|a, b| a.name.cmp(&b.name));
        Ok(projects)
    }

    /// Get a specific project
    pub fn get_project(&self, name: &str) -> Result<Project> {
        let manifest = self.load_manifest()?;
        manifest
            .get_project(name)
            .cloned()
            .ok_or_else(|| anyhow!("Project '{}' not found", name))
    }

    /// Scan a directory for projects and auto-register them
    pub fn scan_and_register(&mut self, scan_dir: &str, tool: &str) -> Result<Vec<String>> {
        let scan_path = PathBuf::from(scan_dir);

        if !scan_path.exists() {
            return Err(anyhow!("Scan directory does not exist: {}", scan_dir));
        }

        let mut registered_projects = Vec::new();

        // Recursively scan for projects (up to depth 3)
        for entry in WalkDir::new(&scan_path).max_depth(3) {
            let entry = match entry {
                Ok(e) => e,
                Err(_) => continue,
            };

            // Check if this directory has .{tool}/skills/ subdirectory
            if entry.file_type().is_dir() {
                let skills_dir = entry.path().join(format!(".{}", tool)).join("skills");

                if skills_dir.exists() && skills_dir.is_dir() {
                    let project_path = entry.path();

                    // Skip if it's the scan directory itself
                    if project_path == scan_path {
                        continue;
                    }

                    // Infer project name from directory name
                    let project_name = project_path
                        .file_name()
                        .and_then(|n| n.to_str())
                        .unwrap_or("unknown")
                        .to_string();

                    // Try to register (skip if already registered)
                    match self.register_project(
                        project_path.to_str().unwrap(),
                        Some(&project_name),
                        tool,
                    ) {
                        Ok(name) => {
                            registered_projects.push(name);
                        }
                        Err(e) => {
                            // Skip already registered projects
                            if e.to_string().contains("already registered") {
                                continue;
                            }
                            // Log other errors but continue scanning
                            eprintln!("Warning: Failed to register '{}': {}", project_name, e);
                        }
                    }
                }
            }
        }

        Ok(registered_projects)
    }

    /// Scan skills in a project directory
    pub fn scan_project_skills(&self, project_name: &str) -> Result<Vec<String>> {
        let manifest = self.load_manifest()?;
        let project = manifest
            .get_project(project_name)
            .ok_or_else(|| anyhow!("Project '{}' not found", project_name))?;

        let skills_dir = PathBuf::from(&project.path)
            .join(format!(".{}", &project.tool))
            .join("skills");

        if !skills_dir.exists() {
            return Ok(vec![]);
        }

        let mut skills = Vec::new();
        for entry in WalkDir::new(&skills_dir).max_depth(2) {
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

    /// Install a skill to a project
    pub fn install_skill(&mut self, project_name: &str, skill_name: &str) -> Result<()> {
        let mut manifest = self.load_manifest()?;

        // Verify project exists
        let project = manifest
            .get_project(project_name)
            .ok_or_else(|| anyhow!("Project '{}' not found", project_name))?
            .clone();

        // Verify skill exists in global repository
        if manifest.get_skill(skill_name).is_none() {
            return Err(anyhow!("Skill '{}' not found in global repository", skill_name));
        }

        // Check if already installed
        if project.installed_skills.contains(&skill_name.to_string()) {
            return Err(anyhow!(
                "Skill '{}' already installed in project '{}'",
                skill_name,
                project_name
            ));
        }

        // Copy skill to project
        let source_path = self.base_path.join("repository").join(skill_name);
        let dest_path = PathBuf::from(&project.path)
            .join(format!(".{}", &project.tool))
            .join("skills")
            .join(skill_name);

        fs_utils::copy_dir_recursive(&source_path, &dest_path)?;

        // Update manifest
        if let Some(proj) = manifest.get_project_mut(project_name) {
            proj.installed_skills.push(skill_name.to_string());
        }

        manifest.save(&self.base_path.join("manifest.json"))?;

        Ok(())
    }

    /// Uninstall a skill from a project
    pub fn uninstall_skill(&mut self, project_name: &str, skill_name: &str) -> Result<()> {
        let mut manifest = self.load_manifest()?;

        let project = manifest
            .get_project(project_name)
            .ok_or_else(|| anyhow!("Project '{}' not found", project_name))?
            .clone();

        if !project.installed_skills.contains(&skill_name.to_string()) {
            return Err(anyhow!(
                "Skill '{}' not installed in project '{}'",
                skill_name,
                project_name
            ));
        }

        // Remove skill directory from project
        let skill_path = PathBuf::from(&project.path)
            .join(format!(".{}", &project.tool))
            .join("skills")
            .join(skill_name);

        if skill_path.exists() {
            fs::remove_dir_all(&skill_path)?;
        }

        // Update manifest
        if let Some(proj) = manifest.get_project_mut(project_name) {
            proj.installed_skills.retain(|s| s != skill_name);
            proj.overrides.remove(skill_name);
        }

        manifest.save(&self.base_path.join("manifest.json"))?;

        Ok(())
    }

    /// Detect overrides in a project
    pub fn detect_overrides(&mut self, project_name: &str) -> Result<Vec<String>> {
        let mut manifest = self.load_manifest()?;

        let project = manifest
            .get_project(project_name)
            .ok_or_else(|| anyhow!("Project '{}' not found", project_name))?
            .clone();

        let mut overrides = Vec::new();

        for skill_name in &project.installed_skills {
            // Get global skill hash
            let global_skill = match manifest.get_skill(skill_name) {
                Some(s) => s,
                None => continue, // Skip if not in global repository
            };

            // Get project skill hash
            let project_skill_path = PathBuf::from(&project.path)
                .join(format!(".{}", &project.tool))
                .join("skills")
                .join(skill_name)
                .join("SKILL.md");

            if !project_skill_path.exists() {
                continue;
            }

            let project_hash = hash::calculate_file_hash(&project_skill_path)?;

            // Compare hashes
            if project_hash != global_skill.hash {
                overrides.push(skill_name.clone());

                // Record override in manifest
                if let Some(proj) = manifest.get_project_mut(project_name) {
                    proj.overrides.insert(
                        skill_name.clone(),
                        SkillOverride {
                            hash: project_hash,
                            updated_at: Utc::now().to_rfc3339(),
                        },
                    );
                }
            }
        }

        manifest.save(&self.base_path.join("manifest.json"))?;

        Ok(overrides)
    }

    fn load_manifest(&self) -> Result<Manifest> {
        Manifest::load(&self.base_path.join("manifest.json"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_register_unregister_project() {
        let temp_dir = TempDir::new().unwrap();
        let base = temp_dir.path().join(".skillstack");
        let project_dir = temp_dir.path().join("my-project");

        // Setup
        fs::create_dir_all(&base.join("repository")).unwrap();
        fs::create_dir_all(&project_dir).unwrap();

        let manifest = Manifest::new("/test");
        manifest.save(&base.join("manifest.json")).unwrap();

        let mut pm = ProjectManager::new(&base);

        // Test register
        let name = pm
            .register_project(project_dir.to_str().unwrap(), None, "claude")
            .unwrap();
        assert_eq!(name, "my-project");

        let projects = pm.list_projects().unwrap();
        assert_eq!(projects.len(), 1);
        assert_eq!(projects[0].name, "my-project");

        // Test unregister
        pm.unregister_project("my-project").unwrap();
        let projects = pm.list_projects().unwrap();
        assert!(projects.is_empty());
    }

    #[test]
    fn test_register_duplicate_fails() {
        let temp_dir = TempDir::new().unwrap();
        let base = temp_dir.path().join(".skillstack");
        let project_dir = temp_dir.path().join("test-proj");

        fs::create_dir_all(&base.join("repository")).unwrap();
        fs::create_dir_all(&project_dir).unwrap();

        let manifest = Manifest::new("/test");
        manifest.save(&base.join("manifest.json")).unwrap();

        let mut pm = ProjectManager::new(&base);

        pm.register_project(project_dir.to_str().unwrap(), Some("test-proj"), "claude")
            .unwrap();

        let result = pm.register_project(project_dir.to_str().unwrap(), Some("test-proj"), "claude");
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("already registered"));
    }

    #[test]
    fn test_list_projects_sorted() {
        let temp_dir = TempDir::new().unwrap();
        let base = temp_dir.path().join(".skillstack");

        fs::create_dir_all(&base.join("repository")).unwrap();

        let manifest = Manifest::new("/test");
        manifest.save(&base.join("manifest.json")).unwrap();

        let mut pm = ProjectManager::new(&base);

        // Register projects in non-alphabetical order
        for name in &["zebra", "apple", "middle"] {
            let dir = temp_dir.path().join(name);
            fs::create_dir_all(&dir).unwrap();
            pm.register_project(dir.to_str().unwrap(), Some(name), "claude")
                .unwrap();
        }

        let projects = pm.list_projects().unwrap();
        assert_eq!(projects.len(), 3);
        assert_eq!(projects[0].name, "apple");
        assert_eq!(projects[1].name, "middle");
        assert_eq!(projects[2].name, "zebra");
    }
}
