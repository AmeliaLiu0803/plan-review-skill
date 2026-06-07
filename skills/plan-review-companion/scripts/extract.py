#!/usr/bin/env python3
"""Extract existing review and feedback memories into lesson-memo files."""

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
DEFAULT_MEMORY_DIR = Path("~/.claude/projects").expanduser()
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


def slugify(value: str, fallback: str = "lesson") -> str:
    ascii_parts = re.findall(r"[A-Za-z0-9]+", value.lower())
    if ascii_parts:
        slug = "-".join(ascii_parts[:8])
    else:
        digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
        slug = f"{fallback}-{digest}"
    return slug[:80].strip("-") or fallback


def stable_id(source: str, text: str, index: int) -> str:
    digest = hashlib.sha1(f"{source}\n{text}".encode("utf-8")).hexdigest()[:10]
    return f"{slugify(source, 'source')}-{index:03d}-{digest}"


def strip_markdown(value: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    return " ".join(value.strip().split())


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


def action_from_text(text: str) -> str:
    clean = strip_markdown(text)
    if "如何避免：" in clean:
        return clean.split("如何避免：", 1)[1].strip()
    if "正确做法" in clean:
        return clean[clean.find("正确做法") :].strip()
    if "下期改进" in clean:
        return clean
    return "复用该教训前，先对照当前任务检查触发条件、依赖、权限和验证方式。"


def extract_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^(?P<level>#+)\s*{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    level = len(match.group("level"))
    start = match.end()
    next_heading = re.compile(rf"^#{{1,{level}}}\s+", re.MULTILINE)
    next_match = next_heading.search(text, start)
    end = next_match.start() if next_match else len(text)
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
        elif current and not line.strip():
            continue
    if current:
        items.append("\n".join(current).strip())
    return [item for item in items if item]


def parse_review_file(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"warning: failed to read review {path}: {exc}", file=sys.stderr)
        return []

    lessons: list[dict[str, Any]] = []
    index = 1
    for heading in ["犯错教训", "下期改进"]:
        section = extract_section(text, heading)
        for item in split_markdown_items(section):
            domain = infer_domain(item)
            lesson_id = stable_id(path.stem, item, index)
            lessons.append(
                {
                    "id": lesson_id,
                    "title": title_from_text(item),
                    "source": path.stem,
                    "source_type": "plan_review",
                    "created_at": date.today().isoformat(),
                    "domain": domain,
                    "tags": infer_tags(item, domain),
                    "trigger": f"when current task resembles review section '{heading}' from {path.name}",
                    "lesson": lesson_from_text(item),
                    "action": action_from_text(item),
                    "evidence": [strip_markdown(item), str(path)],
                    "references": [str(path)],
                    "confidence": 0.7,
                    "usage_count": 0,
                    "last_used": None,
                }
            )
            index += 1
    return lessons


def frontmatter_and_body(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    front = parts[1].strip()
    body = parts[2].strip()
    if yaml is not None:
        try:
            loaded = yaml.safe_load(front) or {}
            if isinstance(loaded, dict):
                return loaded, body
        except Exception:
            pass
    metadata: dict[str, Any] = {}
    current_parent: str | None = None
    for raw in front.splitlines():
        if not raw.strip():
            continue
        if not raw.startswith(" ") and ":" in raw:
            key, value = raw.split(":", 1)
            value = value.strip()
            if value:
                metadata[key.strip()] = value
                current_parent = None
            else:
                metadata[key.strip()] = {}
                current_parent = key.strip()
        elif current_parent and ":" in raw:
            key, value = raw.strip().split(":", 1)
            metadata.setdefault(current_parent, {})[key.strip()] = value.strip()
    return metadata, body


def is_feedback_memory(frontmatter: dict[str, Any]) -> bool:
    if frontmatter.get("type") == "feedback":
        return True
    metadata = frontmatter.get("metadata")
    return isinstance(metadata, dict) and metadata.get("type") == "feedback"


def parse_memory_file(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"warning: failed to read memory {path}: {exc}", file=sys.stderr)
        return []
    frontmatter, body = frontmatter_and_body(text)
    if not is_feedback_memory(frontmatter):
        return []
    body = body.strip()
    if not body:
        return []
    name = str(frontmatter.get("name") or path.stem)
    description = str(frontmatter.get("description") or title_from_text(body))
    domain = infer_domain(f"{description}\n{body}")
    lesson_id = stable_id(name, body, 1)
    return [
        {
            "id": lesson_id,
            "title": description[:80],
            "source": name,
            "source_type": "memory",
            "created_at": date.today().isoformat(),
            "domain": domain,
            "tags": infer_tags(f"{description}\n{body}", domain),
            "trigger": f"when current task matches feedback memory '{name}'",
            "lesson": lesson_from_text(body),
            "action": action_from_text(body),
            "evidence": [strip_markdown(body)[:500], str(path)],
            "references": [str(path)],
            "confidence": 0.7,
            "usage_count": 0,
            "last_used": None,
        }
    ]


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
            "confidence": lesson.get("confidence", 0.7),
            "source": lesson.get("source"),
            "source_type": lesson.get("source_type"),
        }
    ordered = sorted(by_id.values(), key=lambda entry: str(entry.get("id", "")))
    write_json(registry_file, {"lessons": ordered})


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract lesson-memo entries from reviews and feedback memories.")
    parser.add_argument("--review-dir", default=str(DEFAULT_REVIEW_DIR), help="Directory containing review Markdown files.")
    parser.add_argument("--memory-dir", default=str(DEFAULT_MEMORY_DIR), help="Directory or tree containing memory Markdown files.")
    parser.add_argument("--lesson-memo-dir", default=str(DEFAULT_MEMO_DIR), help="Lesson memo root directory.")
    args = parser.parse_args()

    review_dir = expand(args.review_dir)
    memory_dir = expand(args.memory_dir)
    memo_dir = expand(args.lesson_memo_dir)
    config = load_json(memo_dir / "config.json", {})
    lessons_dir = expand(config.get("lessons_dir", str(memo_dir / "lessons")))
    registry_file = expand(config.get("registry_file", str(memo_dir / "registry.json")))
    lessons_dir.mkdir(parents=True, exist_ok=True)

    lessons: list[dict[str, Any]] = []
    if review_dir.exists():
        for path in sorted(review_dir.glob("*.md")):
            lessons.extend(parse_review_file(path))
    else:
        print(f"warning: review dir not found: {review_dir}", file=sys.stderr)

    if memory_dir.exists():
        for path in sorted(memory_dir.rglob("*.md")):
            lessons.extend(parse_memory_file(path))
    else:
        print(f"warning: memory dir not found: {memory_dir}", file=sys.stderr)

    unique: dict[str, dict[str, Any]] = {}
    for lesson in lessons:
        unique[lesson["id"]] = lesson
    lessons = list(unique.values())

    for lesson in lessons:
        (lessons_dir / f"{lesson['id']}.md").write_text(dump_lesson(lesson), encoding="utf-8")
    update_registry(registry_file, lessons_dir, lessons)

    domain_counts = Counter(str(lesson.get("domain")) for lesson in lessons)
    print(f"extracted {len(lessons)} lessons")
    print("domains: " + json.dumps(domain_counts, ensure_ascii=False, sort_keys=True))
    print("confidence: " + json.dumps(Counter(str(lesson.get("confidence")) for lesson in lessons), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
