from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from docx import Document


DATA_RE = re.compile(r"var\s+data\s*=\s*(\{.*\})\s*;\s*$", re.S)


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text)


def locate_data_file(report_path: Path) -> Path:
    report_path = report_path.resolve()
    if report_path.is_file() and report_path.suffix.lower() == ".js":
        return report_path
    root = report_path if report_path.is_dir() else report_path.parent
    candidates = [
        root / "htmls" / "js" / "simplesentenceresult_ai.js",
        root / "js" / "simplesentenceresult_ai.js",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    matches = list(root.rglob("simplesentenceresult_ai.js"))
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError("Could not uniquely locate simplesentenceresult_ai.js")


def parse_report(path: Path) -> dict:
    source = path.read_text(encoding="utf-8-sig")
    match = DATA_RE.search(source)
    if not match:
        raise RuntimeError(f"Could not parse PaperPass AIGC data in {path}")
    return json.loads(match.group(1))


def risk(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 60:
        return "middle"
    return "low"


def map_context(context: str, paragraphs: list[dict]) -> dict:
    target = normalize(context)
    contained = [
        p for p in paragraphs
        if len(normalize(p["text"])) >= 20 and normalize(p["text"]) in target
    ]
    if contained:
        return {
            "method": "contained-paragraphs",
            "confidence": 1.0,
            "paragraphs": contained,
        }

    windows = []
    for start in range(len(paragraphs)):
        for width in range(1, 5):
            group = paragraphs[start:start + width]
            if len(group) != width:
                continue
            if any(group[i + 1]["index"] != group[i]["index"] + 1 for i in range(width - 1)):
                continue
            candidate = normalize("".join(p["text"] for p in group))
            score = SequenceMatcher(None, target, candidate).ratio()
            windows.append((score, group))
    windows.sort(key=lambda item: item[0], reverse=True)
    best_score, best_group = windows[0]
    runner_up = windows[1][0] if len(windows) > 1 else 0.0
    return {
        "method": "fuzzy-window",
        "confidence": round(best_score, 4),
        "margin": round(best_score - runner_up, 4),
        "paragraphs": best_group,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract PaperPass AIGC blocks and map them to DOCX paragraphs")
    parser.add_argument("--report", type=Path, required=True, help="Offline report HTML, report directory, or JS data file")
    parser.add_argument("--docx", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    data_path = locate_data_file(args.report)
    report = parse_report(data_path)
    document = Document(args.docx)
    paragraphs = [
        {"index": index, "style": paragraph.style.name, "text": paragraph.text.strip()}
        for index, paragraph in enumerate(document.paragraphs)
        if paragraph.text.strip()
    ]

    blocks = []
    for report_key, item in report.items():
        score = float(item.get("overall", 0.0))
        for context_index, raw_context in enumerate(item.get("sectionContentList", [])):
            context = raw_context.strip()
            if not context:
                continue
            mapping = map_context(context, paragraphs)
            blocks.append({
                "report_key": report_key,
                "score": score,
                "risk": risk(score),
                "context_index": context_index,
                "report_text": context,
                "mapping": mapping,
                "requires_review": mapping["confidence"] < 0.90 or mapping.get("margin", 1.0) < 0.05,
            })

    result = {
        "report_data": str(data_path),
        "docx": str(args.docx.resolve()),
        "block_count": len(report),
        "context_count": len(blocks),
        "risk_counts": {
            level: sum(1 for item in report.values() if risk(float(item.get("overall", 0.0))) == level)
            for level in ("high", "middle", "low")
        },
        "blocks": blocks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    review_count = sum(1 for block in blocks if block["requires_review"])
    print(json.dumps({
        "block_count": result["block_count"],
        "context_count": result["context_count"],
        "risk_counts": result["risk_counts"],
        "requires_review": review_count,
        "output": str(args.output.resolve()),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
