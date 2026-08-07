# 项目模块状态

> 本文档由 `python playground/generate_project_status.py` 自动生成。请勿手工维护统计表；服务启动时也会自动同步。

## 当前概况

- Skill 总数：**38**
- 前端架构：原生 HTML + CSS + ES Modules，无构建步骤
- 执行后端：本机 Codex CLI（sandbox：`danger-full-access`，approval：`never`）
- 提示词策略：仅添加显式 `$skill-name` 选择标记，用户输入原样转发，无 Runner 行为提示
- 服务地址：`http://127.0.0.1:8765`
- 可选模型：`gpt-5.6-terra`、`gpt-5.6-sol`、`deepseek-v4-flash`
- Git 代理：`http://127.0.0.1:7897`（端口 `0` 表示关闭）

## 模块状态

| 文件 | 模块职责 | 状态 | 大小 | 对外导出 | 当前功能 |
|---|---|---|---:|---|---|
| `skills-showcase.html` | 页面外壳 | 正常 | 16,760 B | — | 保留语义化 HTML、卡片容器、详情弹窗和右侧对话区域 |
| `playground/static/styles.css` | 样式系统 | 正常 | 19,214 B | — | 负责响应式布局、卡片、对话、日志和产物预览样式 |
| `playground/static/js/data.js` | Skill 数据 | 正常 | 17,615 B | `repositorySkills`, `skillDetails` | 维护自创 Skill 详情以及已测/待测 Skill 展示元数据 |
| `playground/static/js/catalog.js` | 目录交互 | 正常 | 5,729 B | `initializeCatalog` | 渲染仓库 Skill 卡片、分类标签和详情弹窗 |
| `playground/static/js/api.js` | API 客户端 | 正常 | 2,298 B | `apiBase`, `getRunnerConfig`, `createRun`, `getRun`, `getRatings`, `saveRatingLevels`, `saveSkillRating`, `getGitStatus`, `getGitDiff`, `fetchGitUpdates`, `pullGitUpdates`, `commitAndPushGit`, `saveGitProxyPort` | 封装配置读取、任务创建和运行状态查询 |
| `playground/static/js/artifacts.js` | 产物渲染 | 正常 | 1,760 B | `createArtifacts` | 预览图片、音频、视频、HTML 和普通文件 |
| `playground/static/js/markdown.js` | Markdown 渲染 | 正常 | 3,694 B | `renderMarkdown` | 安全渲染标题、列表、引用、代码和外部链接，不执行原始 HTML |
| `playground/static/js/resize.js` | 面板缩放 | 正常 | 2,691 B | `initializePanelResize` | 拖动或用键盘调整对话栏宽度，并在浏览器本地记忆 |
| `playground/static/js/chat.js` | 对话状态 | 正常 | 6,765 B | `initializeChat` | 管理模型/Skill 选择、Codex session、轮询、日志、Markdown 和消息 |
| `playground/static/js/ratings.js` | 评分交互 | 正常 | 4,031 B | `initializeRatings` | 管理 A/B/C 评分、备注、筛选和等级显示设置 |
| `playground/static/js/git-panel.js` | Git 项目管理 | 正常 | 6,461 B | `initializeGitPanel` | 展示状态与 Diff，并触发 fetch、ff-only pull、选择性 commit/push |
| `playground/static/js/app.js` | 前端编排 | 正常 | 872 B | — | 组合目录、对话与面板缩放模块并选择默认 Skill |
| `playground/server.py` | 本地 Runner | 正常 | 23,160 B | — | 注册原始 Skills，以 `$skill-name` 加用户原文桥接 Codex CLI，提供运行状态并执行静态资源白名单 |
| `playground/rating_service.py` | 评分服务 | 正常 | 4,599 B | — | 校验并原子更新可进入 Git 的 skill-metadata.yaml |
| `playground/git_service.py` | Git 服务 | 正常 | 10,907 B | — | 执行白名单 Git 参数、保护敏感文件并通过 GCM 推送 |
| `skill-metadata.yaml` | 维护数据 | 正常 | 429 B | — | 保存 A/B/C 显示设置、Skill 评分和备注，随 Git 同步 |
| `playground/generate_project_status.py` | 状态文档生成器 | 正常 | 8,551 B | — | 扫描模块、配置与 Skill 目录并更新本文件 |

## 数据与调用关系

```text
skills-showcase.html
└─ app.js
   ├─ data.js
   ├─ catalog.js
   ├─ ratings.js ──> rating_service.py ──> skill-metadata.yaml
   ├─ git-panel.js ──> git_service.py ──> Git / GCM / origin
   └─ chat.js
      ├─ api.js ──> server.py ──> Codex CLI
      ├─ markdown.js
      ├─ artifacts.js <── .runs/<run-id>/
      └─ resize.js
```

## 后端接口

| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/config` | GET | 返回模型、默认模型和 Codex CLI 可用状态 |
| `/api/runs` | POST | 创建新的 Codex CLI 执行或续接已有 session |
| `/api/runs/<run-id>` | GET | 查询状态、日志、答复、session 和产物 |
| `/api/runs/<run-id>/files/<path>` | GET | 在页面中预览或下载本次运行产物 |
| `/api/ratings` | GET | 读取评分等级、Skill 评分和备注 |
| `/api/ratings/settings` | POST | 更新 A/B/C 的名称、说明和颜色 |
| `/api/ratings/skill` | POST | 更新或清除单个 Skill 评分 |
| `/api/git/status` | GET | 读取分支、远程同步和本地改动状态 |
| `/api/git/diff?path=...` | GET | 读取安全改动文件的文本 Diff |
| `/api/git/fetch` | POST | 检查并刷新 origin 远程引用 |
| `/api/git/pull` | POST | 在干净工作区执行 `pull --ff-only` |
| `/api/git/commit-push` | POST | 提交明确选择的文件并立即通过 GCM push |
| `/api/git/proxy` | POST | 保存项目级 Git 代理端口，0 表示关闭 |

## Skill 分类状态

| 分类 | 目录 | 数量 | Skill |
|---|---|---:|---|
| 自创 | `自创skills/` | 11 | `arxiv-search`、`douyin-video-downloader`、`gpt-image`、`html-ppt-build`、`local-credential-memory`、`mineru-to-markdown`、`ppt-technical-redesign`、`semantic-scholar-search`、`temporary-public-file-links`、`video-narration-tts`、`xiaohongshu-note-downloader` |
| 已测 | `已测skills/` | 7 | `codex-ppt-skill`、`dashiai-ppt`、`imagegen`、`openai-docs`、`professor-synapse`、`skill-creator`、`skill-installer` |
| 待测 | `待测skills/` | 20 | `canvas-design`、`create-plan`、`develop-web-game`、`docx`、`films-search`、`frontend-design`、`frontend-slides`、`imap-smtp-email`、`local-tools`、`music-search`、`pdf`、`playwright`、`pptx`、`remotion`、`scheduled-task`、`seedance`、`seedream`、`technology-news-search`、`web-search`、`xlsx` |

## 同步规则

- 修改前端模块、Runner、配置或 Skill 后，执行 `python playground/generate_project_status.py`。
- `start-playground.ps1` 启动服务时会再次自动生成本文档，确保模块存在状态、文件大小、模型和 Skill 数量同步。
- Skill 名称、分类、功能说明变化时，仍需同步维护 `readme.md` 与 `playground/static/js/data.js` 中的展示信息。
- 修改 Playground 后必须重启，并检查 `/api/config`、页面模块加载、分类切换、详情弹窗和对话发送按钮。
