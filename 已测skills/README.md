# 已测 Skills

本目录用于保存已经测试或准备测试的 Codex Skill 副本。复制到这里不会自动启用 Skill；需要使用时，应将对应目录复制或链接到 `%USERPROFILE%\.codex\skills\`，然后重新开始一个 Codex 任务。

## PPT Skill 选择

### codex-ppt-skill

- 目录：[`codex-ppt-skill`](./codex-ppt-skill)
- 当前状态：已从 `C:\Users\23262\.codex\skills\codex-ppt-skill` 原样复制。
- 适合场景：希望获得较强视觉冲击力、统一设计语言和完整故事线的演示文稿；适合研究报告、方案汇报、论文解读和视觉型提案。
- 输出特点：每页由图像生成后作为整页画面装入 PPTX，视觉统一，但页面中的文字、图表和形状通常不能在 PowerPoint 中逐项编辑。
- 使用条件：需要可用的 Python；图像生成阶段需要 Skill 支持的生图后端及相应 API 配置；高质量整页生成可能耗时较长。
- 启用方式：将本目录复制到 `%USERPROFILE%\.codex\skills\codex-ppt-skill`，重新开始 Codex 任务，然后直接提出“使用 codex-ppt-skill 将这份报告制作成 PPT”。
- 推荐流程：确认大纲 → 确认视觉风格 → 确认生图后端 → 生成并确认样张 → 生成全套页面 → 视觉检查 → 组装 PPTX。
- 适用前提：接受以整页图片为主的 PPT；若要求每个文本框、图表和形状都可独立编辑，不应选择此 Skill。

### dashiAI-ppt-skill

- 仓库地址：[chuspeeism/dashiAI-ppt-skill](https://github.com/chuspeeism/dashiAI-ppt-skill)
- 目录：[`dashiAI-ppt-skill`](./dashiAI-ppt-skill)
- 当前状态：已通过本机 `127.0.0.1:7897` 代理完成浅克隆；实际 Skill 位于 `dashiAI-ppt-skill/skills/dashiai-ppt`。
- 适合场景：希望先生成浏览器可编辑的 HTML 演示文稿，并在浏览器中继续调整文字、布局、配色和组件，然后再导出 HTML、PDF 或 PPTX。
- 输出特点：以网页页面为主要编辑载体，后期微调比整页图片型 PPT 方便；实际 PPTX 的可编辑程度取决于该 Skill 的导出实现。
- 使用条件：Node.js 20+、npm，以及导出 PPTX/PDF 所需的 Chrome、Chromium 或 Edge；生成和编辑主要在本机完成，首次运行会在 Skill 内置 `project/` 中安装依赖。
- 启用方式：将 `dashiAI-ppt-skill/skills/dashiai-ppt` 复制到 `%USERPROFILE%\.codex\skills\dashiai-ppt`，重新开始 Codex 任务，然后提出“使用 dashiai-ppt 制作浏览器可编辑的 PPT”。
- 生成方式：按 Skill 要求先准备 `goal.json`，运行 `npm --prefix <skill-root>/project run props:safe -- --goal <goal.json> --write` 和 `validate:goal-spec`，再运行 `scripts/render_goal_deck.sh`。
- 浏览器微调流程：先生成 HTML → 用 Skill 的本地预览服务打开 `http://127.0.0.1:<port>/` → 在浏览器中改文字、换图、调布局、模块数量和配色 → 导出 HTML/PDF/PPTX。导出可编辑 PPTX 时优先使用 `/api/export-editable-pptx` 或 Skill 提供的 `npm run export:pptx` 回退命令。
- 主题选择：内置 12 套主题；研究白皮书可优先尝试 `theme07`，数据分析可尝试 `theme05`，科技发布可尝试 `theme02`。
- 适用前提：更重视浏览器内的后期编辑和迭代效率，并可以接受 HTML/网页工作流。

## 其他已测 Skills

- [`imagegen`](./imagegen)：生成或编辑位图素材；内置工具可直接使用，CLI 回退通常需要 `OPENAI_API_KEY`。
- [`openai-docs`](./openai-docs)：检索 OpenAI 官方文档，适合 API、模型选型和迁移咨询。
- [`professor-synapse`](./professor-synapse)：组织领域专家代理，适合需要多专业视角的复杂任务。
- [`skill-creator`](./skill-creator)：创建或更新 Codex Skill。
- [`skill-installer`](./skill-installer)：从官方列表或 GitHub 仓库安装 Skill。
