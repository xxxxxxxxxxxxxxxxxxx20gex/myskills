# Repository Instructions

本文件适用于整个 `myskills` 仓库。维护、移动、安装或删除任何 skill 时，都必须遵守以下约定。

## 项目用途

这是个人维护的 Codex skills 仓库。Skill 按来源和验证状态分为自创、已测、待测三类，并通过 README 和静态 HTML 页面提供目录导航。

## 项目结构

```text
myskills/
├── AGENTS.md                  # 仓库级维护约定
├── readme.md                  # 项目说明、分类数量与 skill 名单
├── skills-showcase.html       # 可交互的静态 skill 导航页面
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

## Skill 变更时必须同步文档

新增、复制、修改、重命名、移动或删除任何 skill 时，必须在同一个改动中同步检查并更新：

1. `readme.md`

   - 更新三个分类的数量。
   - 更新对应分类中的 skill 名单。
   - 新增或修改自创 skill 时，同步更新其功能简介。
   - 删除或重命名 skill 时，移除所有旧名称、旧路径和过时说明。
2. `skills-showcase.html`

   - 更新页面顶部的总数和 `自创 / 已测 / 待测` 数量。
   - 更新状态标签页上的数量。
   - 自创 skill 变化时，更新对应静态卡片和 `skillDetails` 详情数据。
   - 已测或待测 skill 变化时，更新 `repositorySkills` 中的名称、目录、状态、简介和 `SKILL.md` 章节。
   - Skill 在 `已测skills/` 与 `待测skills/` 之间移动时，只保留新状态的数据条目。
   - 保证每个实际 skill 都能在页面中找到，并可点击打开详细信息。

以下改动也视为需要同步：

- 修改 `SKILL.md` frontmatter 中的 `name` 或 `description`。
- 修改 skill 的核心能力、依赖、输出格式或使用边界。
- 调整目录名称或维护状态。
- 替换一个旧 skill 为职责不同的新 skill。

## 验证要求

完成 skill 或目录页面改动后，至少执行以下检查：

1. 统计 `自创skills/`、`已测skills/`、`待测skills/` 中包含 `SKILL.md` 的目录数量。
2. 确认该数量与 `readme.md`、`skills-showcase.html` 顶部统计和标签页数字一致。
3. 确认展示页的卡片集合与实际目录一致，没有遗漏、重复或已删除的条目。
4. 对 `skills-showcase.html` 中的 JavaScript 执行语法检查，并用浏览器打开页面检查标签页、卡片和详情弹窗。
5. 对新增或修改的 skill 运行 skill 结构验证；存在脚本时，按风险执行语法检查或代表性测试。
6. 提交前运行 `git diff --check` 并检查暂存文件列表。

## 安全规则

- 不读取、输出、提交或复制真实 `.env`、密码、API key、访问令牌、私钥、证书或 `secrets.*`。
- 只提交脱敏的 `.env_example` 或 `.env.example`。
- 添加新类型的本地凭据文件时，同步更新 `.gitignore`。
- 不把运行产物、缓存、下载文件或生成媒体提交到 skill 源码目录，除非它们是明确需要版本控制的示例或资产。
- 在推送前确认 Git 暂存区不含任何敏感文件或意外生成物。

## Git 与维护边界

- 保留用户已有的未提交改动，不覆盖或回滚无关内容。
- 只提交当前任务涉及的 skill、README、展示页和必要维护文件。
- 不使用破坏性 Git 操作清理工作区。
- 只有用户明确要求时才推送远程仓库。
