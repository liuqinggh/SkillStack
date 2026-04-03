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
    if !output.status.success() {
        eprintln!("Init stdout: {}", String::from_utf8_lossy(&output.stdout));
        eprintln!("Init stderr: {}", String::from_utf8_lossy(&output.stderr));
    }
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
