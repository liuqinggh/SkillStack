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
        let json = serde_json::to_string_pretty(&self)?;
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
