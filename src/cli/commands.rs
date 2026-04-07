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
        project_name: String,
        #[arg(long)]
        skills: Option<Vec<String>>,
        #[arg(long)]
        force: bool,
        #[arg(long)]
        dry_run: bool,
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
            ProjectCommands::Sync { project_name, skills, force, dry_run } => {
                cmd_project_sync(&project_name, skills.as_deref(), force, dry_run)
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
