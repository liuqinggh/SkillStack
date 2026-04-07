# Changelog

## [0.1.0-mvp] - 2026-04-07

### Added
- Initial MVP release with full P0+P1 functionality
- Core commands (7): init, list, add, edit, delete, sync, status
- Advanced commands (3): import, show, doctor
- Symlink-based real-time sync (zero-latency)
- Manifest tracking with SHA256 hash
- Config management (editor, auto-sync)
- Interactive prompts with colored output
- Relative time display (just now, 5m ago, etc.)

### Tested
- ✅ All 10 commands manually tested
- ✅ 8/8 unit tests passing
- ✅ 1/1 integration test passing
- ✅ Claude Code integration verified:
  - New skills immediately visible
  - Modified skills instantly updated
  - Deleted skills removed in real-time
- ✅ Release build successful

### Technical
- Rust 2021 edition
- Symlink-based sync (Unix only)
- JSON manifest + config
- YAML frontmatter parsing
- SHA256 file hashing
