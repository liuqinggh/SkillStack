use anyhow::Result;
use serde::{Deserialize, Serialize};
use skillstack::core::{
    repository::Repository,
    project::ProjectManager,
    manifest::Manifest,
};
use skillstack::utils::fs;

// ============================================================================
// Types
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillInfo {
    pub name: String,
    pub description: String,
    pub created_at: String,
    pub updated_at: String,
    pub hash: String,
    pub path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectInfo {
    pub name: String,
    pub path: String,
    pub tool: String,
    pub registered_at: String,
    pub installed_skills: Vec<String>,
    pub skill_count: usize,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DashboardStats {
    pub total_skills: usize,
    pub total_projects: usize,
    pub synced_today: usize,
}

// ============================================================================
// Skill Commands
// ============================================================================

#[tauri::command]
pub async fn get_skills() -> Result<Vec<SkillInfo>, String> {
    let base = fs::expand_tilde("~/.skillstack");
    let repo = Repository::new(&base);

    let skills = repo.list_skills().map_err(|e| e.to_string())?;

    let skill_infos: Vec<SkillInfo> = skills.iter().map(|skill| SkillInfo {
        name: skill.name.clone(),
        description: skill.description.clone(),
        created_at: skill.created_at.clone(),
        updated_at: skill.updated_at.clone(),
        hash: skill.hash.clone(),
        path: base.join("repository").join(&skill.name).to_string_lossy().to_string(),
    }).collect();

    Ok(skill_infos)
}

#[tauri::command]
pub async fn get_skill(name: String) -> Result<SkillInfo, String> {
    let base = fs::expand_tilde("~/.skillstack");
    let manifest = Manifest::load(&base.join("manifest.json"))
        .map_err(|e| e.to_string())?;

    let skill = manifest.skills.get(&name)
        .ok_or_else(|| format!("Skill '{}' not found", name))?;

    Ok(SkillInfo {
        name: name.clone(),
        description: skill.description.clone(),
        created_at: skill.created_at.clone(),
        updated_at: skill.updated_at.clone(),
        hash: skill.hash.clone(),
        path: base.join("repository").join(&name).to_string_lossy().to_string(),
    })
}

#[tauri::command]
pub async fn create_skill(name: String, description: Option<String>) -> Result<(), String> {
    let base = fs::expand_tilde("~/.skillstack");
    let mut repo = Repository::new(&base);

    let desc = description.unwrap_or_else(|| format!("Description for {}", name));
    repo.create_skill(&name, &desc)
        .map_err(|e| e.to_string())?;

    Ok(())
}

#[tauri::command]
pub async fn delete_skill(name: String) -> Result<(), String> {
    let base = fs::expand_tilde("~/.skillstack");
    let mut repo = Repository::new(&base);

    repo.delete_skill(&name)
        .map_err(|e| e.to_string())?;

    Ok(())
}

// ============================================================================
// Project Commands
// ============================================================================

#[tauri::command]
pub async fn get_projects() -> Result<Vec<ProjectInfo>, String> {
    let base = fs::expand_tilde("~/.skillstack");
    let pm = ProjectManager::new(&base);

    let projects = pm.list_projects().map_err(|e| e.to_string())?;

    let project_infos: Vec<ProjectInfo> = projects.iter().map(|p| ProjectInfo {
        name: p.name.clone(),
        path: p.path.clone(),
        tool: p.tool.clone(),
        registered_at: p.registered_at.clone(),
        installed_skills: p.installed_skills.clone(),
        skill_count: p.installed_skills.len(),
    }).collect();

    Ok(project_infos)
}

#[tauri::command]
pub async fn get_project(name: String) -> Result<ProjectInfo, String> {
    let base = fs::expand_tilde("~/.skillstack");
    let pm = ProjectManager::new(&base);

    let project = pm.get_project(&name).map_err(|e| e.to_string())?;

    Ok(ProjectInfo {
        name: project.name.clone(),
        path: project.path.clone(),
        tool: project.tool.clone(),
        registered_at: project.registered_at.clone(),
        installed_skills: project.installed_skills.clone(),
        skill_count: project.installed_skills.len(),
    })
}

#[tauri::command]
pub async fn register_project(
    path: String,
    name: Option<String>,
    tool: String,
) -> Result<(), String> {
    let base = fs::expand_tilde("~/.skillstack");
    let mut pm = ProjectManager::new(&base);

    pm.register_project(&path, name.as_deref(), &tool)
        .map_err(|e| e.to_string())?;

    Ok(())
}

#[tauri::command]
pub async fn unregister_project(name: String) -> Result<(), String> {
    let base = fs::expand_tilde("~/.skillstack");
    let mut pm = ProjectManager::new(&base);

    pm.unregister_project(&name)
        .map_err(|e| e.to_string())?;

    Ok(())
}

#[tauri::command]
pub async fn install_skill_to_project(
    skill_name: String,
    project_name: String,
) -> Result<(), String> {
    let base = fs::expand_tilde("~/.skillstack");
    let mut pm = ProjectManager::new(&base);

    pm.install_skill(&project_name, &skill_name)
        .map_err(|e| e.to_string())?;

    Ok(())
}

#[tauri::command]
pub async fn uninstall_skill_from_project(
    skill_name: String,
    project_name: String,
) -> Result<(), String> {
    let base = fs::expand_tilde("~/.skillstack");
    let mut pm = ProjectManager::new(&base);

    pm.uninstall_skill(&project_name, &skill_name)
        .map_err(|e| e.to_string())?;

    Ok(())
}

// ============================================================================
// Dashboard Commands
// ============================================================================

#[tauri::command]
pub async fn get_dashboard_stats() -> Result<DashboardStats, String> {
    let base = fs::expand_tilde("~/.skillstack");
    let repo = Repository::new(&base);
    let pm = ProjectManager::new(&base);

    let skills = repo.list_skills().map_err(|e| e.to_string())?;
    let projects = pm.list_projects().map_err(|e| e.to_string())?;

    // TODO: Calculate actual synced_today count from sync history
    let synced_today = 0;

    Ok(DashboardStats {
        total_skills: skills.len(),
        total_projects: projects.len(),
        synced_today,
    })
}

// ============================================================================
// Utility Commands
// ============================================================================

#[tauri::command]
pub async fn check_initialized() -> Result<bool, String> {
    let base = fs::expand_tilde("~/.skillstack");
    Ok(base.exists())
}

#[tauri::command]
pub async fn initialize_skillstack() -> Result<(), String> {
    let base_path = fs::expand_tilde("~/.skillstack");
    let claude_path = fs::expand_tilde("~/.claude/skills");

    let repo = Repository::new(&base_path);
    repo.init(claude_path.to_str().unwrap())
        .map_err(|e| e.to_string())?;

    Ok(())
}

#[tauri::command]
pub async fn open_skill_in_editor(name: String) -> Result<(), String> {
    let base = fs::expand_tilde("~/.skillstack");
    let skill_path = base.join("repository").join(&name).join("SKILL.md");

    if !skill_path.exists() {
        return Err(format!("Skill '{}' not found", name));
    }

    // Open in default editor
    // This is platform-specific and should use tauri-plugin-opener
    Ok(())
}
