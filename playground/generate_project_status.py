from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


MODULES = [
    ("skills-showcase.html", "页面外壳", "保留语义化 HTML、卡片容器、详情弹窗和右侧对话区域"),
    ("playground/static/styles.css", "样式系统", "负责响应式布局、卡片、对话、Git 操作反馈、日志和产物预览样式"),
    ("playground/static/js/data.js", "Skill 数据", "维护自创 Skill 详情以及已测/待测 Skill 展示元数据"),
    ("playground/static/js/catalog.js", "目录交互", "渲染仓库 Skill 卡片、分类标签和详情弹窗"),
    ("playground/static/js/api.js", "API 客户端", "封装配置读取、任务创建和运行状态查询"),
    ("playground/static/js/artifacts.js", "产物渲染", "预览图片、音频、视频、HTML 和普通文件"),
    ("playground/static/js/markdown.js", "Markdown 渲染", "安全渲染标题、列表、引用、代码和外部链接，不执行原始 HTML"),
    ("playground/static/js/resize.js", "面板缩放", "拖动或用键盘调整对话栏宽度，并在浏览器本地记忆"),
    ("playground/static/js/chat.js", "对话状态", "管理模型/Skill 选择、Codex session、轮询、日志、Markdown 和消息"),
    ("playground/static/js/ratings.js", "评分交互", "管理 A/B/C 评分、备注、筛选和等级显示设置"),
    ("playground/static/js/git-panel.js", "Git 项目管理", "展示状态与 Diff，提供 Git 操作按钮的执行反馈，并触发 fetch、ff-only pull、选择性 commit/push"),
    ("playground/static/js/app.js", "前端编排", "组合目录、对话与面板缩放模块并选择默认 Skill"),
    ("playground/server.py", "本地 Runner", "注册原始 Skills，以 `$skill-name` 加用户原文桥接 Codex CLI，提供运行状态并执行静态资源白名单"),
    ("playground/rating_service.py", "评分服务", "校验并原子更新可进入 Git 的 skill-metadata.yaml"),
    ("playground/git_service.py", "Git 服务", "执行白名单 Git 参数、保护敏感文件并通过 GCM 推送"),
    ("skill-metadata.yaml", "维护数据", "保存 A/B/C 显示设置、Skill 评分和备注，随 Git 同步"),
    ("playground/generate_project_status.py", "状态文档生成器", "扫描模块、配置与 Skill 目录并更新本文件"),
]

SKILL_GROUPS = [
    ("自创skills", "自创"),
    ("已测skills", "已测"),
    ("待测skills", "待测"),
]


def module_exports(path: Path) -> str:
    if path.suffix != ".js" or not path.exists():
        return "—"
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    names = re.findall(r"export\s+(?:async\s+)?(?:function|const|class)\s+([A-Za-z_$][\w$]*)", text)
    return ", ".join(f"`{name}`" for name in names) or "—"


def skill_names(root: Path, folder: str) -> list[str]:
    base = root / folder
    if not base.exists():
        return []
    return sorted(
        path.parent.name
        for path in base.glob("*/SKILL.md")
        if path.is_file()
    )


