#!/usr/bin/env python3
"""Recall relevant lesson-memo entries for plan review context."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    yaml = None


DEFAULT_MEMO_DIR = Path("~/.claude/lesson-memo").expanduser()

DOMAIN_KEYWORDS = {
    "research-reproduction": ["手写", "clone", "官方", "实现", "复现", "论文", "repo", "github"],
    "dependency-analysis": ["依赖", "接口", "源码", "分析", "调用", "temporal_credits"],
    "cross-platform": ["wsl", "兼容", "平台", "路径", "linux", "windows", "bsd"],
    "tool-access": ["codex", "ssh", "权限", "工具", "集群", "auto mode"],
    "project-management": ["phase", "gate", "审查", "流程", "计划", "checklist", "fallback"],
    "claude-workflow": ["settings", "claude.md", "规则", "claude", "hook", "workflow"],
}


def expand(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"warning: failed to read {path}: {exc}", file=sys.stderr)
    return default


def parse_simple_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] | None = None
    current_block: list[str] | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if current_block is not None:
            if raw_line.startswith("  "):
                current_block.append(raw_line[2:])
                continue
            if current_key:
                data[current_key] = "\n".join(current_block).strip()
            current_block = None
            current_key = None
        if current_list is not None:
            if raw_line.startswith("  - "):
                current_list.append(raw_line[4:].strip().strip('"\''))
                continue
            if current_key:
                data[current_key] = current_list
            current_list = None
            current_key = None
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        if value in {"|", ">"}:
            current_key = key
            current_block = []
        elif value == "":
            current_key = key
            current_list = []
        elif value.startswith("[") and value.endswith("]"):
            data[key] = [part.strip().strip('"\'') for part in value[1:-1].split(",") if part.strip()]
        elif value.lower() in {"null", "none"}:
            data[key] = None
        else:
            data[key] = value.strip().strip('"\'')

    if current_block is not None and current_key:
        data[current_key] = "\n".join(current_block).strip()
    if current_list is not None and current_key:
        data[current_key] = current_list
    return data


def parse_lesson_file(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"warning: failed to read lesson {path}: {exc}", file=sys.stderr)
        return {}
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            try:
                if yaml is not None:
                    loaded = yaml.safe_load(frontmatter) or {}
                    if isinstance(loaded, dict):
                        return loaded
            except Exception as exc:
                print(f"warning: PyYAML failed for {path}: {exc}", file=sys.stderr)
            return parse_simple_yaml(frontmatter)
    return parse_simple_yaml(text)


def config_paths(lesson_dir_arg: str | None) -> tuple[Path, Path, Path]:
    if lesson_dir_arg:
        lessons_dir = expand(lesson_dir_arg)
        memo_dir = lessons_dir.parent
    else:
        memo_dir = DEFAULT_MEMO_DIR
        lessons_dir = expand(memo_dir / "lessons")
    config = load_json(memo_dir / "config.json", {})
    lessons_dir = expand(config.get("lessons_dir", str(lessons_dir))) if not lesson_dir_arg else lessons_dir
    registry_file = expand(config.get("registry_file", str(memo_dir / "registry.json")))
    return memo_dir, lessons_dir, registry_file


def normalize_text(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(normalize_text(item) for item in value)
    return str(value or "").lower()


def query_tokens(query: str) -> set[str]:
    lowered = query.lower()
    tokens = set(re.findall(r"[a-z0-9_./+-]+|[\u4e00-\u9fff]{2,}", lowered))
    for token in list(tokens):
        if re.search(r"[\u4e00-\u9fff]", token) and len(token) > 2:
            tokens.update(token[i : i + 2] for i in range(len(token) - 1))
    return {token for token in tokens if len(token) >= 2}


def infer_domains(query: str) -> set[str]:
    lowered = query.lower()
    domains = set()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            domains.add(domain)
    return domains


def match_score(lesson: dict[str, Any], query: str) -> float:
    lowered = query.lower()
    domains = infer_domains(query)
    tokens = query_tokens(query)
    score = 0.0

    domain = normalize_text(lesson.get("domain"))
    if domain and domain in domains:
        score += 4.0
    if domain and domain in lowered:
        score += 3.0

    tags = normalize_text(lesson.get("tags"))
    title = normalize_text(lesson.get("title"))
    lesson_text = normalize_text(lesson.get("lesson"))
    trigger = normalize_text(lesson.get("trigger"))
    haystack = f"{title} {lesson_text} {trigger} {tags} {domain}"

    for token in tokens:
        if token in tags:
            score += 2.0
        if token in title:
            score += 2.0
        if token in trigger:
            score += 1.5
        if token in lesson_text:
            score += 1.0
        if token in domain:
            score += 1.0
        if token in haystack:
            score += 0.2
    return score


def load_lessons(registry_file: Path, lessons_dir: Path) -> list[dict[str, Any]]:
    registry = load_json(registry_file, {"lessons": []})
    entries = registry.get("lessons", []) if isinstance(registry, dict) else []
    lessons: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        file_value = entry.get("file")
        lesson_path = expand(file_value) if file_value else None
        if lesson_path is None or not lesson_path.exists():
            lesson_id = str(entry.get("id", ""))
            candidates = list(lessons_dir.glob(f"{lesson_id}.md")) if lesson_id else []
            lesson_path = candidates[0] if candidates else None
        lesson = parse_lesson_file(lesson_path) if lesson_path else {}
        merged = {**entry, **lesson}
        if lesson_path:
            merged["file"] = str(lesson_path)
        lessons.append(merged)
    return lessons


def first_line(text: Any, max_len: int = 180) -> str:
    line = " ".join(str(text or "").strip().split())
    if len(line) > max_len:
        return line[: max_len - 1].rstrip() + "..."
    return line


def format_markdown(matches: list[dict[str, Any]]) -> str:
    if not matches:
        return "## 历史教训参考（自动检索自错题本）\n\n未找到匹配的历史教训。"

    lines = ["## 历史教训参考（自动检索自错题本）", ""]
    for idx, lesson in enumerate(matches, 1):
        confidence = float(lesson.get("confidence") or 0.0)
        source = lesson.get("source") or lesson.get("source_type") or "lesson-memo"
        title = lesson.get("title") or lesson.get("id") or "未命名教训"
        lines.append(f"{idx}. **[{confidence:.2f}] {title}**（来自 {source}）")
        if lesson.get("trigger"):
            lines.append(f"   触发条件：{first_line(lesson.get('trigger'), 140)}")
        if lesson.get("lesson"):
            lines.append(f"   教训：{first_line(lesson.get('lesson'), 220)}")
        if lesson.get("action"):
            lines.append(f"   行动：{first_line(lesson.get('action'), 180)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Recall relevant lesson-memo entries.")
    parser.add_argument("--query", required=True, help="Task or plan description to match.")
    parser.add_argument("--top", type=int, default=None, help="Maximum lessons to print.")
    parser.add_argument("--min-confidence", type=float, default=None, help="Minimum confidence threshold.")
    parser.add_argument("--lesson-dir", help="Override lesson directory, default ~/.claude/lesson-memo/lessons.")
    args = parser.parse_args()

    _, lessons_dir, registry_file = config_paths(args.lesson_dir)
    config = load_json(registry_file.parent / "config.json", {})
    top = args.top if args.top is not None else int(config.get("default_top_n", 5))
    min_conf = args.min_confidence if args.min_confidence is not None else float(config.get("min_confidence", 0.3))

    if top <= 0:
        print("error: --top must be positive", file=sys.stderr)
        return 2
    if not registry_file.exists():
        print(f"error: registry not found: {registry_file}", file=sys.stderr)
        return 1

    candidates = []
    for lesson in load_lessons(registry_file, lessons_dir):
        confidence = float(lesson.get("confidence") or 0.0)
        if confidence < min_conf:
            continue
        score = match_score(lesson, args.query)
        if score > 0:
            candidates.append((confidence, score, lesson))

    candidates.sort(key=lambda item: (-item[0], -item[1], str(item[2].get("id", ""))))
    print(format_markdown([lesson for _, _, lesson in candidates[:top]]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
