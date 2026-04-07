# SkillStack 阶段总结与规划

**更新日期**: 2026-04-07  
**当前版本**: v0.1.0-mvp  

---

## 📊 第一阶段 (MVP) - 完成总结

### ✅ 完成状态: 100%

**目标**: 构建中央仓库管理全局Skill,实现单源真相和实时同步

**时间**: 2026-04-03 ~ 2026-04-07 (实际5天，原计划6天)

### 核心成果

#### 1. 功能完成度

| 类别 | 数量 | 状态 | 说明 |
|------|------|------|------|
| **P0核心命令** | 7/7 | ✅ 100% | init, list, add, edit, delete, sync, status |
| **P1高级命令** | 3/3 | ✅ 100% | import, show, doctor |
| **单元测试** | 8/8 | ✅ 通过 | 覆盖所有核心模块 |
| **集成测试** | 1/1 | ✅ 通过 | 完整工作流验证 |
| **Claude集成** | - | ✅ 验证通过 | 实时同步验证 |

#### 2. 技术实现

**架构设计**:
```
~/.skillstack/repository/     # 中央仓库(单源真相)
    ├── skill-1/SKILL.md
    └── skill-2/SKILL.md
~/.skillstack/manifest.json   # 状态追踪(hash, 时间戳)
~/.skillstack/config.json     # 配置(编辑器, 自动同步)
~/.claude/skills -> repository  # 目录级symlink
```

**核心特性**:
- ✅ **单源真相**: 所有Skill集中在中央仓库,避免版本漂移
- ✅ **实时同步**: symlink机制实现零延迟同步(无需手动sync)
- ✅ **完整CRUD**: 创建、查询、编辑、删除一应俱全
- ✅ **健康检查**: 自动检测和修复symlink/manifest问题
- ✅ **友好交互**: 彩色输出、表格展示、交互式确认

**技术栈**:
- Rust 2021 (高性能、类型安全)
- Clap 4.5 (CLI框架)
- serde_json/serde_yaml (序列化)
- sha2 (文件hash校验)
- chrono (时间处理)
- colored + dialoguer (交互体验)

#### 3. Claude Code 集成验证结果

**验证方法**: 观察Claude Code的`<system-reminder>`中skills列表变化

| 操作 | 验证内容 | 结果 |
|------|---------|------|
| `skillstack add` | 新skill立即出现在Claude | ✅ 通过 |
| 手动编辑SKILL.md | 修改立即在Claude生效 | ✅ 通过 |
| `skillstack delete` | skill立即从Claude消失 | ✅ 通过 |
| `skillstack import` | 导入skill立即可用 | ✅ 通过 |

**结论**: symlink方案完全满足实时同步需求,无需任何手动操作。

#### 4. 项目结构

```
SkillStack/
├── src/
│   ├── main.rs              # CLI入口
│   ├── lib.rs               # 库入口
│   ├── cli/commands.rs      # 10个命令实现
│   ├── core/
│   │   ├── skill.rs         # Skill结构+验证
│   │   ├── manifest.rs      # Manifest管理
│   │   ├── config.rs        # Config管理
│   │   ├── repository.rs    # Repository CRUD
│   │   └── sync.rs          # Symlink管理
│   └── utils/
│       ├── hash.rs          # SHA256计算
│       ├── frontmatter.rs   # YAML解析
│       ├── fs.rs            # 文件系统辅助
│       └── ui.rs            # UI辅助
├── tests/integration_test.rs # 集成测试
├── docs/
│   ├── 设计方案.md
│   ├── superpowers/specs/   # MVP详细设计
│   ├── superpowers/plans/   # MVP实现计划
│   └── MVP-COMPLETION-REPORT.md
├── Cargo.toml               # 依赖配置
├── README.md                # 用户文档
└── CHANGELOG.md             # 变更日志
```

#### 5. 已知限制

1. **平台支持**: 仅支持Unix(macOS/Linux), Windows需要junction或copy模式
2. **并发安全**: 未实现文件锁,多进程同时操作可能导致manifest不一致(低概率)
3. **编辑器集成**: 依赖系统编辑器,在非TTY环境可能有问题

---

## 🚀 第二阶段 - 项目级Skill管理 (详细计划)

### 目标

**核心痛点**: MVP只支持全局Skill,无法为不同项目定制不同的Skill集合

**解决方案**: 实现项目注册表+项目级Skill管理+override机制

### 时间估算: 2周 (10个工作日)

### 核心功能

#### 功能1: 项目注册表

**目标**: 支持管理多个项目,记录每个项目的Skill使用情况

**实现要点**:
- 项目扫描和注册(手动添加路径)
- 记录项目元数据(路径、名称、工具类型)
- 项目列表视图
- 批量导入(扫描指定目录下所有子项目)

