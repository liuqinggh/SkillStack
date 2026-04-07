use anyhow::Result;
use std::fs;
use std::path::Path;

pub struct DiffEngine;

#[derive(Debug)]
pub struct SkillDiff {
    pub global_hash: String,
    pub project_hash: String,
    pub global_content: String,
    pub project_content: String,
}

impl DiffEngine {
    pub fn new() -> Self {
        Self
    }

    /// Compare global skill with project skill
    pub fn compare_skills(
        &self,
        global_path: &Path,
        project_path: &Path,
    ) -> Result<SkillDiff> {
        let global_content = fs::read_to_string(global_path)?;
        let project_content = fs::read_to_string(project_path)?;

        let global_hash = crate::utils::hash::calculate_file_hash(global_path)?;
        let project_hash = crate::utils::hash::calculate_file_hash(project_path)?;

        Ok(SkillDiff {
            global_hash,
            project_hash,
            global_content,
            project_content,
        })
    }

    /// Format diff for display
    pub fn format_diff(&self, diff: &SkillDiff) -> String {
        let mut output = String::new();

        output.push_str(&format!("Global hash:  {}\n", diff.global_hash));
        output.push_str(&format!("Project hash: {}\n", diff.project_hash));
        output.push_str("\n");

        if diff.global_hash == diff.project_hash {
            output.push_str("✅ No differences (hashes match)\n");
            return output;
        }

        output.push_str("Changes:\n");
        output.push_str(&self.simple_diff(&diff.global_content, &diff.project_content));

        output
    }

    /// Simple line-by-line diff
    fn simple_diff(&self, global: &str, project: &str) -> String {
        let global_lines: Vec<&str> = global.lines().collect();
        let project_lines: Vec<&str> = project.lines().collect();

        let mut output = String::new();
        let max_lines = global_lines.len().max(project_lines.len());

        for i in 0..max_lines {
            let global_line = global_lines.get(i).copied();
            let project_line = project_lines.get(i).copied();

            match (global_line, project_line) {
                (Some(g), Some(p)) if g != p => {
                    output.push_str(&format!("  - Line {}: - {}\n", i + 1, g));
                    output.push_str(&format!("  + Line {}: + {}\n", i + 1, p));
                }
                (Some(_g), None) => {
                    output.push_str(&format!("  - Line {}: (removed in project)\n", i + 1));
                }
                (None, Some(p)) => {
                    output.push_str(&format!("  + Line {}: + {} (added in project)\n", i + 1, p));
                }
                _ => {}
            }
        }

        if output.is_empty() {
            output.push_str("  (No differences detected)\n");
        }

        output
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::TempDir;

    #[test]
    fn test_compare_identical_files() {
        let temp_dir = TempDir::new().unwrap();
        let global_path = temp_dir.path().join("global.md");
        let project_path = temp_dir.path().join("project.md");

        let content = "---\nname: test\ndescription: Test\n---\n\n# Test\n";
        fs::write(&global_path, content).unwrap();
        fs::write(&project_path, content).unwrap();

        let engine = DiffEngine::new();
        let diff = engine.compare_skills(&global_path, &project_path).unwrap();

        assert_eq!(diff.global_hash, diff.project_hash);
    }

    #[test]
    fn test_compare_different_files() {
        let temp_dir = TempDir::new().unwrap();
        let global_path = temp_dir.path().join("global.md");
        let project_path = temp_dir.path().join("project.md");

        fs::write(&global_path, "Global content\n").unwrap();
        fs::write(&project_path, "Project content\n").unwrap();

        let engine = DiffEngine::new();
        let diff = engine.compare_skills(&global_path, &project_path).unwrap();

        assert_ne!(diff.global_hash, diff.project_hash);
        assert_eq!(diff.global_content, "Global content\n");
        assert_eq!(diff.project_content, "Project content\n");
    }

    #[test]
    fn test_format_diff() {
        let temp_dir = TempDir::new().unwrap();
        let global_path = temp_dir.path().join("global.md");
        let project_path = temp_dir.path().join("project.md");

        fs::write(&global_path, "Line 1\nLine 2\n").unwrap();
        fs::write(&project_path, "Line 1\nModified Line 2\n").unwrap();

        let engine = DiffEngine::new();
        let diff = engine.compare_skills(&global_path, &project_path).unwrap();
        let formatted = engine.format_diff(&diff);

        assert!(formatted.contains("Global hash:"));
        assert!(formatted.contains("Project hash:"));
        assert!(formatted.contains("Changes:"));
    }
}
