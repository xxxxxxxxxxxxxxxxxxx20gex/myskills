# 我的 Codex Skills

个人维护的 Codex skills 仓库。打开 [skills-showcase.html](skills-showcase.html) 可按维护状态浏览全部 skill，并点击卡片查看功能、文档章节和目录位置。启动本地 Skill Playground 后，还可以把所选 skill 和任务直接交给本机 Codex CLI，并在页面中查看执行过程、回答和生成产物。模块、接口、模型和 Skill 分类的实时维护状态见自动生成的 [PROJECT_STATUS.md](PROJECT_STATUS.md)。

## Skill Playground

页面右侧提供常驻多轮对话栏，可拖动中间分隔条调整宽度，并安全渲染助手回复中的 Markdown；左侧卡片在宽屏下一排最多 4 个，并随目录区域的实际宽度自动降为 3、2、1 列。对话栏可直接选择任意 skill，并切换 `gpt-5.6-terra`、`gpt-5.6-sol` 和 `deepseek-v4-flash`；模型下拉框同时显示名称和实际传给 Codex CLI 的模型 ID。Playground 自身不再模拟模型工具调用，而是通过 `codex exec --json` 把任务交给本机 Codex CLI；Codex 原生负责读取 `SKILL.md`、使用 Shell、网络、MCP、本机 skills 与其他可用工具。前端只负责发送任务、接收结构化执行事件、显示回答和 `.runs/` 中的生成产物。

为了能够测试 Skill 自身的原始行为，Runner 不添加输出格式、文件保存、自检、真实性检查或回答风格提示。下拉框选择只会被编码为 Codex 的显式 Skill 标记，例如 `$arxiv-search`；该标记之后的用户输入保持原样。仓库中的 Skills 在启动时通过被 Git 忽略的 `.agents/skills/` 符号链接注册给 Codex，链接直接指向原始 Skill 目录，不复制或改写 `SKILL.md`。

1. 确认本机已安装并登录 Codex Desktop 或 Codex CLI。Runner 会优先自动发现 Codex Desktop 用户目录中的 CLI，也可在 `config.yaml` 中手动填写路径。
2. 按需修改 `config.yaml` 中的模型、CLI sandbox、审批策略和服务端口。默认是面向本机个人环境的 `danger-full-access` 与 `never`，页面不会弹出终端审批。
3. 仅当某个 skill 需要额外 API 凭据时，才将 `.env.example` 复制为 `.env` 并填写相应环境变量；Playground 自身使用 Codex 的本机配置和认证，不依赖该文件。
4. 运行 `start-playground.ps1`。
5. 浏览器打开 `http://127.0.0.1:8765`，在右侧“Skill 对话”栏选择 skill 后直接发送任务。

首次消息会创建一个 Codex session，后续消息用该 session 继续，因此多轮上下文由 Codex 原生维护。切换 skill 或点击“新对话”会创建新 session。执行日志来自 Codex JSONL 事件；图片、音频、视频、HTML 和其他文件只要保存到本次 `.runs/<run-id>/` 目录，就会显示在对应消息下。

页面还提供两组可持久化的维护功能：每个 Skill 可评为 A、B、C，填写备注并按等级筛选；三个等级的显示名称、说明和颜色也可在“等级设置”中自定义。数据统一保存到 `skill-metadata.yaml`，可和代码一起通过 Git 同步。

“项目管理”面板可查看当前分支、origin、ahead/behind、本地文件状态和逐文件 Diff，也能检查远程更新、执行 `git pull --ff-only`，以及选择文件后一次完成 commit 和 push。文件默认不勾选，提交前会再次确认；敏感文件、运行产物和外部已暂存文件不能从网页提交。PAT 不需要也不允许填入网页：标准 Git 会直接复用本机 Git Credential Manager（GCM）中已有的 GitHub 凭据。若 GCM 尚未登录，应先在终端完成一次 GitHub 认证。

如果 GitHub 直连不可用，可在“项目管理”中填写本机 HTTP/SOCKS 混合代理端口。默认配置为 `127.0.0.1:7897`，端口写入 `config.yaml`；填写 `0` 可关闭。代理仅以临时 Git 参数作用于本 Playground 的 fetch、pull 和 push，不修改系统代理，也不写入全局或仓库级 Git 配置。

## 前端模块

前端使用浏览器原生 ES Modules，不需要 React、Vite 或构建命令：

