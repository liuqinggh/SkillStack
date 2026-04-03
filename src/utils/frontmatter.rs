use anyhow::{anyhow, Result};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize, Serialize)]
struct FrontmatterData {
    name: String,
    description: String,
}

pub fn parse(content: &str) -> Result<(String, String)> {
    let parts: Vec<&str> = content.splitn(3, "---").collect();
    if parts.len() < 3 {
        return Err(anyhow!("Invalid frontmatter format"));
    }
    let yaml = parts[1].trim();
    let data: FrontmatterData = serde_yaml::from_str(yaml)?;
    Ok((data.name, data.description))
}

pub fn generate_template(name: &str, desc: &str) -> String {
    format!(
        "---\nname: {}\ndescription: {}\n---\n\n# {}\n\n## 功能说明\n\n这个skill用于...\n",
        name, desc, name
    )
}
