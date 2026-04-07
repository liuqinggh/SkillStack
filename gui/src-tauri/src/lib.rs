mod commands;

use commands::*;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            // Skill commands
            get_skills,
            get_skill,
            create_skill,
            delete_skill,
            // Project commands
            get_projects,
            get_project,
            register_project,
            unregister_project,
            install_skill_to_project,
            uninstall_skill_from_project,
            // Dashboard commands
            get_dashboard_stats,
            // Utility commands
            check_initialized,
            initialize_skillstack,
            open_skill_in_editor,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
