use colored::*;
use dialoguer::Confirm;

pub fn success(msg: &str) {
    println!("{} {}", "✅".green(), msg);
}

pub fn error(msg: &str) {
    eprintln!("{} {}", "❌".red(), msg);
}

pub fn warning(msg: &str) {
    println!("{} {}", "⚠️ ".yellow(), msg);
}

pub fn info(msg: &str) {
    println!("{} {}", "💡".blue(), msg);
}

pub fn prompt(msg: &str) -> bool {
    Confirm::new().with_prompt(msg).default(true).interact().unwrap_or(false)
}

pub fn format_table_row(cols: &[&str], widths: &[usize]) -> String {
    cols.iter().zip(widths).map(|(c, w)| format!("{:<w$}", c, w=w)).collect::<Vec<_>>().join("  ")
}
