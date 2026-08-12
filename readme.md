# MySkills

个人维护的 Codex Skills 仓库，附带一个本地 Skill Playground。它可以浏览、筛选和评价本地 Skills，调用 AI 生成结构化用途与风险结论，也可以把任务原样交给本机 Codex CLI 执行，并展示对话、运行日志和生成产物。Skill 文件维护由内置的 `MySkills 管理` 智能体通过自然语言完成。

启动后访问：<http://127.0.0.1:8765/>

Skill 的当前分类、功能和测试状态以展示页面为准，README 不再维护容易过期的 Skill 数量与名单。

## 环境要求

- Windows 10/11 与 PowerShell 5.1 或更高版本。
- Python 3.10 或更高版本，并可通过 `python` 命令调用。
- 已安装并登录 Codex Desktop 或 Codex CLI。Playground 会优先自动发现 Codex Desktop 自带的 CLI，然后检查 VS Code 和系统 `PATH`。
- 如需在页面中拉取或推送代码，还需要 Git；推荐安装 Git Credential Manager，并提前完成远程仓库登录。

前端使用原生 HTML、CSS 和 ES Modules，不需要安装 Node.js、React、Vite，也没有前端构建步骤。

## 安装

克隆或下载仓库后，在 PowerShell 中进入项目目录：

```powershell
cd C:\path\to\myskills
```

