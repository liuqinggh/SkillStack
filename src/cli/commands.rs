use clap::{Parser, Subcommand};
use anyhow::Result;
use chrono::{DateTime, Utc};
use std::process::Command;

use crate::core::{repository::Repository, sync::SyncEngine, project::ProjectManager};
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
    Project {
        #[command(subcommand)]
        command: ProjectCommands,
    },
    Install {
        skill_name: String,
        #[arg(long)]
        project: String,
    },
    Uninstall {
        skill_name: String,
        #[arg(long)]
        project: String,
    },
}

#[derive(Subcommand)]
pub enum ProjectCommands {
    Add {
        path: String,
        #[arg(long)]
        name: Option<String>,
        #[arg(long, default_value = "claude")]
        tool: String,
        #[arg(long)]
        scan_skills: bool,
    },
    List {
        #[arg(long, default_value = "name")]
        sort: String,
        #[arg(long)]
        reverse: bool,
    },
    Remove {
        name: String,
        #[arg(short, long)]
        force: bool,
    },
    Sync {
        project_name: Option<String>,
        #[arg(long)]
        all_projects: bool,
        #[arg(long)]
        skills: Option<Vec<String>>,
        #[arg(long)]
        force: bool,
        #[arg(long)]
        dry_run: bool,
    },
    DetectOverrides {
        project_name: Option<String>,
        #[arg(long)]
        all_projects: bool,
    },
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
        Commands::Project { command } => match command {
            ProjectCommands::Add { path, name, tool, scan_skills } => {
                cmd_project_add(&path, name.as_deref(), &tool, scan_skills)
            }
            ProjectCommands::List { sort, reverse } => {
                cmd_project_list(&sort, reverse)
            }
            ProjectCommands::Remove { name, force } => {
                cmd_project_remove(&name, force)
            }
            ProjectCommands::Sync { project_name, all_projects, skills, force, dry_run } => {
                cmd_project_sync(project_name.as_deref(), all_projects, skills.as_deref(), force, dry_run)
            }
            ProjectCommands::DetectOverrides { project_name, all_projects } => {
                cmd_project_detect_overrides(project_name.as_deref(), all_projects)
            }
        },
        Commands::Install { skill_name, project } => {
            cmd_install(&skill_name, &project)
        }
        Commands::Uninstall { skill_name, project } => {
            cmd_uninstall(&skill_name, &project)
        }
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

    let mut issues: Vec<String> = Vec::new();

    if !base.exists() {
        issues.push("❌ Directory: ~/.skillstack/ not found".to_string());
    } else {
        ui::success("Directory structure: OK");
    }

