use anyhow::Result;
use std::fs;
use std::path::Path;

#[cfg(unix)]
use std::os::unix::fs as unix_fs;

pub struct SyncEngine;

impl SyncEngine {
    pub fn new() -> Self {
        Self
    }

    pub fn create_symlink(&self, source: &Path, target: &Path) -> Result<()> {
        if target.exists() {
            let backup = target.with_extension("backup");
            if target.is_symlink() {
                fs::remove_file(target)?;
            } else {
                fs::rename(target, &backup)?;
            }
        }

        #[cfg(unix)]
        unix_fs::symlink(source, target)?;

        #[cfg(not(unix))]
        return Err(anyhow!("Symlink not supported on this platform"));

        Ok(())
    }

    pub fn verify_symlink(&self, target: &Path, expected_source: &Path) -> Result<bool> {
        if !target.exists() || !target.is_symlink() {
            return Ok(false);
        }
        let actual = target.read_link()?;
        Ok(actual == expected_source)
    }

    pub fn rebuild_symlink(&self, source: &Path, target: &Path) -> Result<()> {
        if target.exists() && target.is_symlink() {
            fs::remove_file(target)?;
        }
        self.create_symlink(source, target)
    }
}

#[cfg(test)]
#[cfg(unix)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_create_symlink() {
        let temp = TempDir::new().unwrap();
        let src = temp.path().join("src");
        let tgt = temp.path().join("tgt");
        fs::create_dir(&src).unwrap();

        let engine = SyncEngine::new();
        engine.create_symlink(&src, &tgt).unwrap();

        assert!(tgt.is_symlink());
    }
}