def build_document(root: Path, config: dict[str, Any]) -> str:
    module_rows = []
    for relative, responsibility, feature in MODULES:
        path = root / relative
        status = "正常" if path.is_file() else "缺失"
        size = f"{path.stat().st_size:,} B" if path.is_file() else "—"
        module_rows.append(
            f"| `{relative}` | {responsibility} | {status} | {size} | {module_exports(path)} | {feature} |"
        )

    group_data = [(folder, label, skill_names(root, folder)) for folder, label in SKILL_GROUPS]
    total = sum(len(names) for _, _, names in group_data)
    models = config.get("models", [])
    model_names = "、".join(f"`{item.get('id', '')}`" for item in models) or "未配置"
    server = config.get("server", {})
    codex = config.get("codex_cli", {})

    lines = [
        "# 项目模块状态",
        "",
        "> 本文档由 `python playground/generate_project_status.py` 自动生成。请勿手工维护统计表；服务启动时也会自动同步。",
        "",
        "## 当前概况",
        "",
        f"- Skill 总数：**{total}**",
        f"- 前端架构：原生 HTML + CSS + ES Modules，无构建步骤",
        f"- 执行后端：本机 Codex CLI（sandbox：`{codex.get('sandbox', '未配置')}`，approval：`{codex.get('approval_policy', '未配置')}`）",
        "- 提示词策略：仅添加显式 `$skill-name` 选择标记，用户输入原样转发，无 Runner 行为提示",
        f"- 服务地址：`http://{server.get('host', '127.0.0.1')}:{server.get('port', 8765)}`",
        f"- 可选模型：{model_names}",
        f"- Git 代理：`http://{config.get('git', {}).get('proxy_host', '127.0.0.1')}:{config.get('git', {}).get('proxy_port', 0)}`（端口 `0` 表示关闭）",
        "",
        "## 模块状态",
        "",
        "| 文件 | 模块职责 | 状态 | 大小 | 对外导出 | 当前功能 |",
        "|---|---|---|---:|---|---|",
        *module_rows,
        "",
        "## 数据与调用关系",
        "",
        "```text",
        "skills-showcase.html",
        "└─ app.js",
        "   ├─ data.js",
        "   ├─ catalog.js",
        "   ├─ ratings.js ──> rating_service.py ──> skill-metadata.yaml",
        "   ├─ git-panel.js ──> git_service.py ──> Git / GCM / origin",
        "   └─ chat.js",
        "      ├─ api.js ──> server.py ──> Codex CLI",
        "      ├─ markdown.js",
        "      ├─ artifacts.js <── .runs/<run-id>/",
        "      └─ resize.js",
        "```",
        "",
        "## 后端接口",
        "",
        "| 接口 | 方法 | 用途 |",
        "|---|---|---|",
        "| `/api/config` | GET | 返回模型、默认模型和 Codex CLI 可用状态 |",
        "| `/api/runs` | POST | 创建新的 Codex CLI 执行或续接已有 session |",
        "| `/api/runs/<run-id>` | GET | 查询状态、日志、答复、session 和产物 |",
        "| `/api/runs/<run-id>/files/<path>` | GET | 在页面中预览或下载本次运行产物 |",
        "| `/api/ratings` | GET | 读取评分等级、Skill 评分和备注 |",
        "| `/api/ratings/settings` | POST | 更新 A/B/C 的名称、说明和颜色 |",
        "| `/api/ratings/skill` | POST | 更新或清除单个 Skill 评分 |",
        "| `/api/git/status` | GET | 读取分支、远程同步和本地改动状态 |",
        "| `/api/git/diff?path=...` | GET | 读取安全改动文件的文本 Diff |",
        "| `/api/git/fetch` | POST | 检查并刷新 origin 远程引用 |",
        "| `/api/git/pull` | POST | 在干净工作区执行 `pull --ff-only` |",
        "| `/api/git/commit-push` | POST | 提交明确选择的文件并立即通过 GCM push |",
        "| `/api/git/proxy` | POST | 保存项目级 Git 代理端口，0 表示关闭 |",
        "",
        "## Skill 分类状态",
        "",
        "| 分类 | 目录 | 数量 | Skill |",
        "|---|---|---:|---|",
    ]
    for folder, label, names in group_data:
        rendered = "、".join(f"`{name}`" for name in names) or "—"
        lines.append(f"| {label} | `{folder}/` | {len(names)} | {rendered} |")

    lines.extend([
        "",
        "## 同步规则",
        "",
        "- 修改前端模块、Runner、配置或 Skill 后，执行 `python playground/generate_project_status.py`。",
        "- `start-playground.ps1` 启动服务时会再次自动生成本文档，确保模块存在状态、文件大小、模型和 Skill 数量同步。",
        "- Skill 名称、分类、功能说明变化时，仍需同步维护 `readme.md` 与 `playground/static/js/data.js` 中的展示信息。",
        "- 修改 Playground 后必须重启，并检查 `/api/config`、页面模块加载、分类切换、详情弹窗和对话发送按钮。",
        "",
    ])
    return "\n".join(lines)


def update_project_status(root: Path, config: dict[str, Any]) -> bool:
    target = root / "PROJECT_STATUS.md"
    content = build_document(root, config)
    previous = target.read_text(encoding="utf-8-sig") if target.exists() else ""
    if previous == content:
        return False
    target.write_text(content, encoding="utf-8")
    return True


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
    changed = update_project_status(root, config)
    print(f"PROJECT_STATUS.md {'updated' if changed else 'already current'}")


if __name__ == "__main__":
    main()
