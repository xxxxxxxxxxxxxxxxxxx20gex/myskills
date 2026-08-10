# Repository Instructions

本文件适用于整个 `myskills` 仓库。维护、移动、安装或删除任何 skill 时，都必须遵守以下约定。

## 项目用途

这是个人维护的 Codex skills 仓库。Skill 按来源和验证状态分为自创、已测、待测三类，并通过静态 HTML 页面提供目录导航。README 只负责项目安装、配置、启动和使用说明，不维护易过期的 Skill 数量与名单。

## 项目结构

```text
myskills/
├── AGENTS.md                  # 仓库级维护约定
├── readme.md                  # 项目介绍、环境安装、配置、启动与使用入口
├── PROJECT_STATUS.md          # 自动生成的模块、接口、配置与 Skill 状态
├── skills-showcase.html       # 页面语义结构，不再内嵌 CSS 与 JavaScript
├── config.yaml                # Skill Playground、Codex CLI 与模型参数
├── skill-metadata.yaml         # 可同步的 A/B/C 评分、备注与等级显示设置
├── .env.example               # 可选的 skill 环境变量示例
├── start-playground.ps1       # 本地执行器启动脚本
├── playground/                # Playground 后端与模块化静态资源
│   ├── server.py              # Codex CLI 桥接、运行状态和产物服务
│   ├── run_registry.py        # 线程安全且有界的运行记录存储
│   ├── rating_service.py      # Skill 评分读取、校验与原子持久化
│   ├── git_service.py         # Git 状态、Diff、ff-only pull 与选择性 commit/push
│   ├── skill_service.py       # Skill 扫描、导入导出、文件预览、回收删除和 AI 结论持久化
│   ├── generate_project_status.py # PROJECT_STATUS.md 自动生成器
│   ├── tests/                 # 后端状态与前端纯逻辑回归测试
│   └── static/
│       ├── styles.css         # 页面样式
│       └── js/
│           ├── app.js         # 前端启动编排
│           ├── data.js        # Skill 展示数据与功能分类归属
│           ├── catalog.js     # 功能分类、组合筛选、卡片和详情交互
│           ├── chat.js        # 对话与 Codex session 状态
│           ├── attachments.js # 附件选择、拖拽、缩略图、上传和状态管理
│           ├── attachment-prompt.js # 用户输入与可见附件路径的纯组合逻辑
│           ├── conversation-state.js # 防止重复任务与旧轮询污染的纯状态模块
│           ├── api.js         # Runner API 客户端
│           ├── artifacts.js   # 运行产物预览
│           ├── markdown.js    # 安全 Markdown 回复渲染
│           ├── resize.js      # 左右面板拖动缩放与宽度记忆
│           ├── ratings.js     # 卡片评分元数据和等级自定义
│           ├── skill-manager.js # Skill 导入、导出、删除、目录树和文件预览交互
│           └── git-panel.js   # Git/GCM 项目管理界面
├── .runs/                     # 本地运行产物，不进入 Git
├── .skill-trash/              # 页面删除 Skill 的本地回收目录，不进入 Git
├── .gitignore                 # 密钥、缓存、运行产物等忽略规则
├── 自创skills/                # 自主创建或深度定制的 skills
├── 已测skills/                # 已经过实际使用或验证的 skills
└── 待测skills/                # 已收集但仍需验证的 skills
```

## 分类规则

- `自创skills/`：由本仓库作者创建或针对本机环境深度定制，并由作者持续维护。
- `已测skills/`：已经完成实际使用、依赖检查或关键流程验证，可优先复用。
- `待测skills/`：已收集但尚未完成兼容性、依赖、安全性或实际效果验证。
- Skill 完成验证后，应从 `待测skills/` 移动到 `已测skills/`，不要在两个目录保留重复副本。
- 自创 skill 即使已经测试，也继续放在 `自创skills/`；其测试状态通过 Git 历史和文档说明维护。
- 页面中的维护标签是目录位置的唯一来源：标记为“自创 / 已测 / 待测”时，Skill 必须分别位于 `自创skills/`、`已测skills/`、`待测skills/`。人工更新标签必须移动整个目录，并同步迁移 `skill-metadata.yaml` 与 `skill-insights.yaml` 中的路径键。

