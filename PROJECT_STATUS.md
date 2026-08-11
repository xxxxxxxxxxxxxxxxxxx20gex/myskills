# 项目模块状态

> 本文档由 `python playground/generate_project_status.py` 自动生成。请勿手工维护统计表；服务启动时也会自动同步。

## 当前概况

- Skill 总数：**42**
- 前端架构：原生 HTML + CSS + ES Modules，无构建步骤
- 执行后端：本机 Codex CLI（sandbox：`danger-full-access`，approval：`never`）
- 提示词策略：仅添加显式 `$skill-name` 选择标记，用户输入原样转发，无 Runner 行为提示
- 服务地址：`http://127.0.0.1:8765`
- 可选模型：`gpt-5.6-terra`、`gpt-5.6-sol`、`deepseek-v4-flash`
- Git 代理：`http://127.0.0.1:7897`（端口 `0` 表示关闭）

## 模块状态

| 文件 | 模块职责 | 状态 | 大小 | 对外导出 | 当前功能 |
|---|---|---|---:|---|---|
| `skills-showcase.html` | 页面外壳 | 正常 | 10,788 B | — | 保留语义化 HTML、动态卡片容器、AI 详情、评分、项目版本管理和右侧对话区域 |
| `playground/static/styles.css` | 样式系统 | 正常 | 25,129 B | — | 负责响应式布局、卡片、对话、Git 操作反馈、日志和产物预览样式 |
| `playground/static/js/data.js` | Skill 辅助数据 | 正常 | 21,478 B | `repositorySkills`, `skillDetails`, `skillCategories` | 维护已有 Skill 的展示别名、视觉样式和默认功能分类 |
| `playground/static/js/catalog.js` | 目录交互 | 正常 | 11,328 B | `initializeCatalog` | 根据后端实际目录渲染分类、组合筛选、AI 分析结论和详情弹窗 |
| `playground/static/js/api.js` | API 客户端 | 正常 | 3,137 B | `apiBase`, `getRunnerConfig`, `createRun`, `getRun`, `cancelRun`, `getRatings`, `saveRatingLevels`, `saveSkillRating`, `getGitStatus`, `getGitDiff`, `fetchGitUpdates`, `pullGitUpdates`, `commitAndPushGit`, `saveGitProxyPort`, `getSkills`, `analyzeSkill`, `uploadAttachment` | 封装配置、目录、AI 分析、评分、Git、附件、任务和运行状态接口 |
| `playground/static/js/artifacts.js` | 产物渲染 | 正常 | 1,760 B | `createArtifacts` | 预览图片、音频、视频、HTML 和普通文件 |
| `playground/static/js/markdown.js` | Markdown 渲染 | 正常 | 6,488 B | `renderMarkdown` | 安全渲染标题、表格、任务列表、引用、代码和外部链接，不执行原始 HTML |
| `playground/static/js/resize.js` | 面板缩放 | 正常 | 2,691 B | `initializePanelResize` | 拖动或用键盘调整对话栏宽度，并在浏览器本地记忆 |
| `playground/static/js/chat.js` | 对话状态 | 正常 | 9,599 B | `initializeChat` | 管理模型/Skill 选择、Codex session、停止任务、断线重连轮询、日志、Markdown 和消息 |
| `playground/static/js/attachments.js` | 附件交互 | 正常 | 3,174 B | `initializeAttachments` | 管理多选、拖拽、图片缩略图、移除、上传和附件状态 |
| `playground/static/js/attachment-prompt.js` | 附件提示组合 | 正常 | 260 B | `composeAttachmentPrompt` | 把用户输入与上传后的本地绝对路径组合为页面可见且原样转发的消息 |
| `playground/static/js/conversation-state.js` | 对话运行状态 | 正常 | 529 B | `createConversationState` | 隔离对话代次，阻止重复任务和过期轮询污染当前会话 |
| `playground/static/js/ratings.js` | 评分交互 | 正常 | 3,845 B | `initializeRatings` | 管理 A/B/C 评分、备注和等级显示设置，并向目录筛选器同步评分元数据 |
| `playground/static/js/git-panel.js` | Git 项目管理 | 正常 | 8,029 B | `initializeGitPanel` | 展示状态与 Diff，提供 Git 操作按钮的执行反馈，并触发 fetch、ff-only pull、选择性 commit/push |
| `playground/static/js/app.js` | 前端编排 | 正常 | 1,169 B | — | 读取实际 Skill 目录并组合目录、评分、Git、对话与面板缩放模块 |
| `playground/server.py` | 本地 Runner | 正常 | 34,908 B | — | 注册原始 Skills，桥接 Codex CLI，提供运行与 AI 分析接口并执行静态资源白名单 |
| `playground/skill_service.py` | Skill 目录服务 | 正常 | 5,834 B | — | 扫描三类 Skill 目录，过滤 AI 分析输入中的敏感文件并持久化分析结论 |
| `playground/run_registry.py` | 运行记录 | 正常 | 4,263 B | — | 将有界运行状态、日志和产物元数据线程安全地持久化到 .runs，支持服务重启恢复 |
| `playground/rating_service.py` | 评分服务 | 正常 | 4,599 B | — | 校验并原子更新可进入 Git 的 skill-metadata.yaml |
| `playground/git_service.py` | Git 服务 | 正常 | 10,907 B | — | 执行白名单 Git 参数、保护敏感文件并通过 GCM 推送 |
| `skill-metadata.yaml` | 维护数据 | 正常 | 588 B | — | 保存 A/B/C 显示设置、Skill 评分和备注，随 Git 同步 |
| `skill-insights.yaml` | AI 分析数据 | 正常 | 6,896 B | — | 保存功能分类、用途结论和仅针对恶意行为/信息窃取/系统破坏/重大资源占用的安全评估 |
| `playground/generate_project_status.py` | 状态文档生成器 | 正常 | 11,722 B | — | 扫描模块、配置与 Skill 目录并更新本文件 |
| `playground/tests/test_run_registry.py` | 后端回归测试 | 正常 | 3,409 B | — | 验证运行记录隔离、清理、取消、持久化和服务重启恢复逻辑 |
| `playground/tests/test_run_cancel.py` | 停止任务回归测试 | 正常 | 1,798 B | — | 验证停止请求终止指定进程并持久化 canceled 状态 |
| `playground/tests/test_skill_service.py` | Skill 目录回归测试 | 正常 | 3,283 B | — | 验证目录扫描、分析输入凭据过滤和分析结果持久化 |
| `playground/tests/test_conversation_state.mjs` | 前端状态回归测试 | 正常 | 758 B | — | 验证重复任务拦截和旧对话代次失效逻辑 |
| `playground/tests/test_attachments.mjs` | 附件回归测试 | 正常 | 560 B | — | 验证原始输入与一个或多个可见附件路径的组合格式 |
| `playground/tests/test_markdown.mjs` | Markdown 回归测试 | 正常 | 1,531 B | — | 验证表格、对齐、任务列表、行内格式和 HTML 转义 |
| `playground/tests/test_catalog_data.mjs` | 目录数据回归测试 | 正常 | 1,033 B | — | 验证全部 Skill 的功能分类没有遗漏、重复或无效归属 |

