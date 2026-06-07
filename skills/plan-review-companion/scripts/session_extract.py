#!/usr/bin/env python3
"""Lightweight Stop-hook extractor for newly added review lessons."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    yaml = None


DEFAULT_REVIEW_DIR = Path("~/.claude/reviews").expanduser()
DEFAULT_MEMO_DIR = Path("~/.claude/lesson-memo").expanduser()

DOMAIN_KEYWORDS = [
    ("research-reproduction", ["手写", "clone", "官方", "实现", "复现", "论文", "repo", "github"]),
    ("dependency-analysis", ["依赖", "接口", "源码", "分析", "调用", "temporal_credits"]),
    ("cross-platform", ["wsl", "兼容", "平台", "路径", "linux", "windows", "bsd"]),
    ("tool-access", ["codex", "ssh", "权限", "工具", "集群", "auto mode"]),
    ("project-management", ["phase", "gate", "审查", "流程", "计划", "checklist", "fallback"]),
    ("claude-workflow", ["settings", "claude.md", "规则", "claude", "hook", "workflow"]),
]


def expand(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"warning: failed to read {path}: {exc}", file=sys.stderr)
    return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def strip_markdown(value: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    return " ".join(value.strip().split())


def stable_id(source: str, text: str) -> str:
    digest = hashlib.sha1(f"{source}\n{text}".encode("utf-8")).hexdigest()[:12]
    parts = re.findall(r"[A-Za-z0-9]+", source.lower())
    prefix = "-".join(parts[:6]) if parts else "session-lesson"
    return f"{prefix}-{digest}"


def infer_domain(text: str) -> str:
    lowered = text.lower()
    scores = Counter()
    for domain, keywords in DOMAIN_KEYWORDS:
        for keyword in keywords:
            if keyword.lower() in lowered:
                scores[domain] += 1
    return scores.most_common(1)[0][0] if scores else "project-management"


def infer_tags(text: str, domain: str) -> list[str]:
    lowered = text.lower()
    tags = [domain]
    for _, keywords in DOMAIN_KEYWORDS:
        for keyword in keywords:
            if keyword.lower() in lowered:
                tags.append(keyword.lower().replace(" ", "-"))
    return list(dict.fromkeys(tags))[:8]


def title_from_text(text: str) -> str:
    clean = strip_markdown(text)
    if "：" in clean:
        clean = clean.split("：", 1)[0]
    elif ":" in clean:
        clean = clean.split(":", 1)[0]
    return clean[:80] or "未命名教训"


def lesson_from_text(text: str) -> str:
    clean = strip_markdown(text)
    for marker in ["教训：", "教训:", "必须", "不要"]:
        if marker in clean:
            return clean[clean.find(marker) :].strip()
    return clean


def extract_section(text: str, heading: str) -> str:
    match = re.search(rf"^(?P<level>#+)\s*{re.escape(heading)}\s*$", text, flags=re.MULTILINE)
    if not match:
        return ""
    level = len(match.group("level"))
    start = match.end()
    next_match = re.search(rf"^#{{1,{level}}}\s+", text[start:], flags=re.MULTILINE)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end].strip()


def split_markdown_items(section: str) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    item_start = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)、]\s+)(.*)$")
    for line in section.splitlines():
        match = item_start.match(line)
        if match:
            if current:
                items.append("\n".join(current).strip())
            current = [match.group(1).strip()]
        elif current and line.strip():
            current.append(line.strip())
    if current:
        items.append("\n".join(current).strip())
    return [item for item in items if item]


def review_items(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"warning: failed to read review {path}: {exc}", file=sys.stderr)
        return []
    items: list[str] = []
    for heading in ["犯错教训", "下期改进"]:
        items.extend(split_markdown_items(extract_section(text, heading)))
    return items


def dump_lesson(lesson: dict[str, Any]) -> str:
    if yaml is not None:
        return "---\n" + yaml.safe_dump(lesson, allow_unicode=True, sort_keys=False) + "---\n"
    lines = ["---"]
    for key, value in lesson.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {json.dumps(str(item), ensure_ascii=False)}")
        elif value is None:
            lines.append(f"{key}: null")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        else:
            escaped = str(value).replace("\n", "\n  ")
            if "\n" in str(value):
                lines.append(f"{key}: |")
                lines.append(f"  {escaped}")
            else:
                lines.append(f"{key}: {json.dumps(str(value), ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def update_registry(registry_file: Path, lessons_dir: Path, lessons: list[dict[str, Any]]) -> None:
    registry = load_json(registry_file, {"lessons": []})
    existing = registry.get("lessons", []) if isinstance(registry, dict) else []
    by_id = {entry.get("id"): entry for entry in existing if isinstance(entry, dict)}
    for lesson in lessons:
        by_id[lesson["id"]] = {
            "id": lesson["id"],
            "file": str(lessons_dir / f"{lesson['id']}.md"),
            "title": lesson.get("title"),
            "domain": lesson.get("domain"),
            "tags": lesson.get("tags", []),
            "confidence": lesson.get("confidence", 0.5),
            "source": lesson.get("source"),
            "source_type": lesson.get("source_type"),
        }
    write_json(registry_file, {"lessons": sorted(by_id.values(), key=lambda entry: str(entry.get("id", "")))})


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract newly added review lessons since last snapshot.")
    parser.add_argument("--review-dir", default=str(DEFAULT_REVIEW_DIR), help="Directory containing review Markdown files.")
    parser.add_argument("--memo-dir", default=str(DEFAULT_MEMO_DIR), help="Lesson memo root directory.")
    args = parser.parse_args()

    review_dir = expand(args.review_dir)
    memo_dir = expand(args.memo_dir)
    config = load_json(memo_dir / "config.json", {})
    lessons_dir = expand(config.get("lessons_dir", str(memo_dir / "lessons")))
    registry_file = expand(config.get("registry_file", str(memo_dir / "registry.json")))
    state_file = memo_dir / ".last_session_state.json"
    lessons_dir.mkdir(parents=True, exist_ok=True)

    had_snapshot = state_file.exists()
    previous = load_json(state_file, {"seen_hashes": []})
    seen = set(previous.get("seen_hashes", [])) if isinstance(previous, dict) else set()
    current_seen: set[str] = set()
    new_lessons: list[dict[str, Any]] = []

    if not review_dir.exists():
        print(f"warning: review dir not found: {review_dir}", file=sys.stderr)
        write_json(state_file, {"seen_hashes": sorted(current_seen), "updated_at": date.today().isoformat()})
        return 0

    for path in sorted(review_dir.glob("*.md")):
        for item in review_items(path):
            item_hash = hashlib.sha1(f"{path}\n{item}".encode("utf-8")).hexdigest()
            current_seen.add(item_hash)
            if item_hash in seen or not had_snapshot:
                continue
            domain = infer_domain(item)
            lesson_id = stable_id(path.stem, item)
            new_lessons.append(
                {
                    "id": lesson_id,
                    "title": title_from_text(item),
                    "source": path.stem,
                    "source_type": "hook_observed",
                    "created_at": date.today().isoformat(),
                    "domain": domain,
                    "tags": infer_tags(item, domain),
                    "trigger": f"new review lesson observed in {path.name}",
                    "lesson": lesson_from_text(item),
                    "action": "下次处理相似计划或执行任务时，先显式检查该教训是否触发。",
                    "evidence": [strip_markdown(item), str(path)],
                    "references": [str(path)],
                    "confidence": 0.5,
                    "usage_count": 0,
                    "last_used": None,
                }
            )

    for lesson in new_lessons:
        (lessons_dir / f"{lesson['id']}.md").write_text(dump_lesson(lesson), encoding="utf-8")
    if new_lessons:
        update_registry(registry_file, lessons_dir, new_lessons)
    write_json(state_file, {"seen_hashes": sorted(current_seen), "updated_at": date.today().isoformat()})
    print(f"session_extract: added {len(new_lessons)} new lessons")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