**数据结构扩展**:
```json
// manifest.json 新增
{
  "version": "1.0",
  "skills": { ... },
  "sync_status": { ... },
  "projects": {                          // 新增
    "my-app": {
      "path": "/Users/xxx/projects/my-app",
      "tool": "claude",
      "registered_at": "2026-04-10T10:00:00Z",
      "installed_skills": ["skill-a", "skill-b"],
      "overrides": {
        "skill-a": {
          "hash": "sha256:xyz789...",
          "updated_at": "2026-04-10T11:00:00Z"
        }
      }
    }
  }
}
```

#### 功能2: 项目级CRUD

**目标**: 为特定项目安装/管理Skill

**核心操作**:
1. **安装到项目**: 从中央仓库复制Skill到项目`.claude/skills/`
2. **项目级override**: 项目可以修改Skill(覆盖全局版本)
3. **项目级删除**: 仅删除项目中的Skill(不影响全局)
4. **查看项目Skill**: 列出项目当前拥有的所有Skill

**优先级机制**:
```
项目级Skill > 全局Skill
(符合Claude Code官方优先级: Project > User > Bundled)
```

#### 功能3: 同步管理

**目标**: 支持灵活的同步策略

**同步模式**:
1. **同步到单个项目**: `skillstack sync --project my-app`
2. **同步到所有项目**: `skillstack sync --all-projects`
3. **增量同步**: 仅同步变更的Skill(检测hash差异)
4. **选择性同步**: 指定Skill列表同步

**同步方式**:
- 全局 → 项目: copy模式(不能用symlink,需要支持override)
- 自动检测变更: 对比hash,仅同步有变化的文件

#### 功能4: 视图优化

**目标**: 清晰展示项目和Skill的关系

**新增视图**:
1. **项目列表**: 显示所有注册项目+Skill数量+最后同步时间
2. **项目详情**: 显示项目拥有的Skill+override标记
3. **Skill使用情况**: 显示Skill被哪些项目使用
4. **Override对比**: diff视图显示项目版本vs全局版本差异

### 新增命令设计

#### 命令1: `skillstack project add`

**功能**: 注册新项目

**语法**:
```bash
skillstack project add <PATH> [OPTIONS]
```

**选项**:
- `--name <NAME>`: 指定项目名称(默认从路径推断)
- `--tool <claude|cursor>`: 指定工具类型(默认claude)
- `--scan-skills`: 扫描并记录项目现有Skill

**输出示例**:
```
✅ 项目 'my-app' 已注册
📂 路径: /Users/xxx/projects/my-app
🔍 发现 3 个现有 skills: skill-a, skill-b, skill-c
```

#### 命令2: `skillstack project list`

**功能**: 列出所有注册项目

**语法**:
```bash
skillstack project list [OPTIONS]
```

**选项**:
- `--sort <name|path|skills|updated>`: 排序方式
- `--reverse`: 反向排序

**输出示例**:
```
NAME        PATH                          SKILLS  LAST_SYNC
my-app      /Users/xxx/projects/my-app    5       2h ago
demo        /Users/xxx/projects/demo      3       1d ago
```

#### 命令3: `skillstack project remove`

**功能**: 取消注册项目(不删除文件)

**语法**:
```bash
skillstack project remove <NAME> [OPTIONS]
```

**选项**:
- `--force`: 跳过确认

#### 命令4: `skillstack project sync`

**功能**: 同步Skill到指定项目

**语法**:
```bash
skillstack project sync <PROJECT_NAME> [OPTIONS]
```

**选项**:
- `--skills <SKILL1,SKILL2>`: 指定Skill列表(默认全部)
- `--force`: 强制覆盖(即使hash相同)
- `--dry-run`: 模拟运行,不实际写入

**输出示例**:
```
🔄 同步 'my-app'...
✅ 已同步 skill-a (新增)
✅ 已同步 skill-b (更新)
⏭️  跳过 skill-c (已是最新)
✅ 同步完成: 2 个 skill
```

#### 命令5: `skillstack install`

**功能**: 安装Skill到项目

**语法**:
```bash
skillstack install <SKILL_NAME> --project <PROJECT_NAME> [OPTIONS]
```

**选项**:
- `--project <NAME>`: 目标项目
- `--all-projects`: 安装到所有项目

**输出示例**:
```
✅ 已安装 'skill-debug' 到项目 'my-app'
📂 路径: /Users/xxx/projects/my-app/.claude/skills/skill-debug
```

#### 命令6: `skillstack uninstall`

**功能**: 从项目卸载Skill(不影响全局)

**语法**:
```bash
skillstack uninstall <SKILL_NAME> --project <PROJECT_NAME>
```

