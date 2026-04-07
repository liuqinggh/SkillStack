# SkillStack GUI 设计方案

**版本**: v1.0  
**日期**: 2026-04-07  
**目标**: 为 SkillStack 提供现代化的图形界面，降低使用门槛，提升用户体验

---

## 📋 目录

1. [设计目标](#1-设计目标)
2. [技术选型](#2-技术选型)
3. [架构设计](#3-架构设计)
4. [界面设计](#4-界面设计)
5. [功能模块](#5-功能模块)
6. [交互流程](#6-交互流程)
7. [实现计划](#7-实现计划)
8. [风险与应对](#8-风险与应对)

---

## 1. 设计目标

### 1.1 核心目标

**降低使用门槛**:
- 可视化管理 Skills，无需记忆 CLI 命令
- 拖拽操作，直观的项目-Skill 关联
- 实时预览 Skill 内容

**提升用户体验**:
- 现代化 UI/UX 设计
- 快速搜索和过滤
- 批量操作支持
- 实时状态反馈

**保持 CLI 优势**:
- GUI 和 CLI 共享同一核心库
- GUI 可显示等效的 CLI 命令（学习模式）
- 专业用户仍可使用 CLI

### 1.2 目标用户

**主要用户**:
- 不熟悉命令行的开发者
- 管理多个项目的开发者
- 需要可视化概览的团队

**次要用户**:
- CLI 用户（GUI 作为辅助工具）
- 新手（通过 GUI 学习工具）

### 1.3 成功标准

- ✅ 所有 CLI 功能都有 GUI 对应
- ✅ 常见操作（创建 Skill、同步项目）≤ 3 次点击
- ✅ 启动时间 < 2 秒
- ✅ 内存占用 < 100MB
- ✅ 跨平台一致体验（macOS/Windows/Linux）

---

## 2. 技术选型

### 2.1 推荐方案：Tauri 2.0

**选择理由**:

| 特性 | Tauri | Electron | Iced | egui |
|------|-------|----------|------|------|
| **包体积** | ~5MB | ~50MB | ~10MB | ~15MB |
| **内存占用** | ~50MB | ~150MB | ~40MB | ~30MB |
| **开发效率** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **UI 现代化** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **跨平台** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Rust 集成** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **生态成熟度** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

**Tauri 优势**:
- ✅ 复用现有 Rust 核心代码（无需重写）
- ✅ 前端使用现代 Web 技术（React/Vue/Svelte）
- ✅ 打包体积小（~5MB vs Electron ~50MB）
- ✅ 内存占用低（~50MB vs Electron ~150MB）
- ✅ 安全性高（沙箱隔离、权限控制）
- ✅ 原生系统集成（文件拾取器、通知等）
- ✅ 活跃社区和丰富文档

### 2.2 技术栈

**后端（Rust）**:
```toml
[dependencies]
tauri = "2.0"                    # GUI 框架
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
tokio = { version = "1", features = ["full"] }  # 异步运行时

# 复用现有依赖
skillstack = { path = "../" }    # 核心库
```

**前端（推荐 React + TypeScript）**:
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tauri-apps/api": "^2.0.0",
    "react-router-dom": "^6.20.0",
    "tailwindcss": "^3.4.0",      // 样式
    "lucide-react": "^0.300.0",   // 图标
    "react-query": "^3.39.0",     // 数据管理
    "zustand": "^4.4.0"           // 状态管理
  }
}
```

**替代方案（Svelte - 更轻量）**:
- 更小的打包体积
- 更快的运行速度
- 学习曲线稍陡

**替代方案（Vue 3 - 中等选择）**:
- 平衡的性能和开发体验
- 组合式 API 适合复杂状态

### 2.3 项目结构

```
SkillStack/
├── src/                          # 现有 CLI 核心库
│   ├── core/                     # 核心模块（共享）
│   ├── cli/                      # CLI 专用
│   └── lib.rs
├── gui/                          # 新增 GUI 部分
│   ├── src-tauri/                # Tauri Rust 后端
│   │   ├── src/
│   │   │   ├── main.rs           # GUI 入口
│   │   │   ├── commands.rs       # Tauri 命令（调用核心库）
│   │   │   ├── state.rs          # 应用状态
│   │   │   └── events.rs         # 事件处理
│   │   ├── Cargo.toml
│   │   └── tauri.conf.json       # Tauri 配置
│   └── src/                      # React 前端
│       ├── components/           # UI 组件
│       ├── pages/                # 页面
│       ├── hooks/                # React Hooks
│       ├── utils/                # 工具函数
│       ├── App.tsx
│       └── main.tsx
├── Cargo.toml                    # 主 Cargo 配置
└── README.md
```

---

## 3. 架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────┐
│              GUI Application                │
├─────────────────────────────────────────────┤
│  Frontend (React/TypeScript)                │
│  ┌────────────┬──────────────┬────────────┐ │
│  │  Dashboard │  Skill View  │  Projects  │ │
│  │    Page    │     Page     │    Page    │ │
│  └────────────┴──────────────┴────────────┘ │
│         ↕ (IPC: invoke/emit)                │
├─────────────────────────────────────────────┤
│  Backend (Tauri + Rust)                     │
│  ┌────────────────────────────────────────┐ │
│  │  Tauri Commands (API Layer)           │ │
│  │  - get_skills(), create_skill()       │ │
│  │  - get_projects(), sync_project()     │ │
│  └────────────────────────────────────────┘ │
│         ↕                                   │
│  ┌────────────────────────────────────────┐ │
│  │  SkillStack Core Library (Shared)     │ │
│  │  - Repository, ProjectManager          │ │
│  │  - Manifest, SyncEngine                │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
         ↕
┌─────────────────────────────────────────────┐
│        File System                          │
│  ~/.skillstack/  +  Project Directories     │
└─────────────────────────────────────────────┘
```

### 3.2 通信机制

**Tauri IPC (Inter-Process Communication)**:

```typescript
// Frontend -> Backend (调用命令)
import { invoke } from '@tauri-apps/api/tauri';

// 获取所有 Skills
const skills = await invoke<Skill[]>('get_skills');

// 创建新 Skill
await invoke('create_skill', { 
  name: 'my-skill',
  description: 'My awesome skill' 
});

// Backend -> Frontend (事件推送)
import { listen } from '@tauri-apps/api/event';

listen('sync-progress', (event) => {
  console.log('Sync progress:', event.payload);
});
```

**Rust 后端命令定义**:

```rust
// gui/src-tauri/src/commands.rs

#[tauri::command]
async fn get_skills() -> Result<Vec<Skill>, String> {
    let base = fs::expand_tilde("~/.skillstack");
    let repo = Repository::new(&base);
    repo.list_skills().map_err(|e| e.to_string())
}

#[tauri::command]
async fn create_skill(name: String, description: String) -> Result<(), String> {
    // 调用核心库
    let base = fs::expand_tilde("~/.skillstack");
    let mut repo = Repository::new(&base);
    repo.create_skill(&name, Some(&description))
        .map_err(|e| e.to_string())
}

#[tauri::command]
async fn sync_project(
    project_name: String, 
    parallel: bool,
    window: tauri::Window
) -> Result<SyncSummary, String> {
    // 带进度反馈的同步
    // ...发送进度事件到前端
    window.emit("sync-progress", progress).ok();
    // ...
}
```

### 3.3 状态管理

**前端状态 (Zustand)**:

```typescript
// src/stores/useAppStore.ts
import create from 'zustand';

interface AppState {
  skills: Skill[];
  projects: Project[];
  selectedSkill: Skill | null;
  selectedProject: Project | null;
  
  // Actions
  fetchSkills: () => Promise<void>;
  fetchProjects: () => Promise<void>;
  selectSkill: (skill: Skill) => void;
  syncProject: (projectName: string) => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  skills: [],
  projects: [],
  selectedSkill: null,
  selectedProject: null,
  
  fetchSkills: async () => {
    const skills = await invoke<Skill[]>('get_skills');
    set({ skills });
  },
  
  // ... 其他 actions
}));
```

---

## 4. 界面设计

### 4.1 布局设计

**主窗口布局 (三栏式)**:

```
┌──────────────────────────────────────────────────────────┐
│  SkillStack                            [ - ] [ □ ] [ × ] │ 顶部标题栏
├────────┬─────────────────────────────────────────────────┤
│        │                                                  │
│  侧边  │              主内容区域                          │
│  导航  │                                                  │
│        │                                                  │
│  🏠    │  根据选中页面显示不同内容:                      │
│ 仪表板 │  - Dashboard (概览)                             │
│        │  - Skills (技能列表)                            │
│  📦    │  - Projects (项目列表)                          │
│ Skills │  - Settings (设置)                              │
│        │                                                  │
│  📂    │                                                  │
│Projects│                                                  │
│        │                                                  │
│  ⚙️    │                                                  │
│ Settings│                                                 │
│        │                                                  │
├────────┴─────────────────────────────────────────────────┤
│  Status: Ready | 10 skills, 5 projects                   │ 底部状态栏
└──────────────────────────────────────────────────────────┘
```

### 4.2 页面详细设计

#### 页面 1: Dashboard (仪表板)

**目标**: 快速概览和常用操作

```
┌──────────────────────────────────────────────────────────┐
│  Dashboard                                    [新建 Skill]│
├──────────────────────────────────────────────────────────┤
│                                                           │
│  📊 统计概览                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ 10       │  │ 5        │  │ 2        │               │
│  │ Skills   │  │ Projects │  │ Synced   │               │
│  │          │  │          │  │ Today    │               │
│  └──────────┘  └──────────┘  └──────────┘               │
│                                                           │
│  📌 最近使用的 Skills                         [查看全部] │
│  ┌────────────────────────────────────────────────────┐  │
│  │ debugging        Updated 2h ago        [编辑][同步]│  │
│  │ testing          Updated 1d ago        [编辑][同步]│  │
│  │ deployment       Updated 3d ago        [编辑][同步]│  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  📂 项目状态                                  [管理项目] │
│  ┌────────────────────────────────────────────────────┐  │
│  │ web-app          5 skills    ✅ Synced 1h ago     │  │
│  │ api-server       3 skills    ⚠️  2 overrides       │  │
│  │ mobile-app       2 skills    ❌ Out of sync       │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  🔔 提醒                                                  │
│  - skill-debug 有新版本可用于 web-app                    │
│  - api-server 有 2 个 override 需要处理                  │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

#### 页面 2: Skills (技能管理)

**目标**: 管理所有全局 Skills

```
┌──────────────────────────────────────────────────────────┐
│  Skills                        [🔍 搜索] [+ 新建 Skill]  │
├──────────────────────────────────────────────────────────┤
│  过滤: [全部▾] [最近使用▾] [标签▾]     排序: [名称▾]    │
├───────────────────────────────┬──────────────────────────┤
│  Skills 列表                  │  Skill 详情              │
│                               │                          │
│  ┌─────────────────────────┐ │  debugging               │
│  │ ✅ debugging            │ │  ──────────────────────  │
│  │    描述: Debug skill    │ │                          │
│  │    更新: 2h ago         │ │  📝 描述                 │
│  └─────────────────────────┘ │  Advanced debugging...   │
│                               │                          │
│  ┌─────────────────────────┐ │  📊 使用情况             │
│  │ □ testing               │ │  使用于 3 个项目:        │
│  │    描述: Testing skill  │ │  - web-app               │
│  │    更新: 1d ago         │ │  - api-server            │
│  └─────────────────────────┘ │  - mobile-app            │
│                               │                          │
│  ┌─────────────────────────┐ │  🏷️ 元数据               │
│  │ □ deployment            │ │  Created: 2026-04-01     │
│  │    描述: Deploy skill   │ │  Updated: 2h ago         │
│  │    更新: 3d ago         │ │  Hash: abc123...         │
│  └─────────────────────────┘ │                          │
│                               │  [编辑] [删除] [同步到...]│
│  批量操作: [同步] [删除]      │                          │
└───────────────────────────────┴──────────────────────────┘
```

**交互细节**:
- 点击 Skill 名称 → 右侧显示详情
- 勾选复选框 → 启用批量操作
- 双击 → 打开编辑器
- 右键 → 上下文菜单（编辑/删除/同步）

#### 页面 3: Projects (项目管理)

**目标**: 管理项目和项目级 Skills

```
┌──────────────────────────────────────────────────────────┐
│  Projects                  [🔍 搜索] [+ 注册项目]         │
├──────────────────────────────────────────────────────────┤
│  [全部项目 ▾]  [扫描目录] [批量同步]                     │
├──────────────────┬──────────────────────────────────────┤
│  项目列表        │  项目详情: web-app                   │
│                  │                                       │
│  ┌────────────┐  │  📂 路径: /Users/xxx/projects/web-app│
│  │ web-app ✅ │  │  🔧 工具: Claude                      │
│  │ 5 skills   │  │  📊 状态: ✅ 已同步 (1h ago)          │
│  │ Synced 1h  │  │                                       │
│  └────────────┘  │  ─────────────────────────────────── │
│                  │                                       │
│  ┌────────────┐  │  Skills (5)    [从全局安装] [全部同步]│
│  │ api-server │  │                                       │
│  │ 3 skills   │  │  ┌───────────────────────────────┐   │
│  │ 2 override │  │  │ ✅ debugging     [global]     │   │
│  └────────────┘  │  │    已同步 ✓                   │   │
│                  │  └───────────────────────────────┘   │
│  ┌────────────┐  │                                       │
│  │ mobile-app │  │  ┌───────────────────────────────┐   │
│  │ 2 skills   │  │  │ ⚠️  testing      [override]   │   │
│  │ Out of sync│  │  │    项目版本与全局不同         │   │
│  └────────────┘  │  │    [查看 Diff] [接受全局版本] │   │
│                  │  └───────────────────────────────┘   │
│                  │                                       │
│                  │  ┌───────────────────────────────┐   │
│                  │  │ □ deployment     [global]     │   │
│                  │  │    需要更新 🔄                │   │
│                  │  │    [同步]                     │   │
│                  │  └───────────────────────────────┘   │
│                  │                                       │
│                  │  [移除项目]                           │
└──────────────────┴──────────────────────────────────────┘
```

**交互细节**:
- Override 标记用黄色高亮
- 点击 "查看 Diff" → 弹出 Diff 对比窗口
- 拖拽全局 Skill → 项目 → 自动安装

#### 页面 4: Settings (设置)

**目标**: 全局配置

```
┌──────────────────────────────────────────────────────────┐
│  Settings                                                 │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ⚙️ 通用设置                                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 编辑器: [VS Code ▾]                                │  │
│  │ 主题:   [自动 ▾] (跟随系统)                        │  │
│  │ 启动时: [✅] 检查更新                              │  │
│  │         [✅] 扫描项目变化                          │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  📂 路径设置                                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 中央仓库: ~/.skillstack/repository    [更改]       │  │
│  │ 配置文件: ~/.skillstack/manifest.json             │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  🔄 同步设置                                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 默认同步模式: [增量同步 ▾]                         │  │
│  │ 并行同步:     [✅] 启用 (更快)                     │  │
│  │ Override 处理: [询问 ▾]                            │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  💾 数据管理                                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │ [导出配置]  [导入配置]  [清理缓存]                 │  │
│  │ [运行 Doctor]                                      │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  ℹ️ 关于                                                  │
│  ┌────────────────────────────────────────────────────┐  │
│  │ SkillStack v0.2.1                                  │  │
│  │ 集中式 Skill 管理工具                              │  │
│  │ [检查更新] [查看文档] [报告问题]                   │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### 4.3 弹窗/对话框设计

#### 对话框 1: 创建 Skill

```
┌─────────────────────────────────────────┐
│  创建新 Skill                   [ × ]   │
├─────────────────────────────────────────┤
│                                         │
│  名称 *                                 │
│  ┌───────────────────────────────────┐ │
│  │ my-awesome-skill                  │ │
│  └───────────────────────────────────┘ │
│                                         │
│  描述                                   │
│  ┌───────────────────────────────────┐ │
│  │ This skill helps with...          │ │
│  │                                   │ │
│  └───────────────────────────────────┘ │
│                                         │
│  [✅] 创建后打开编辑器                  │
│  [✅] 立即同步到项目:                   │
│      ☐ web-app                         │
│      ☐ api-server                      │
│      ☐ mobile-app                      │
│                                         │
│              [取消]     [创建]          │
└─────────────────────────────────────────┘
```

#### 对话框 2: Diff 对比

```
┌──────────────────────────────────────────────────────┐
│  Diff: testing (全局 vs web-app)           [ × ]    │
├──────────────────────────────────────────────────────┤
│                                                       │
│  全局版本              │  项目版本 (web-app)         │
│  Hash: abc123...       │  Hash: xyz789...            │
│  Updated: 1d ago       │  Updated: 2h ago            │
│  ─────────────────────────────────────────────────   │
│                                                       │
│   1  ---                │   1  ---                   │
│   2  name: testing      │   2  name: testing         │
│   3  description: ...   │   3  description: ...      │
│   4  ---                │   4  ---                   │
│   5  ## Instructions    │   5  ## Instructions       │
│   6  - Step 1           │   6  - Step 1              │
│   7  - Step 2           │ - 7  - Step 2              │
│                         │ + 7  - Step 2 (modified)   │
│   8  - Step 3           │   8  - Step 3              │
│                                                       │
│  ─────────────────────────────────────────────────   │
│                                                       │
│  [接受全局版本]  [保留项目版本]  [手动合并]  [关闭]  │
└──────────────────────────────────────────────────────┘
```

#### 对话框 3: 同步进度

```
┌─────────────────────────────────────────┐
│  正在同步项目...                [ × ]   │
├─────────────────────────────────────────┤
│                                         │
│  同步到: web-app, api-server, mobile-app│
│                                         │
│  ┌───────────────────────────────────┐ │
│  │ ████████████░░░░░░░░░░░░░ 50%     │ │
│  └───────────────────────────────────┘ │
│                                         │
│  正在同步: debugging -> web-app         │
│                                         │
│  已完成:                                │
│  ✅ testing -> web-app                  │
│  ✅ deployment -> api-server            │
│                                         │
│  跳过:                                  │
│  ⏭️  testing -> api-server (override)   │
│                                         │
│                      [取消]             │
└─────────────────────────────────────────┘
```

### 4.4 主题设计

**亮色主题 (默认)**:
- 背景: `#FFFFFF`
- 侧边栏: `#F5F5F5`
- 主色调: `#3B82F6` (蓝色)
- 成功: `#10B981` (绿色)
- 警告: `#F59E0B` (橙色)
- 错误: `#EF4444` (红色)

**暗色主题**:
- 背景: `#1E1E1E`
- 侧边栏: `#252526`
- 主色调: `#60A5FA` (浅蓝)
- 成功: `#34D399`
- 警告: `#FBBF24`
- 错误: `#F87171`

---

## 5. 功能模块

### 5.1 核心功能映射

| CLI 命令 | GUI 操作 | 页面位置 |
|----------|----------|----------|
| `init` | 自动初始化（首次启动） | - |
| `list` | Skills 列表 | Skills 页面 |
| `add <name>` | [+ 新建 Skill] 按钮 | Skills 页面 |
| `edit <name>` | 双击 Skill / [编辑] 按钮 | Skills 详情 |
| `delete <name>` | [删除] 按钮 | Skills 详情 |
| `sync` | [全部同步] 按钮 | Dashboard |
| `import <path>` | 拖拽文件到窗口 | Skills 页面 |
| `show <name>` | 点击 Skill 查看详情 | Skills 详情 |
| `doctor` | Settings → [运行 Doctor] | Settings 页面 |
| `status` | Dashboard 顶部统计 | Dashboard |
| `project add` | [+ 注册项目] 按钮 | Projects 页面 |
| `project list` | 项目列表 | Projects 页面 |
| `project remove` | [移除项目] 按钮 | Projects 详情 |
| `project sync` | [同步] / [全部同步] | Projects 详情 |
| `project scan` | [扫描目录] 按钮 | Projects 页面 |
| `install` | 拖拽 Skill 到项目 | Projects 详情 |
| `uninstall` | Skill 卡片 [×] 按钮 | Projects 详情 |
| `diff` | [查看 Diff] 按钮 | Projects 详情 |

### 5.2 额外 GUI 功能

**仅 GUI 支持的功能**:

1. **拖拽操作**
   - 拖拽文件 → 导入 Skill
   - 拖拽 Skill → 项目 → 安装到项目
   - 拖拽项目文件夹 → 注册项目

2. **可视化对比**
   - 并排 Diff 视图
   - 语法高亮
   - 一键接受/拒绝变更

3. **批量操作**
   - 多选 Skills → 批量同步
   - 多选项目 → 批量操作

4. **实时搜索**
   - 即时过滤 Skills/Projects
   - 模糊搜索
   - 标签筛选

5. **快捷键**
   - `Cmd+N` / `Ctrl+N`: 新建 Skill
   - `Cmd+S` / `Ctrl+S`: 保存当前编辑
   - `Cmd+F` / `Ctrl+F`: 搜索
   - `Cmd+,` / `Ctrl+,`: 打开设置

---

## 6. 交互流程

### 6.1 首次使用流程

```
用户启动 GUI
    ↓
检测 ~/.skillstack 是否存在
    ↓
否 → 显示欢迎界面
    ↓
    "欢迎使用 SkillStack!"
    [开始使用] 按钮
    ↓
    自动执行 init
    ↓
    "是否导入现有 Skills?" (如果检测到 ~/.claude/skills)
    [是] / [否]
    ↓
是 → 直接进入 Dashboard
    ↓
    显示快速入门提示:
    - 创建第一个 Skill
    - 注册第一个项目
    - 同步 Skill 到项目
    ↓
    [跳过教程] / [开始教程]
```

### 6.2 创建并同步 Skill 流程

```
用户点击 [+ 新建 Skill]
    ↓
弹出 "创建 Skill" 对话框
    ↓
用户输入:
    - 名称: "my-skill"
    - 描述: "..."
    - ✅ 创建后打开编辑器
    - ✅ 同步到项目: web-app, api-server
    ↓
点击 [创建]
    ↓
后台调用: invoke('create_skill', ...)
    ↓
成功后:
    1. 关闭对话框
    2. 刷新 Skills 列表
    3. 打开系统编辑器 (VS Code)
    4. 后台自动同步到选中项目
    5. 显示通知: "Skill 已创建并同步到 2 个项目"
    ↓
用户在 Skills 列表中看到新 Skill
```

### 6.3 处理 Override 流程

```
用户在 Projects 页面选择项目 "web-app"
    ↓
看到 Skill "testing" 标记为 ⚠️ override
    ↓
点击 [查看 Diff]
    ↓
弹出 Diff 对比窗口
    ↓
显示:
    - 全局版本 (左侧)
    - 项目版本 (右侧)
    - 高亮差异部分
    ↓
用户选择:
    - [接受全局版本] → 覆盖项目版本
    - [保留项目版本] → 继续使用 override
    - [手动合并] → 打开编辑器手动处理
    ↓
执行操作并刷新界面
```

---

## 7. 实现计划

### 7.1 阶段划分 (4 周)

#### Week 1: 基础架构 (5 天)

**Day 1-2: Tauri 项目搭建**
- [ ] 创建 Tauri 项目结构
- [ ] 配置 Tauri + React + TypeScript
- [ ] 设置 Tailwind CSS
- [ ] 创建基础组件库（Button, Input, Card 等）

**Day 3-4: 后端集成**
- [ ] 创建 Tauri 命令层（commands.rs）
- [ ] 集成 SkillStack 核心库
- [ ] 实现基础 API:
  - `get_skills()`
  - `create_skill()`
  - `get_projects()`
- [ ] 编写单元测试

**Day 5: 状态管理**
- [ ] 设置 Zustand 状态管理
- [ ] 实现前后端通信
- [ ] 测试 IPC 调用

#### Week 2: 核心页面 (5 天)

**Day 6-7: Dashboard 页面**
- [ ] 实现统计卡片
- [ ] 最近使用的 Skills 列表
- [ ] 项目状态概览
- [ ] 提醒/通知区域

**Day 8-9: Skills 页面**
- [ ] Skills 列表组件
- [ ] Skill 详情面板
- [ ] 搜索和过滤功能
- [ ] 创建 Skill 对话框
- [ ] 编辑/删除功能

**Day 10: Projects 页面 (基础)**
- [ ] 项目列表组件
- [ ] 项目详情面板
- [ ] 注册/移除项目功能

#### Week 3: 高级功能 (5 天)

**Day 11-12: Projects 页面 (完整)**
- [ ] Skill 安装/卸载
- [ ] 项目级 Skills 列表
- [ ] Override 检测和显示
- [ ] 同步功能

**Day 13-14: Diff 功能**
- [ ] Diff 对比对话框
- [ ] 语法高亮
- [ ] 并排对比视图
- [ ] 接受/拒绝变更

**Day 15: 批量操作**
- [ ] 多选 UI
- [ ] 批量同步
- [ ] 批量删除
- [ ] 进度显示

#### Week 4: 完善与发布 (5 天)

**Day 16-17: Settings 页面**
- [ ] 通用设置
- [ ] 路径设置
- [ ] 同步设置
- [ ] 数据管理
- [ ] Doctor 集成

**Day 18: 拖拽功能**
- [ ] 拖拽导入 Skill
- [ ] 拖拽注册项目
- [ ] 拖拽安装 Skill 到项目

**Day 19: 测试和优化**
- [ ] 端到端测试
- [ ] 性能优化
- [ ] Bug 修复
- [ ] UI/UX 打磨

**Day 20: 打包和发布**
- [ ] 配置打包选项
- [ ] 生成安装包 (macOS/Windows/Linux)
- [ ] 编写用户文档
- [ ] 创建 release

### 7.2 技术债务处理

**重构核心库以支持 GUI**:
- [ ] 提取 CLI 特定代码
- [ ] 使核心库完全可复用
- [ ] 添加异步支持（使用 tokio）
- [ ] 改进错误处理（返回结构化错误）

**示例重构**:

```rust
// 之前 (CLI 特定)
pub fn create_skill(&mut self, name: &str) -> Result<()> {
    // ...
    ui::success("Skill created");  // ❌ CLI 耦合
    Ok(())
}

// 之后 (GUI 友好)
pub fn create_skill(&mut self, name: &str) -> Result<SkillCreatedEvent> {
    // ...
    Ok(SkillCreatedEvent {
        name: name.to_string(),
        path: skill_path,
        created_at: Utc::now(),
    })
}
```

### 7.3 开发工具链

**所需工具**:
```bash
# Rust 工具链
rustup default stable

# Node.js (推荐 v18+)
node --version

# Tauri CLI
cargo install tauri-cli

# 前端依赖
cd gui && npm install

# 开发模式运行
npm run tauri dev

# 构建生产版本
npm run tauri build
```

---

## 8. 风险与应对

### 8.1 技术风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| Tauri 学习曲线 | 中 | 中 | 先做 PoC，验证可行性 |
| 性能问题（大量 Skills） | 中 | 高 | 虚拟滚动、分页加载 |
| 跨平台兼容性 | 低 | 高 | 每个平台都测试 |
| 打包体积过大 | 低 | 低 | 代码分割、Tree shaking |

### 8.2 用户体验风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| 界面过于复杂 | 中 | 高 | 简化初始界面，高级功能可选 |
| 与 CLI 不一致 | 中 | 中 | 保持功能对等，GUI 可显示等效命令 |
| 学习成本高 | 低 | 中 | 提供教程、工具提示 |

### 8.3 项目管理风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| 时间估算不足 | 高 | 中 | MVP 优先，次要功能后置 |
| 需求变更 | 中 | 中 | 敏捷开发，小步迭代 |
| 维护成本高 | 中 | 中 | 良好的代码结构、文档 |

---

## 9. MVP 范围

### 9.1 MVP 功能清单

**必须有 (Must Have)**:
- ✅ Dashboard 页面（基础统计）
- ✅ Skills 页面（列表、创建、编辑、删除）
- ✅ Projects 页面（列表、注册、移除）
- ✅ 基础同步功能
- ✅ 搜索功能

**应该有 (Should Have)**:
- ⭐ Override 检测和标记
- ⭐ Diff 对比（简化版）
- ⭐ 批量操作（基础）
- ⭐ Settings 页面

**可以有 (Could Have)**:
- 📌 拖拽操作
- 📌 实时同步进度
- 📌 主题切换
- 📌 快捷键

**不会有 (Won't Have in MVP)**:
- ❌ 版本管理（留给后续）
- ❌ 团队协作
- ❌ 云同步
- ❌ 插件系统

### 9.2 MVP 验收标准

MVP 完成当且仅当:

1. ✅ 所有 CLI 核心功能都有 GUI 对应
2. ✅ 可以完整完成以下用户故事:
   - 创建 Skill 并同步到项目
   - 注册项目并管理 Skills
   - 检测和处理 Override
3. ✅ 跨平台打包成功（macOS/Windows/Linux）
4. ✅ 启动时间 < 2 秒
5. ✅ 内存占用 < 100MB
6. ✅ 用户文档完整

---

## 10. 后续扩展

### 10.1 Phase 2 功能

**版本管理集成**:
- 在 GUI 中查看版本历史
- 可视化版本切换
- 版本对比 (v1.0 vs v2.0)

**高级 Diff**:
- 三向合并
- 冲突解决工具
- 自动合并建议

### 10.2 Phase 3 功能

**团队协作**:
- 共享 Skill 仓库
- 权限管理
- 协作编辑

**技能市场**:
- 浏览公共 Skills
- 一键安装社区 Skills
- 发布自己的 Skills

---

## 11. 总结

### 11.1 为什么选择 Tauri

**对比 Electron**:
- ✅ 体积小 10 倍 (~5MB vs ~50MB)
- ✅ 内存占用低 1/3 (~50MB vs ~150MB)
- ✅ 启动更快
- ✅ 更安全（沙箱隔离）
- ✅ 原生性能

**对比纯 Rust GUI (Iced/egui)**:
- ✅ 开发效率高（Web 技术栈成熟）
- ✅ UI 更现代化
- ✅ 组件生态丰富
- ✅ 设计师友好

### 11.2 预期成果

**技术指标**:
- 安装包体积: ~5-10MB
- 启动时间: < 2s
- 内存占用: < 100MB
- 支持平台: macOS, Windows, Linux

**用户价值**:
- 零学习成本的可视化管理
- 拖拽操作，提升效率 10 倍
- 实时预览，所见即所得
- 批量操作，管理更高效

### 11.3 下一步行动

1. **验证可行性** (1-2 天)
   - 搭建 Tauri PoC
   - 验证与核心库集成
   - 测试基本 IPC 通信

2. **技术选型确认** (1 天)
   - React vs Vue vs Svelte
   - 组件库选择 (shadcn/ui vs Ant Design)
   - 状态管理方案

3. **开始开发** (按计划执行)

---

**文档版本**: v1.0  
**最后更新**: 2026-04-07  
**作者**: SkillStack Development Team

---

**准备好开始实现了吗？** 🚀