推荐创建独立的 Python 虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\playground\requirements.txt
```

当前 Python 依赖只有 PyYAML。也可以不创建虚拟环境，启动脚本会使用当前 `python` 自动安装 `playground/requirements.txt` 中的依赖。

如果 PowerShell 阻止激活脚本，可只对当前终端临时放开：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

## 配置

主要配置位于 `config.yaml`：

| 配置 | 用途 |
|---|---|
| `server.host` / `server.port` | 本地服务监听地址和端口，默认 `127.0.0.1:8765` |
| `agent.default_model` | 页面默认选择的模型 |
| `codex_cli.path` | Codex CLI 路径；保持 `auto` 可自动发现 |
| `codex_cli.sandbox` | Codex CLI 沙箱权限，例如 `workspace-write` 或 `danger-full-access` |
| `codex_cli.approval_policy` | CLI 审批策略；网页执行无法弹出终端审批 |
| `runs.directory` | 本地运行记录与产物目录，默认 `.runs` |
| `git.proxy_port` | Playground Git 操作使用的代理端口；`0` 表示关闭 |
| `models` | 页面可选模型及实际传给 Codex CLI 的模型 ID |

默认配置适合受信任的个人电脑，CLI 使用 `danger-full-access` 和 `never`。如果希望限制文件写入范围，可将 `codex_cli.sandbox` 改为 `workspace-write`，但部分需要访问项目外文件或本机工具的 Skill 可能无法完整执行。

Playground 本身使用 Codex 的本机认证，不要求 API key。只有所选 Skill 需要额外凭据时，才创建本地 `.env`：

```powershell
Copy-Item .env.example .env
```

然后填写该 Skill 需要的字段。`.env` 会传递给本机 Codex CLI 和子工具，但不会发送到浏览器，也已被 Git 忽略。不要在 README、Skill 文档或提交记录中填写真实密钥。

## 启动

在项目根目录运行：

```powershell
.\start-playground.ps1
```

脚本会安装 Python 依赖并启动服务。看到服务启动信息后，在浏览器打开：

<http://127.0.0.1:8765/>

如果只想手动启动：

```powershell
python -m pip install -r .\playground\requirements.txt
python .\playground\server.py
```

停止服务时，在启动它的终端中按 `Ctrl+C`。

## 使用

### 浏览与评价 Skill

- 使用顶部标签按“办公文档 / 图像演示 / 学术研究 / 内容媒体 / 开发工具 / 系统效率”浏览。
- 来源、测试状态、评分和关键词可以组合筛选；“自创 / 已测 / 待测”仍是目录维护属性，不再作为功能分类。
- 点击 Skill 卡片查看运行前提、需要提供的输入、能解决的问题、典型任务、具体输出附件、最终交付和安全风险评估。
- 安全风险评估只检查恶意代码、信息或凭据窃取、重大系统破坏以及明显或失控的资源占用；不会输出使用建议，也不会把版权、平台规则、正常联网或普通产物占用列为安全风险。
- 点击“AI 分析”会调用当前选择的模型静态分析 Skill 文件，并把结论保存到 `skill-insights.yaml`；分析不会执行该 Skill。
- 可为每个 Skill 设置 A/B/C 评分和备注，也可以自定义等级名称、说明与颜色。
- 评分数据保存在 `skill-metadata.yaml`，可随代码在不同设备间同步。

### 通过管理智能体维护 Skill

1. 在右侧“Skill 对话”中选择 `MySkills 管理`。
2. 直接描述目标，例如“搜索本机的 PDF Skill”“把这个目录导入待测”“将某个 Skill 移到已测”“修改、删除或恢复某个 Skill”“同步项目状态”。
3. 管理智能体会检查仓库规则和现有改动，完成 Skill 的搜索、导入、创建、增删改查、分类移动与元数据迁移。
4. 发生项目修改时，它会同步目录数据和 `PROJECT_STATUS.md`，执行相关验证，并按约定 commit、push。通过网页运行时不会重启承载当前任务的 Playground：Skill 目录会动态注册，静态页面刷新后生效；只有后端或启动配置确实需要重载时才会提示任务返回后再重启。只读搜索和比较不会产生提交。

外部 Skill 默认进入 `待测skills/`；只有实际验证过关键流程后才移动到 `已测skills/`。删除默认移入本地 `.skill-trash/`，不会直接永久清除。真实凭据、`.env`、私钥、缓存和运行产物不会被导入或提交。

### 执行 Skill

1. 在右侧“Skill 对话”中选择 Skill 和模型。
2. 输入任务；需要本地文件时可以点击“添加附件”多选文件，或直接把文件拖入输入区域。
3. 点击“发送”。附件会保存到本地 `.runs/uploads/<conversation-id>/`，并以页面中可见的绝对路径附在用户消息后面。
4. 页面只会添加 Codex 原生的 `$skill-name` 选择标记；用户输入及页面可见的附件路径会原样交给 Codex，不附加隐藏要求。
5. 本机 Codex CLI 负责读取 `SKILL.md`、附件、调用工具并维护多轮 session。
6. 回答以 Markdown 显示；运行产生的图片、音频、视频、HTML 和其他文件会显示在对应消息下。

普通 Skill 会在独立的 `.runs/<run-id>/workspace/` 中执行，产物不会混入项目根目录；只有 `MySkills 管理` 会直接操作项目目录。

任务开始后，“发送”按钮会变为红色“停止”。点击后只终止当前对话对应的 Codex CLI 及其子进程，并把该次运行标记为“已停止”；不会重复提交任务，也不会影响其他正在执行的对话。

当前附件上传不限制文件类型、单文件大小或总大小；文件只保存在本机并已被 Git 忽略。

点击“新对话”或切换 Skill 会创建新的 Codex session。拖动页面中间的分隔条可以调整右侧对话栏宽度。

### 同步项目

“项目管理”面板可以查看分支、远程同步状态、本地改动和逐文件 Diff，并执行：

- 刷新本地状态。
- 检查远程更新。
- 在工作区干净时执行 `git pull --ff-only`。
- 明确勾选文件后 commit，并立即 push 当前分支。
- 设置只对 Playground Git 命令生效的本机代理端口。

Push 凭据只由 Git Credential Manager 提供，页面不接收或保存 PAT。提交操作不会执行 `git add -A`，敏感文件、运行产物及已有外部暂存改动也不能从页面提交。

## 文档职责

- 当前 Skill 分类、功能、详情和评分：本地展示页面。
- 模块、接口、模型和 Skill 目录状态：[PROJECT_STATUS.md](PROJECT_STATUS.md)（自动生成）。
- 仓库结构、Skill 变更同步规则和安全边界：[AGENTS.md](AGENTS.md)。
- 单个 Skill 的完整说明：对应目录中的 `SKILL.md`。

修改模块或配置后，可手动刷新状态文档：

```powershell
python .\playground\generate_project_status.py
```

服务启动时也会自动执行一次同步。

## 安全提示

- Playground 仅适合本机使用。不要把 `127.0.0.1` 改为局域网或公网地址，除非已经额外实现认证和权限隔离。
- `.env`、`.runs/`（包括上传附件）、`.skill-trash/`、日志、证书、私钥和 `secrets.*` 均不应进入 Git。
- 默认 Codex CLI 权限较高，执行不熟悉的 Skill 前应先查看其详情和 `SKILL.md`。
- Runner 只负责选择 Skill、转发用户原文和接收结果；需要改变输出规范时，应修改对应 Skill，而不是在 Runner 中加入隐藏提示词。