| 模块 | 职责 |
|---|---|
| `skills-showcase.html` | 页面语义结构和各分类的自创 Skill 卡片 |
| `playground/static/styles.css` | 全部页面与响应式样式 |
| `playground/static/js/data.js` | 自创、已测和待测 Skill 展示数据 |
| `playground/static/js/catalog.js` | 分类标签、动态卡片和详情弹窗 |
| `playground/static/js/api.js` | 本地 Runner HTTP API |
| `playground/static/js/artifacts.js` | 图片、音频、视频、HTML 和文件预览 |
| `playground/static/js/markdown.js` | 安全的助手 Markdown 回复渲染 |
| `playground/static/js/resize.js` | 对话栏拖动缩放、键盘操作和宽度记忆 |
| `playground/static/js/chat.js` | 对话、轮询、日志和 Codex session |
| `playground/static/js/ratings.js` | Skill 评分、筛选和等级设置 |
| `playground/static/js/git-panel.js` | Git 状态、Diff、拉取与 commit/push 界面 |
| `playground/static/js/app.js` | 模块启动和依赖编排 |
| `playground/rating_service.py` | 评分校验和 `skill-metadata.yaml` 持久化 |
| `playground/git_service.py` | 受限 Git 操作和 GCM push 桥接 |

运行 `python playground/generate_project_status.py` 可随时重新生成 `PROJECT_STATUS.md`；启动 Playground 时也会自动同步一次。

## 目录状态

| 目录 | 数量 | 含义 |
|---|---:|---|
| `自创skills/` | 11 | 自主创建和定制，按自己的工作环境维护 |
| `已测skills/` | 7 | 已经过实际使用或验证，可优先复用 |
| `待测skills/` | 20 | 已收集，尚需验证依赖、兼容性或实际效果 |

## 自创 Skills

- `arxiv-search`：检索 arXiv 论文、预印本、精确 ID 和 PDF 链接。
- `douyin-video-downloader`：归档公开抖音视频、封面、图文和元数据。
- `gpt-image`：通过 OpenAI-compatible Images API 生成、编辑和局部重绘图片。
- `html-ppt-build`：将报告或 Markdown 制作成中文 HTML 技术 PPT，并导出 PPTX。
- `local-credential-memory`：本地管理账号、密码、API key、SSH 和数据库凭据；用户授权查看本机配置时，可发现并导入凭据供后续直接复用。
- `mineru-to-markdown`：将 PDF、Office、图片或网页转换为 Markdown。
- `ppt-technical-redesign`：重构普通 PPT 的技术叙事、内容结构和视觉表达。
- `semantic-scholar-search`：检索 Semantic Scholar 论文、作者、引用和参考文献。
- `temporary-public-file-links`：为本地文件或目录创建临时公开链接。
- `video-narration-tts`：根据视频画面改写旁白、生成中文 TTS 并合成 MP4。
- `xiaohongshu-note-downloader`：归档公开小红书图文、视频和来源信息。

## 已测 Skills

`codex-ppt-skill`、`dashiai-ppt`、`imagegen`、`openai-docs`、`professor-synapse`、`skill-creator`、`skill-installer`

## 待测 Skills

`canvas-design`、`create-plan`、`develop-web-game`、`docx`、`films-search`、`frontend-design`、`frontend-slides`、`imap-smtp-email`、`local-tools`、`music-search`、`pdf`、`playwright`、`pptx`、`remotion`、`scheduled-task`、`seedance`、`seedream`、`technology-news-search`、`web-search`、`xlsx`

## 安全约定

- `.env`、证书、私钥和 `secrets.*` 已被 Git 忽略；只提交脱敏的示例配置。`.env` 只向本机 Codex CLI 和子工具注入，不传给浏览器。
- `.runs/`、运行日志和临时上传目录不会提交到 Git。
- 不将真实凭据写入 skill 文档、脚本、README、展示页或 Git 历史。
- Playground 仅绑定 `127.0.0.1`，并只接受本页面来源的 JSON 任务请求。默认 CLI sandbox 为 `danger-full-access`，不要把该服务暴露到局域网或公网。
- Runner 只负责 Skill 选择、用户输入转发和 CLI 事件接收。需要改变输出格式或执行约束时，应修改对应 Skill，而不是在 Runner 中添加隐藏提示词。
- 项目管理页不接收 PAT；push 认证只交给本机 Git Credential Manager。commit 只暂存用户勾选的安全文件，不执行 `git add -A`。