#### 命令7: `skillstack list --project`

**功能**: 增强现有list命令,支持查看项目Skill

**语法**:
```bash
skillstack list --project <NAME>
```

**输出示例**:
```
NAME          SOURCE    DESCRIPTION
skill-a       override  项目定制版本
skill-b       global    全局版本
skill-c       local     项目专属
```

**说明**:
- `override`: 覆盖全局版本
- `global`: 使用全局版本
- `local`: 项目独有,不存在于全局

#### 命令8: `skillstack diff`

**功能**: 对比项目版本和全局版本差异

**语法**:
```bash
skillstack diff <SKILL_NAME> --project <PROJECT_NAME>
```

**输出示例**:
```
Diff for 'skill-a':
  Global: sha256:abc123...
  Project (my-app): sha256:xyz789...
  
  Changes:
  - Line 5: - description: "Old"
  + Line 5: + description: "New"
```

### 数据模型设计

#### Project 结构

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Project {
    pub name: String,
    pub path: String,
    pub tool: String,  // "claude" | "cursor" | ...
    pub registered_at: String,
    pub installed_skills: Vec<String>,
    pub overrides: HashMap<String, SkillOverride>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillOverride {
    pub hash: String,
    pub updated_at: String,
}
```

#### Manifest 扩展

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Manifest {
    pub version: String,
    pub skills: HashMap<String, Skill>,
    pub sync_status: SyncStatus,
    pub projects: HashMap<String, Project>,  // 新增
}
```

### 核心流程设计

#### 流程1: 注册项目并安装Skill

```
1. skillstack project add /path/to/my-app
   ├─ 验证路径存在
   ├─ 检测工具类型(查找.claude/目录)
   ├─ 扫描现有skills(可选)
   ├─ 添加到manifest.projects
   └─ 输出注册成功

2. skillstack install skill-debug --project my-app
   ├─ 验证skill存在于全局仓库
   ├─ 验证project已注册
   ├─ 复制skill到项目目录
   │  source: ~/.skillstack/repository/skill-debug/
   │  dest:   /path/to/my-app/.claude/skills/skill-debug/
   ├─ 更新manifest.projects[my-app].installed_skills
   └─ 输出安装成功
```

#### 流程2: 项目级Override

```
用户场景: 项目需要定制某个Skill

1. 用户手动编辑项目中的Skill
   编辑: /path/to/my-app/.claude/skills/skill-a/SKILL.md

2. skillstack project sync my-app (检测到变更)
   ├─ 扫描项目skills目录
   ├─ 对比hash差异
   ├─ 发现skill-a被修改(hash不匹配)
   ├─ 记录为override
   │  manifest.projects[my-app].overrides[skill-a] = {
   │    hash: "新hash",
   │    updated_at: "当前时间"
   │  }
   └─ 输出: "⚠️ 检测到 skill-a 被项目覆盖"

3. skillstack list --project my-app
   输出:
   NAME      SOURCE    DESCRIPTION
   skill-a   override  项目定制版本 (与全局版本不同)
```

#### 流程3: 全局更新 → 项目同步

```
场景: 全局Skill更新后,同步到所有项目

1. skillstack edit skill-shared
   (编辑全局Skill)

2. skillstack project sync --all-projects
   ├─ 遍历所有项目
   ├─ 对于每个项目:
   │  ├─ 检查是否安装了skill-shared
   │  ├─ 检查是否有override(如果有,询问是否覆盖)
   │  ├─ 对比hash差异
   │  └─ 如果不同,复制新版本
   └─ 输出同步报告:
      ✅ my-app: 已更新 skill-shared
      ⏭️  demo: 跳过 skill-shared (项目已override)
```

### 新增模块设计

#### 模块: `src/core/project.rs`

**职责**: 项目管理

```rust
pub struct ProjectManager {
    base_path: PathBuf,
}

impl ProjectManager {
    pub fn new(base_path: &Path) -> Self;
    pub fn register_project(&mut self, path: &str, name: Option<&str>, tool: &str) -> Result<()>;
    pub fn unregister_project(&mut self, name: &str) -> Result<()>;
    pub fn list_projects(&self) -> Result<Vec<Project>>;
    pub fn get_project(&self, name: &str) -> Result<&Project>;
    pub fn install_skill(&mut self, project_name: &str, skill_name: &str) -> Result<()>;
    pub fn uninstall_skill(&mut self, project_name: &str, skill_name: &str) -> Result<()>;
    pub fn sync_project(&mut self, project_name: &str, skill_names: Option<Vec<&str>>) -> Result<SyncReport>;
    pub fn detect_overrides(&mut self, project_name: &str) -> Result<Vec<String>>;
}
```

#### 模块: `src/core/diff.rs`

**职责**: Diff对比

```rust
pub struct DiffEngine;

impl DiffEngine {
    pub fn compare_skills(&self, global_path: &Path, project_path: &Path) -> Result<SkillDiff>;
    pub fn format_diff(&self, diff: &SkillDiff) -> String;
}

pub struct SkillDiff {
    pub global_hash: String,
    pub project_hash: String,
    pub changes: Vec<String>,  // Diff行
}
```

### 测试策略

#### 单元测试

**新增测试模块**:
- `project::tests` - 项目注册/列表/删除
- `project::tests::install` - Skill安装/卸载
- `project::tests::sync` - 同步逻辑
- `project::tests::override` - Override检测
- `diff::tests` - Diff对比

**测试覆盖**:
- [ ] 注册项目成功
- [ ] 注册重复项目失败
- [ ] 注册不存在路径失败
- [ ] 安装Skill成功
- [ ] 安装不存在Skill失败
- [ ] 同步检测hash差异
- [ ] Override检测和记录
- [ ] Diff对比正确性

#### 集成测试

**新增测试场景**:

```rust
#[test]
fn test_project_workflow() {
    // 1. 注册项目
    // 2. 安装2个skills
    // 3. 修改其中1个(模拟override)
    // 4. 同步检测override
    // 5. 全局更新skill
    // 6. 同步到项目
    // 7. 验证override未被覆盖
}
```

### 风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| 复制模式性能差 | 中 | 中 | 实现增量同步(仅复制变更文件) |
| Override冲突难以理解 | 中 | 高 | 提供清晰的diff视图+交互式提示 |
| Manifest膨胀 | 低 | 低 | 添加清理命令,移除未注册项目 |
| 多项目同步耗时 | 中 | 中 | 添加并发同步支持 |

### 开发任务分解 (10天)

#### Week 1 (Day 1-5)

**Day 1-2: 数据结构+项目注册**
- [ ] 扩展Manifest结构(projects字段)
- [ ] 实现Project结构
- [ ] 实现project add/remove/list命令
- [ ] 编写单元测试

**Day 3-4: Skill安装+项目同步**
- [ ] 实现install/uninstall命令
- [ ] 实现project sync命令
- [ ] 实现hash对比逻辑
- [ ] 编写单元测试

**Day 5: Override检测**
- [ ] 实现override检测逻辑
- [ ] 更新manifest记录override
- [ ] 增强list命令(显示override标记)

#### Week 2 (Day 6-10)

**Day 6-7: Diff功能**
- [ ] 实现diff命令
- [ ] 实现文件级diff对比
- [ ] 格式化输出

**Day 8: 批量操作**
- [ ] 实现--all-projects选项
- [ ] 实现并发同步(可选)
- [ ] 同步报告汇总

**Day 9: 测试+优化**
- [ ] 完成所有单元测试
- [ ] 完成集成测试
- [ ] 性能优化(大量项目场景)

**Day 10: 文档+发布**
- [ ] 更新README(新命令文档)
- [ ] 编写使用示例
- [ ] 手动测试清单
- [ ] 创建release tag v0.2.0

### 成功标准

阶段2完成当且仅当:

1. ✅ 8个新命令全部可用(project add/list/remove/sync, install/uninstall, diff, list --project)
2. ✅ 单元测试覆盖率 > 80%
3. ✅ 集成测试通过
4. ✅ 能正确处理项目级override
5. ✅ 同步性能可接受(10个项目 < 5秒)
6. ✅ 文档更新完整

---

## 🔮 第三阶段 - 完善与优化 (概要)

**时间**: 1-2周

**核心功能**:
1. **版本管理**: 语义化版本、项目级版本锁定、diff对比、回滚
2. **批量操作**: 选中多个skill批量操作、选中多个项目批量同步
3. **多工具适配**: Cursor支持、OpenCode支持
4. **CLI增强**: 过滤选项、JSON输出模式、自动补全

**优先级**: MEDIUM (根据用户反馈调整)

---

## 🎯 总结

### 第一阶段核心价值

✅ **已实现**: "Install once, edit once, work everywhere"
- 全局Skill的单源真相管理
- 实时同步(symlink)
- 完整的CRUD操作
- 健康检查和修复

### 第二阶段核心价值

🚀 **待实现**: "Per-project customization with centralized management"
- 多项目管理
- 项目级Skill定制(override)
- 灵活的同步策略
- 全局更新 + 项目隔离

### 长期愿景

🌟 **终极目标**: 成为AI辅助开发工具的"包管理器"
- 阶段1+2: 个人开发者痛点解决
- 阶段3: 高级特性完善
- 阶段4: 团队协作+技能市场

---

**文档结束**

最后更新: 2026-04-07  
作者: SkillStack Team
