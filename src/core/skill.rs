use anyhow::{anyhow, Result};
use regex::Regex;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Skill {
    pub name: String,
    pub description: String,
    pub created_at: String,
    pub updated_at: String,
    pub hash: String,
    pub path: String,
}

impl Skill {
    pub fn validate_name(name: &str) -> Result<()> {
        let re = Regex::new(r"^[a-z][a-z0-9-]*$").unwrap();
        if re.is_match(name) {
            Ok(())
        } else {
            Err(anyhow!("Invalid skill name. Use lowercase letters, numbers, hyphens. Must start with letter."))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_name_valid() {
        assert!(Skill::validate_name("my-skill").is_ok());
        assert!(Skill::validate_name("skill-v2").is_ok());
    }

    #[test]
    fn test_validate_name_invalid() {
        assert!(Skill::validate_name("My-Skill").is_err());
        assert!(Skill::validate_name("my skill").is_err());
        assert!(Skill::validate_name("123-skill").is_err());
    }
}