    let sync_engine = SyncEngine::new();
    if !sync_engine.verify_symlink(&claude, &repo_path).unwrap_or(false) {
        issues.push("❌ Symlink: Invalid or broken".to_string());
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
                    issues.push(format!("❌ Missing file: {}", skill.name));
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

    use crate::core::manifest::Manifest;
    let manifest = Manifest::load(&base.join("manifest.json"))?;
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

// Project management commands

fn cmd_project_add(path: &str, name: Option<&str>, tool: &str, scan_skills: bool) -> Result<()> {
    let base = fs::expand_tilde("~/.skillstack");
    if !base.exists() {
        return Err(anyhow::anyhow!("Not initialized. Run 'skillstack init'"));
    }

    let mut pm = ProjectManager::new(&base);
    let project_name = pm.register_project(path, name, tool)?;

    ui::success(&format!("Project '{}' registered", project_name));
    println!("📂 Path: {}", path);

    if scan_skills {
        if let Ok(skills) = pm.scan_project_skills(&project_name) {
            if !skills.is_empty() {
                println!("🔍 Found {} existing skills:", skills.len());
                for s in &skills {
                    println!("  📋 {}", s);
                }
            } else {
                println!("🔍 No existing skills found");
            }
        }
    }

    Ok(())
}

fn cmd_project_list(sort_by: &str, reverse: bool) -> Result<()> {
    let base = fs::expand_tilde("~/.skillstack");
    if !base.exists() {
        return Err(anyhow::anyhow!("Not initialized. Run 'skillstack init'"));
    }

    let pm = ProjectManager::new(&base);
    let mut projects = pm.list_projects()?;

    if projects.is_empty() {
        println!("No projects registered.");
        ui::info("Run 'skillstack project add <path>' to register a project");
        return Ok(());
    }

    match sort_by {
        "path" => projects.sort_by(|a, b| a.path.cmp(&b.path)),
        "skills" => projects.sort_by(|a, b| a.installed_skills.len().cmp(&b.installed_skills.len())),
        _ => projects.sort_by(|a, b| a.name.cmp(&b.name)),
    }

    if reverse {
        projects.reverse();
    }

    let widths = [20, 40, 10];
    println!("{}", ui::format_table_row(&["NAME", "PATH", "SKILLS"], &widths));
    println!("{}", "-".repeat(70));

    for p in &projects {
        let skills_count = p.installed_skills.len().to_string();
        println!("{}", ui::format_table_row(&[&p.name, &p.path, &skills_count], &widths));
    }

    println!("\nTotal: {} projects", projects.len());
    Ok(())
}

fn cmd_project_remove(name: &str, force: bool) -> Result<()> {
    let base = fs::expand_tilde("~/.skillstack");
    let mut pm = ProjectManager::new(&base);

    if !force {
        ui::warning(&format!("About to unregister project '{}'", name));
        println!("This will not delete project files, only remove registration.");
        if !ui::prompt("Continue?") {
            println!("Cancelled.");
            return Ok(());
        }
    }

    pm.unregister_project(name)?;
    ui::success(&format!("Project '{}' unregistered", name));
    Ok(())
}

fn cmd_project_sync(
    project_name: Option<&str>,
    all_projects: bool,
    skills: Option<&[String]>,
    force: bool,
    dry_run: bool,
) -> Result<()> {
    let base = fs::expand_tilde("~/.skillstack");
    let pm = ProjectManager::new(&base);

    if dry_run {
        println!("🏃 Dry run mode (no changes will be made)\n");
    }

    // Determine which projects to sync
    let projects_to_sync = if all_projects {
        pm.list_projects()?
    } else if let Some(name) = project_name {
        vec![pm.get_project(name)?]
    } else {
        return Err(anyhow::anyhow!("Must specify either project name or --all-projects"));
    };

    if projects_to_sync.is_empty() {
        println!("No projects to sync.");
        return Ok(());
    }

    let mut total_synced = 0;
    let mut total_skipped = 0;
    let mut total_with_overrides = 0;

    for project in &projects_to_sync {
        println!("🔄 Syncing '{}'...", project.name);

        // Get list of skills to sync
        let skills_to_sync: Vec<String> = if let Some(skill_list) = skills {
            skill_list.to_vec()
        } else {
            // Sync all installed skills
            project.installed_skills.clone()
        };

        if skills_to_sync.is_empty() {
            println!("  No skills to sync.");
            continue;
        }

        let mut synced = 0;
        let mut skipped = 0;

        for skill_name in &skills_to_sync {
            // Check if skill needs update
            let source_path = base.join("repository").join(skill_name).join("SKILL.md");
            let dest_path = std::path::PathBuf::from(&project.path)
                .join(format!(".{}", &project.tool))
                .join("skills")
                .join(skill_name)
                .join("SKILL.md");

            if !source_path.exists() {
                ui::warning(&format!("  Skill '{}' not found in global repository", skill_name));
                continue;
            }

            // Compare hashes
            let source_hash = crate::utils::hash::calculate_file_hash(&source_path)?;
            let needs_update = if dest_path.exists() {
                let dest_hash = crate::utils::hash::calculate_file_hash(&dest_path)?;

                // Check if project has override
                if project.overrides.contains_key(skill_name) && !force {
                    println!("  ⚠️  Skipped '{}' (project has override, use --force to overwrite)", skill_name);
                    total_with_overrides += 1;
                    skipped += 1;
                    continue;
                }

                source_hash != dest_hash || force
            } else {
                true
            };

            if needs_update {
                if !dry_run {
                    let src_dir = base.join("repository").join(skill_name);
                    let dst_dir = std::path::PathBuf::from(&project.path)
                        .join(format!(".{}", &project.tool))
                        .join("skills")
                        .join(skill_name);

                    crate::utils::fs::copy_dir_recursive(&src_dir, &dst_dir)?;

                    // Remove override after sync
                    if let Ok(proj) = pm.get_project(&project.name) {
                        if proj.overrides.contains_key(skill_name) {
                            // Clear override
                            use crate::core::manifest::Manifest;
                            let mut manifest = Manifest::load(&base.join("manifest.json"))?;
                            if let Some(p) = manifest.get_project_mut(&project.name) {
                                p.overrides.remove(skill_name);
                                manifest.save(&base.join("manifest.json"))?;
                            }
                        }
                    }
                }
                println!("  ✅ Synced '{}'", skill_name);
                synced += 1;
            } else {
                println!("  ⏭️  Skipped '{}' (already up-to-date)", skill_name);
                skipped += 1;
            }
        }

        total_synced += synced;
        total_skipped += skipped;
        println!("  {} synced, {} skipped\n", synced, skipped);
    }

    println!("✅ Total: {} synced, {} skipped across {} project(s)",
             total_synced, total_skipped, projects_to_sync.len());

    if total_with_overrides > 0 {
        println!("⚠️  {} skill(s) with overrides were protected (use --force to overwrite)",
                 total_with_overrides);
    }

    Ok(())
}

fn cmd_install(skill_name: &str, project: &str) -> Result<()> {
    let base = fs::expand_tilde("~/.skillstack");
    let mut pm = ProjectManager::new(&base);

    pm.install_skill(project, skill_name)?;
    ui::success(&format!("Installed '{}' to project '{}'", skill_name, project));

    let proj = pm.get_project(project)?;
    let skill_path = std::path::PathBuf::from(&proj.path)
        .join(format!(".{}", &proj.tool))
        .join("skills")
        .join(skill_name);
    println!("📂 Path: {}", skill_path.display());

    Ok(())
}

fn cmd_uninstall(skill_name: &str, project: &str) -> Result<()> {
    let base = fs::expand_tilde("~/.skillstack");
    let mut pm = ProjectManager::new(&base);

    pm.uninstall_skill(project, skill_name)?;
    ui::success(&format!("Uninstalled '{}' from project '{}'", skill_name, project));

    Ok(())
}
