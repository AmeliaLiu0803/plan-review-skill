#!/usr/bin/env python3
"""
review-init: Create review document skeletons from plan files.

Usage:
    python init_review.py                    # scan all plans without reviews
    python init_review.py my-plan.md         # create review for specific plan
"""

import sys
import os
import re
import glob
from datetime import datetime
from pathlib import Path

PLANS_DIR = Path(os.path.expanduser("~/.claude/plans"))
BASELINES_DIR = PLANS_DIR / ".baselines"
REVIEWS_DIR = Path(os.path.expanduser("~/.claude/reviews"))


def plan_to_review_name(plan_filename: str) -> str:
    """Convert plan filename to review filename."""
    name = plan_filename
    stem, ext = os.path.splitext(name)
    if stem.lower().endswith("-plan"):
        return f"{stem[:-5]}-review{ext}"
    if "-plan-" in stem.lower() and not stem.lower().endswith("-review"):
        idx = stem.lower().rfind("-plan-")
        return f"{stem[:idx]}-review-{stem[idx + 6:]}{ext}"
    return f"{stem}-review{ext}"


def create_baseline(plan_path: Path) -> str:
    """Create a baseline snapshot of the plan for future diff comparison."""
    BASELINES_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    baseline_name = f"{plan_path.name}.{timestamp}.md"
    baseline_path = BASELINES_DIR / baseline_name

    import shutil
    shutil.copy2(plan_path, baseline_path)

    # Clean old baselines, keep only the most recent 5
    existing = sorted(BASELINES_DIR.glob(f"{plan_path.name}.*.md"))
    for old in existing[:-5]:
        old.unlink()

    return baseline_name


def extract_phases(plan_content: str) -> list[dict]:
    """Extract Phase sections from a plan markdown file."""
    phases = []
    pattern = re.compile(
        r"^#{1,4}\s+(?:Task\s+\S+:\s+)?(Phase\s+\d+)[\s:]*([^\n]*)", re.MULTILINE
    )
    matches = list(pattern.finditer(plan_content))

    for i, match in enumerate(matches):
        phase_label = match.group(1).strip()
        phase_name = match.group(2).strip().strip(":").strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(plan_content)
        body = plan_content[start:end].strip()

        deliverable = ""
        for line in body.split("\n"):
            if "Deliverable" in line or "deliverable" in line:
                deliverable = re.sub(
                    r"^[\*\-]?\s*\*\*.*Deliverable:\*\*\s*", "", line
                ).strip()
                break

        time_est = ""
        for line in body.split("\n"):
            m = re.search(r"(\d+)\s*天", line)
            if m:
                time_est = f"{m.group(1)} 天"
                break

        pending = []
        for line in body.split("\n"):
            if "[待核实]" in line:
                pending.append(line.strip())

        phases.append(
            {
                "label": phase_label,
                "name": phase_name,
                "deliverable": deliverable,
                "time_est": time_est,
                "pending_items": pending,
            }
        )

    return phases


def extract_pending_questions(plan_content: str) -> list[str]:
    """Extract all [待核实] questions from plan."""
    questions = []
    pattern = re.compile(r"(?:^|\n)[^\n]*\[待核实\][^\n]*", re.MULTILINE)
    for m in pattern.finditer(plan_content):
        line = m.group(0).strip()
        if line:
            questions.append(line)
    return questions


