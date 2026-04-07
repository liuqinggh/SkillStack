# SkillStack GUI

Modern desktop GUI for SkillStack built with Tauri 2.0 + React + TypeScript.

## 🚀 Quick Start

### Prerequisites

- **Rust**: `rustup` installed
- **Node.js**: v18+ and npm
- **SkillStack Core**: The parent directory's SkillStack Rust library

### Development

```bash
# Install dependencies
npm install

# Run in development mode (opens GUI window)
npm run tauri dev
```

### Build

```bash
# Build production binary
npm run tauri build

# Binary will be in src-tauri/target/release/
```

## 📦 Project Structure

```
gui/
├── src/                    # React frontend
│   ├── components/         # UI components
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Input.tsx
│   │   ├── Modal.tsx
│   │   ├── Toast.tsx
│   │   ├── Sidebar.tsx
│   │   ├── CreateSkillDialog.tsx
│   │   └── ConfirmDialog.tsx
│   ├── pages/              # Page components
│   │   ├── Dashboard.tsx
│   │   └── Skills.tsx
│   ├── stores/             # Zustand state management
│   │   └── useAppStore.ts
│   ├── types/              # TypeScript types
│   │   └── index.ts
│   ├── App.tsx             # Main app component
│   ├── main.tsx            # Entry point
│   └── index.css           # Tailwind styles
├── src-tauri/              # Rust backend
│   ├── src/
│   │   ├── commands.rs     # Tauri commands (API layer)
│   │   ├── lib.rs          # Library entry
│   │   └── main.rs         # Main binary
│   └── Cargo.toml          # Rust dependencies
└── package.json            # npm dependencies
```

## 🎨 Tech Stack

- **Frontend**:
  - React 19
  - TypeScript
  - Tailwind CSS (styling)
  - Zustand (state management)
  - Lucide React (icons)
  - Vite (build tool)

- **Backend**:
  - Tauri 2.0 (native app framework)
  - SkillStack Core Library (reused from parent)

## ✅ Features Implemented

### Week 1 Day 1-2 ✅

- ✅ Tauri project structure
- ✅ React + TypeScript setup
- ✅ Tailwind CSS styling
- ✅ Basic components (Button, Card, Input, Toast, Sidebar)
- ✅ State management with Zustand
- ✅ Tauri command layer (13 commands)
- ✅ Integration with SkillStack core library
- ✅ Dashboard page (basic)

### Week 1 Day 3-4 ✅

- ✅ Modal component
- ✅ CreateSkillDialog component
- ✅ ConfirmDialog component
- ✅ **Skills Page (Complete)**:
  - Skills list with search
  - Skill detail panel
  - Create skill functionality
  - Delete skill functionality
  - Metadata display
  - Empty & loading states

### Coming Soon

- 📂 Projects page (management + sync)
- ⚙️ Settings page
- 🔄 Edit skill functionality
- 📊 Diff viewer
- 🎯 Drag & drop

## 🛠️ Development Status

**Current**: Week 1 Day 3-4 Complete ✅

**Progress**:
- Week 1: 90% complete
- Components: 9/12 (75%)
- Pages: 2/4 (50%)

**Next Steps**:
- Week 1 Day 5: Dashboard enhancement
- Week 2: Projects page + advanced features

## 🔧 Available Commands

### Skills Management (✅ Complete)
- `get_skills()` - Fetch all skills
- `get_skill(name)` - Fetch single skill
- `create_skill(name, description)` - Create new skill
- `delete_skill(name)` - Delete skill

### Project Management (⏳ Backend only)
- `get_projects()` - Fetch all projects
- `register_project()` - Register project
- `install_skill_to_project()` - Install skill
- `uninstall_skill_from_project()` - Uninstall skill

### Dashboard (✅ Complete)
- `get_dashboard_stats()` - Fetch stats

### Utilities (✅ Complete)
- `check_initialized()` - Check initialization
- `initialize_skillstack()` - Initialize

## 📝 Notes

- GUI is completely optional - CLI remains fully functional
- GUI and CLI share the same core library (single source of truth)
- All data is stored locally in `~/.skillstack/`
- No network access required
- TypeScript compilation verified ✅
- Production build successful ✅

## 🐛 Troubleshooting

**Build errors**:
```bash
# Clean and rebuild
rm -rf node_modules package-lock.json
npm install
npm run tauri dev
```

**Rust errors**:
```bash
cd src-tauri
cargo clean
cargo build
```

**TypeScript errors**:
```bash
npx tsc --noEmit
```

## 📚 Resources

- [Tauri Documentation](https://tauri.app)
- [React Documentation](https://react.dev)
- [Tailwind CSS](https://tailwindcss.com)
- [Zustand](https://github.com/pmndrs/zustand)
- [SkillStack Design Document](../docs/GUI-DESIGN.md)
- [Week 1 Day 1-2 Report](../docs/GUI-WEEK1-DAY1-2.md)
- [Week 1 Day 3-4 Report](../docs/GUI-WEEK1-DAY3-4.md)

## 📊 Build Metrics

```bash
# Frontend bundle
Size: 217.77 KB
Gzipped: 67.58 KB
Build time: 1.39s

# TypeScript compilation
Errors: 0
Warnings: 0
```