## Skill 变更时必须同步文档

新增、复制、修改、重命名、移动或删除任何 skill 时，必须在同一个改动中同步检查并更新：

1. 展示页、实际目录扫描与 `playground/static/js/data.js`

   - 页面通过 `/api/skills` 扫描实际目录并动态更新总数；已有 Skill 的默认功能分类仍由 `skillCategories` 指定且只能有一个，页面导入的新 Skill 分类保存在 `skill-insights.yaml`。
   - 功能分类负责主导航；来源（自创/收集）、测试状态（已测/待测/未标注）和评分只作为组合筛选条件。
   - 自创 skill 变化时，更新 HTML 中的静态卡片和 `data.js` 的 `skillDetails` 详情数据。
   - 已测或待测 skill 变化时，更新 `data.js` 的 `repositorySkills` 名称、目录、状态、简介和 `SKILL.md` 章节。
   - Skill 在 `已测skills/` 与 `待测skills/` 之间移动时，只保留新状态的数据条目。
   - 保证每个实际 skill 都能在页面中找到，并可点击打开详细信息。
2. `PROJECT_STATUS.md`

   - 执行 `python playground/generate_project_status.py`，根据当前模块、配置和 Skill 目录自动更新。
   - 不手工编辑其中的统计表；需要改变说明时修改生成器。
   - Playground 服务启动时也会自动执行同步，但提交前仍应主动运行并检查 diff。

以下改动也视为需要同步：

- 修改 `SKILL.md` frontmatter 中的 `name` 或 `description`。
- 修改 skill 的核心能力、依赖、输出格式或使用边界。
- 调整目录名称或维护状态。
- 替换一个旧 skill 为职责不同的新 skill。

## 验证要求

完成 skill 或目录页面改动后，至少执行以下检查：

1. 统计 `自创skills/`、`已测skills/`、`待测skills/` 中包含 `SKILL.md` 的目录数量。
2. 确认总数与 `PROJECT_STATUS.md`、`skills-showcase.html` 的“全部”数字一致，并确认功能分类合计无遗漏、无重复。
3. 确认展示页的卡片集合与实际目录一致，没有遗漏、重复或已删除的条目。
4. 对 `playground/static/js/*.js` 执行语法检查，并用浏览器打开页面检查模块加载、标签页、卡片和详情弹窗。
   - 运行 `python -m unittest discover -s playground/tests -p "test_*.py" -v`。
   - 运行 `node playground/tests/test_catalog_data.mjs`。
   - 运行 `node playground/tests/test_conversation_state.mjs`。
5. 对新增或修改的 skill 运行 skill 结构验证；存在脚本时，按风险执行语法检查或代表性测试。
6. 提交前运行 `git diff --check` 并检查暂存文件列表。

修改 Skill Playground 时，还需要检查 `config.yaml` 可解析、Codex CLI 自动发现或显式路径有效、服务可启动、模型切换可见、session 续聊与路径校验有效，并至少完成一次接口冒烟测试。真实模型调用只有在用户授权且费用可控时执行。

前端继续使用无构建的原生 ES Modules。新增逻辑时按职责放入独立模块；避免重新把大段 CSS、数据或 JavaScript 内嵌到 `skills-showcase.html`。只有当项目明确迁移到新的前端框架时才整体调整此约定。

Skill 评分、备注与 A/B/C 显示设置统一写入 `skill-metadata.yaml`，该文件需要进入 Git 以便多设备同步。评分写入不得改动 Skill 本体；Skill 删除或移动后应同步清理或迁移对应评分路径。

AI 分析结论统一写入 `skill-insights.yaml`，只允许包含使用条件、解决的问题、使用场景、附件、最终结果、安全风险评估、模型和更新时间。安全风险评估只检查恶意代码、敏感信息或凭据窃取、重大系统破坏和明显或失控的资源占用；不得输出使用建议，不得把版权、平台规则、正常联网、普通文件保存或一般功能边界列为安全风险。AI 分析是独立的静态分析功能，不得通过 Runner 注入额外提示，也不得执行被分析 Skill。导入导出和文件预览必须复用 `skill_service.py` 的路径与敏感文件检查；页面删除只能移动到 `.skill-trash/`。