## 数据与调用关系

```text
skills-showcase.html
└─ app.js
   ├─ data.js + /api/skills（实际目录）
   ├─ catalog.js ──> skill_service.py ──> Skill 目录 / skill-insights.yaml
   ├─ ratings.js ──> rating_service.py ──> skill-metadata.yaml
   ├─ git-panel.js ──> git_service.py ──> Git / GCM / origin
   └─ chat.js
      ├─ conversation-state.js
      ├─ attachments.js + attachment-prompt.js ──> .runs/uploads/
      ├─ api.js ──> server.py
      │              ├─ run_registry.py
      │              └─ Codex CLI
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
| `/api/runs/<run-id>/cancel` | POST | 停止指定运行及其 Codex CLI 子进程树 |
| `/api/runs/<run-id>/files/<path>` | GET | 在页面中预览或下载本次运行产物 |
| `/api/uploads` | POST | 流式保存对话附件到本机 `.runs/uploads` 并返回绝对路径 |
| `/api/ratings` | GET | 读取评分等级、Skill 评分和备注 |
| `/api/ratings/settings` | POST | 更新 A/B/C 的名称、说明和颜色 |
| `/api/ratings/skill` | POST | 更新或清除单个 Skill 评分 |
| `/api/skills` | GET | 扫描并返回本地实际 Skill、分类和已保存 AI 结论 |
| `/api/skills/analyze` | POST | 调用本机 Codex 静态分析 Skill 并持久化六类结论 |
| `/api/git/status` | GET | 读取分支、远程同步和本地改动状态 |
| `/api/git/diff?path=...` | GET | 读取安全改动文件的文本 Diff |
| `/api/git/fetch` | POST | 检查并刷新 origin 远程引用 |
| `/api/git/pull` | POST | 在干净工作区执行 `pull --ff-only` |
| `/api/git/commit-push` | POST | 提交明确选择的文件并立即通过 GCM push |
| `/api/git/proxy` | POST | 保存项目级 Git 代理端口，0 表示关闭 |

## Skill 目录维护状态

| 分类 | 目录 | 数量 | Skill |
|---|---|---:|---|
| 自创 | `自创skills/` | 12 | `arxiv-search`、`douyin-video-downloader`、`gpt-image`、`html-ppt-build`、`local-credential-memory`、`manage-myskills`、`mineru-to-markdown`、`ppt-technical-redesign`、`semantic-scholar-search`、`temporary-public-file-links`、`video-narration-tts`、`xiaohongshu-note-downloader` |
| 已测 | `已测skills/` | 9 | `codex-ppt-skill`、`dashiai-ppt`、`imagegen`、`openai-docs`、`professor-synapse`、`skill-creator`、`skill-installer`、`thesis-aigc-rewrite`、`thesis-format-normalize` |
| 待测 | `待测skills/` | 21 | `canvas-design`、`create-plan`、`develop-web-game`、`docx`、`films-search`、`frontend-design`、`frontend-slides`、`grill-me`、`imap-smtp-email`、`local-tools`、`music-search`、`pdf`、`playwright`、`pptx`、`remotion`、`scheduled-task`、`seedance`、`seedream`、`technology-news-search`、`web-search`、`xlsx` |

## 同步规则

- 修改前端模块、Runner、配置或 Skill 后，执行 `python playground/generate_project_status.py`。
- `start-playground.ps1` 启动服务时会再次自动生成本文档，确保模块存在状态、文件大小、模型和 Skill 数量同步。
- Skill 的增删由页面实际扫描同步；已有 Skill 的展示别名或默认分类变化时维护 `data.js`，AI 结论与导入分类写入 `skill-insights.yaml`。README 不维护 Skill 数量和名单。
- 修改 Playground 后通常需要重启并检查 `/api/config`、`/api/skills`、页面模块加载和对话发送；但 Playground 内运行的管理智能体不得重启承载自己的服务，应动态注册 Skill 并把必要的后端重启延后到任务返回之后。