def extract_overview(plan_content: str) -> str:
    """Extract the overview/title from plan."""
    m = re.search(r"^#\s+(.+)$", plan_content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return "Unknown Project"


def generate_review(plan_filename: str, plan_content: str, baseline_name: str) -> str:
    """Generate a review document from plan content."""
    now = datetime.now().strftime("%Y-%m-%d")
    title = extract_overview(plan_content)
    phases = extract_phases(plan_content)
    pending = extract_pending_questions(plan_content)

    parts = [
        f"# {title} — Review",
        "",
        "## 基本信息",
        "",
        "| 项目 | 计划 | 实际 |",
        "|------|------|------|",
        f"| 开始日期 | {now} | 未开始 |",
        f"| 结束日期 | — | 未开始 |",
        "| 总天数 | 按计划 | 待填写 |",
        "| 当前状态 | — | 进行中 |",
        "",
    ]

    # Phase sections
    parts.append("## Phase 回顾")
    parts.append("")

    if phases:
        for phase in phases:
            parts.append(f"### {phase['label']}: {phase['name']}")
            parts.append("")
            parts.append("| 维度 | 预期 | 实际 | 偏差原因 |")
            parts.append("|------|------|------|----------|")
            time_cell = phase["time_est"] if phase["time_est"] else "按计划"
            parts.append(f"| 时间 | {time_cell} | 未开始 | |")
            deliv = phase["deliverable"] if phase["deliverable"] else "见 plan"
            parts.append(f"| Deliverable | {deliv} | 待填写 | |")
            parts.append(f"| 质量门槛 | 按计划 | 待填写 | |")
            parts.append("")

            if phase["pending_items"]:
                parts.append("#### 待确认")
                for item in phase["pending_items"]:
                    parts.append(f"- [ ] {item}")
                parts.append("")

            # Phase-level lessons learned area
            parts.append("#### 经验教训")
            parts.append("")
            parts.append("- （暂无）")
            parts.append("")
    else:
        parts.append("### 任务对照")
        parts.append("")
        parts.append("| 计划事项 | 实际执行 | 偏差原因 | 状态 |")
        parts.append("|---------|---------|----------|------|")
        parts.append(f"| 见 plan: {plan_filename} | 待填写 | | 未开始 |")
        parts.append("")

    # Pending questions from plan
    if pending:
        parts.append("## 待确认问题（来自 plan）")
        parts.append("")
        for q in pending:
            parts.append(f"- [ ] {q}")
        parts.append("")

    # Overall summary section
    parts.extend(
        [
            "---",
            "",
            "## 整体总结",
            "",
            "### 做了什么（vs plan）",
            "",
            "| 计划事项 | 实际执行 | 偏差 |",
            "|---------|---------|------|",
            "| 待填写 | 待填写 | |",
            "",
            "### 犯错教训",
            "",
            "1. （暂无）",
            "",
            "### 下期改进",
            "",
            "1. （暂无）",
            "",
            "---",
            "",
            "## 规划变更记录",
            "",
            "> 当 plan 文件被修改时，这里会追加 diff 记录。首次创建时 baseline 已保存。",
            "",
            "| 时间 | 变更摘要 | diff |",
            "|------|---------|------|",
            "",
            "---",
            "",
            "## 更新日志",
            "",
            "| 时间 | 变更 | 触发方式 |",
            "|------|------|----------|",
            f"| {datetime.now().strftime('%Y-%m-%d %H:%M')} | 创建初始骨架，预填 {len(phases)} 个 Phase；baseline: `{baseline_name}` | /review:init |",
            "",
        ]
    )

    return "\n".join(parts)


def main():
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) > 1:
        plan_files = [sys.argv[1]]
    else:
        plan_files = [f.name for f in PLANS_DIR.glob("*.md")]
        if not plan_files:
            print("[review-init] No plan files found in ~/.claude/plans/")
            return

    created = []
    skipped = []

    existing_reviews = {f.name for f in REVIEWS_DIR.glob("*.md")}

    for pf in plan_files:
        review_name = plan_to_review_name(pf)
        if review_name in existing_reviews:
            skipped.append(pf)
            continue

        plan_path = PLANS_DIR / pf
        plan_content = plan_path.read_text(encoding="utf-8")
        baseline_name = create_baseline(plan_path)
        review_content = generate_review(pf, plan_content, baseline_name)
        review_path = REVIEWS_DIR / review_name
        review_path.write_text(review_content, encoding="utf-8")
        created.append((pf, review_name, baseline_name))

    if created:
        print(f"[review-init] Created {len(created)} review(s):")
        for plan, review, baseline in created:
            print(f"  {plan} → {review}")
            print(f"    baseline: {baseline}")
        print(f"  Saved to: {REVIEWS_DIR}")
    else:
        print("[review-init] All plans already have corresponding reviews.")

    if skipped:
        print(
            f"[review-init] Skipped {len(skipped)} (already exists): {', '.join(skipped)}"
        )


if __name__ == "__main__":
    main()