维护标签更新必须复用 `skill_service.py` 的受限移动逻辑，禁止覆盖目标目录中的同名 Skill，运行中禁止移动；移动成功后必须重新注册项目 Skill、刷新状态文档，并通过 `rating_service.py` 迁移评分和备注路径。

Runner 必须保持提示词透明：只允许把页面选择转换为 Codex 原生的 `$skill-name` 显式 Skill 标记，并在其后原样附加用户输入。不得在 Runner 中加入输出格式、产物目录、回答风格、自检、真实性检查、“不要撒谎”或其他会改变 Skill 原始效果的隐藏指令。需要这些行为时只能修改对应 Skill，并按 Skill 变更规则同步文档。

对话附件上传到 `.runs/uploads/<conversation-id>/`。附件路径必须作为用户消息中的可见文本显示，并将同一段文本原样交给 Runner，不得隐藏注入。当前版本按用户要求不限制附件类型、单文件大小或总大小；后续增加限制时必须同时更新前端提示、后端校验、README 和回归测试。

服务启动时通过 `.agents/skills/` 符号链接向 Codex 注册三个分类目录中的原始 Skill；该目录是生成状态并被 Git 忽略。链接必须指向实际 Skill 目录，不复制 `SKILL.md`，以免测试到过期副本。

每次修改 Skill Playground 的前端、后端、启动脚本或运行配置后，交付前必须重启本地服务，并确认 `http://127.0.0.1:8765` 可访问、`/api/config` 返回正常。除非用户明确要求停止，否则验证完成后保持服务运行。

## 安全规则

- 不读取、输出、提交或复制真实 `.env`、密码、API key、访问令牌、私钥、证书或 `secrets.*`。
- 只提交脱敏的 `.env_example` 或 `.env.example`。
- 添加新类型的本地凭据文件时，同步更新 `.gitignore`。
- 不把运行产物、缓存、下载文件或生成媒体提交到 skill 源码目录，除非它们是明确需要版本控制的示例或资产。
- 在推送前确认 Git 暂存区不含任何敏感文件或意外生成物。
- Playground 通过本机 Codex CLI 执行任务，默认可能拥有 `danger-full-access`；服务必须保持绑定 `127.0.0.1`，不得在没有额外认证与权限隔离的情况下暴露到局域网或公网。
- 本地 HTTP 服务只允许直接公开 `skills-showcase.html` 与 `playground/static/` 下的页面资源。Skill 源码只能通过路径受限、类型受限、大小受限且会屏蔽敏感文件的 `/api/skills/file` 读取；不得使用仓库根目录通用静态服务暴露 `.env`、`.git`、配置文件或其他本地文件。

## Git 与维护边界

- 保留用户已有的未提交改动，不覆盖或回滚无关内容。
- 只提交当前任务涉及的 skill、展示页和必要维护文件。只有安装、配置、启动或使用方式变化时才同步 README。
- 不使用破坏性 Git 操作清理工作区。
- 只有用户明确要求时才推送远程仓库。
- Playground 的项目管理只能执行代码中明确列出的 Git 子命令；拉取固定使用 `git pull --ff-only`。
- 网页 commit 必须由用户明确勾选文件，不得使用 `git add -A`；敏感文件、运行产物和外部已暂存改动必须阻止。
- 网页 commit 成功后必须立即 push 当前分支；push 失败时保留本地 commit 并清楚报告 commit ID，不自动回滚。
- PAT 只由系统 Git Credential Manager 保存和提供。不得在网页、项目配置、日志、Local Storage 或仓库文件中读取、输入、缓存或显示 PAT。
- Git 代理端口保存在 `config.yaml`，只允许 0–65535 的整数；`0` 表示关闭。代理应通过单次 Git 命令参数生效，不修改用户的系统代理或全局 Git 配置。
- 后续增加 Skill 创建、编辑或移动功能时，必须复用本节安全边界，并同时更新展示数据和 `PROJECT_STATUS.md`；只有用户使用流程发生变化时才更新 README。
