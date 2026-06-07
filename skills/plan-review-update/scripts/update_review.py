#!/usr/bin/env python3
"""
review-update: Update an existing review document with latest execution progress.

Usage:
    python update_review.py                        # update all in-progress reviews
    python update_review.py my-review.md           # update specific review
    python update_review.py --auto                 # auto-mode: only update time + status + plan diff
    python update_review.py --full                 # full update: include deviation analysis + lessons
"""

import sys
import os
import re
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

REVIEWS_DIR = Path(os.path.expanduser("~/.claude/reviews"))
PLANS_DIR = Path(os.path.expanduser("~/.claude/plans"))
BASELINES_DIR = PLANS_DIR / ".baselines"
MEMORY_DIR = Path(os.path.expanduser("~/.claude/projects/-home-amelialiu/memory"))


def get_git_log(since_days: int = 30) -> str:
    """Get recent git log for execution context."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"--since={since_days} days ago", "--no-merges"],
            capture_output=True, text=True, timeout=5,
            cwd=os.path.expanduser("~"),
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def get_recent_memory_updates() -> list[dict]:
    """Get recent memory file changes."""
    try:
        files = sorted(
            MEMORY_DIR.glob("*.md"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )[:5]
        return [
            {
                "name": f.name,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            }
            for f in files
        ]
    except Exception:
        return []


def find_review_file(name: str) -> Path | None:
    """Find a review file by name (exact or partial match)."""
    if name.endswith(".md"):
        path = REVIEWS_DIR / name
        return path if path.exists() else None
    for f in REVIEWS_DIR.glob("*.md"):
        if name in f.stem:
            return f
    return None


def review_to_plan_name(review_name: str) -> str:
    """Convert review filename back to plan filename."""
    # Try reversing the init naming logic
    if "-review" in review_name:
        candidate = review_name.replace("-review", "-plan")
        if (PLANS_DIR / candidate).exists():
            return candidate
        # Maybe original didn't have "plan" — try without suffix
        candidate2 = review_name.replace("-review", "")
        if (PLANS_DIR / candidate2).exists():
            return candidate2
    # If name already is the plan name
    if (PLANS_DIR / review_name).exists():
        return review_name
    return None


def get_latest_baseline(plan_name: str) -> Path | None:
    """Get the most recent baseline for a plan."""
    if not plan_name:
        return None
    baselines = sorted(BASELINES_DIR.glob(f"{plan_name}.*.md"))
    return baselines[-1] if baselines else None


def compute_plan_diff(plan_name: str) -> str | None:
    """Compute diff between latest baseline and current plan."""
    if not plan_name:
        return None
    latest_baseline = get_latest_baseline(plan_name)
    if not latest_baseline:
        return None

    current_plan = PLANS_DIR / plan_name
    if not current_plan.exists():
        return None

    try:
        result = subprocess.run(
            ["diff", "-u", str(latest_baseline), str(current_plan)],
            capture_output=True, text=True, timeout=5,
        )
        # diff returns exit code 1 if files differ — that's expected
        if result.returncode in (0, 1) and result.stdout.strip():
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def create_baseline_snapshot(plan_name: str) -> str:
    """Create a new baseline snapshot."""
    BASELINES_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    baseline_name = f"{plan_name}.{timestamp}.md"
    baseline_path = BASELINES_DIR / baseline_name

    shutil.copy2(PLANS_DIR / plan_name, baseline_path)

    # Keep only most recent 5 baselines per plan
    existing = sorted(BASELINES_DIR.glob(f"{plan_name}.*.md"))
    for old in existing[:-5]:
        old.unlink()

    return baseline_name


def get_in_progress_reviews() -> list[Path]:
    """Find all reviews with status '进行中'."""
    results = []
    for f in REVIEWS_DIR.glob("*.md"):
        content = f.read_text(encoding="utf-8")
        if "当前状态" in content:
            # Check if status contains "进行中"
            status_match = re.search(r"当前状态[^|]*\|\s*[^|]*\|\s*([^|]+)", content)
            if status_match and "进行中" in status_match.group(1):
                results.append(f)
            elif "进行中" in content and "已完成" not in content:
                results.append(f)
    return results


def parse_last_update_time(content: str) -> str | None:
    """Extract the timestamp of the last update from the update log."""
    # Find last entry in update log table
    pattern = re.compile(r"\|\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s*\|")
    matches = pattern.findall(content)
    return matches[-1] if matches else None


def update_plan_diff_section(content: str, diff_text: str, baseline_name: str) -> str:
    """Update the plan diff change log section."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Summarize diff (first meaningful line)
    lines = [l for l in diff_text.split("\n") if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
    summary_lines = [l.strip() for l in lines[:5]]
    summary = "；".join(summary_lines) if summary_lines else "细节见 diff"

    if "## 规划变更记录" in content:
        # Insert row after the table header
        parts = content.split("## 规划变更记录")
        header = parts[0]
        rest = "## 规划变更记录" + parts[1]
        lines_content = rest.split("\n")
        insert_idx = 0
        for i, line in enumerate(lines_content):
            if "| 时间" in line or "|------" in line:
                insert_idx = i + 1
                break
        new_row = f"| {now} | {summary} | 见下方 diff |"
        lines_content.insert(insert_idx, new_row)
        rest = "\n".join(lines_content)

        # Append diff block before the next --- or at end
        diff_block = (
            f"\n<details>\n"
            f"<summary>diff: {summary[:60]}</summary>\n\n"
            f"```diff\n{diff_text}\n```\n"
            f"</details>\n"
        )

        if "---" in rest:
            # Insert before the next section separator
            sections = rest.split("---", 1)
            rest = sections[0] + diff_block + "\n---" + sections[1]
        else:
            rest += diff_block

        return header + rest
    else:
        # No diff section exists — append it
        diff_section = (
            f"\n---\n\n"
            f"## 规划变更记录\n\n"
            f"| 时间 | 变更摘要 | diff |\n"
            f"|------|---------|------|\n"
            f"| {now} | {summary} | 见下方 diff |\n\n"
            f"<details>\n"
            f"<summary>diff: {summary[:60]}</summary>\n\n"
            f"```diff\n{diff_text}\n```\n"
            f"</details>\n"
        )
        return content + diff_section


def append_update_log(content: str, summary: str, trigger: str) -> str:
    """Append or update the update log section."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    log_entry = f"| {now} | {summary} | {trigger} |"

    if "## 更新日志" in content:
        parts = content.split("## 更新日志")
        header = parts[0]
        rest = "## 更新日志" + parts[1]
        lines = rest.split("\n")
        insert_idx = 0
        for i, line in enumerate(lines):
            if "| 时间" in line or "|------" in line:
                insert_idx = i + 1
        lines.insert(insert_idx, log_entry)
        return header + "\n".join(lines)
    else:
        return (
            content
            + "\n---\n\n## 更新日志\n\n"
            + "| 时间 | 变更 | 触发方式 |\n"
            + "|------|------|----------|\n"
            + f"{log_entry}\n\n"
        )


def update_review(review_path: Path, auto: bool = False):
    """Update a single review file."""
    content = review_path.read_text(encoding="utf-8")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Determine the associated plan
    plan_name = review_to_plan_name(review_path.name)

    # Step 2: Check for plan diff
    plan_changed = False
    diff_text = None
    new_baseline = None
    if plan_name:
        diff_text = compute_plan_diff(plan_name)
        if diff_text:
            plan_changed = True
            content = update_plan_diff_section(content, diff_text, "")
            new_baseline = create_baseline_snapshot(plan_name)
            content = append_update_log(
                content,
                f"Plan 变更已记录，新 baseline: {new_baseline}",
                "自动（Plan 变更检测）"
            )

    # Step 3: Gather execution data
    git_log = get_git_log()
    memory_updates = get_recent_memory_updates()

    if auto:
        # Light update: time, status, plan diff
        summary_parts = ["轻量更新"]
        if plan_changed:
            summary_parts.append("检测到 plan 变更")
        content = append_update_log(
            content,
            "；".join(summary_parts),
            "自动（Session 结束）"
        )
    else:
        # Full update
        summary_parts = ["完整更新"]
        if plan_changed:
            summary_parts.append("Plan 已变更")
        if git_log:
            recent_commits = git_log.split("\n")[:3]
            summary_parts.append(
                f"最近 {len(recent_commits)} 个提交: {'; '.join(recent_commits)}"
            )
        if memory_updates:
            summary_parts.append(f"{len(memory_updates)} 个 memory 文件有更新")

        content = append_update_log(
            content,
            "；".join(summary_parts),
            "手动（/review:update）"
        )

    review_path.write_text(content, encoding="utf-8")
    print(f"[review-update] Updated: {review_path.name}")
    if plan_changed:
        print(f"  ⚠️ Plan 变更已记录，新 baseline: {new_baseline}")
    print(f"  Log appended at {now}")


def main():
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)

    auto_mode = "--auto" in sys.argv
    full_mode = "--full" in sys.argv

    positional = [a for a in sys.argv[1:] if not a.startswith("-")]

    if positional:
        review_file = find_review_file(positional[0])
        if not review_file:
            print(f"[review-update] Review not found: {positional[0]}")
            sys.exit(1)
        update_review(review_file, auto=auto_mode)
    elif auto_mode or full_mode:
        in_progress = get_in_progress_reviews()
        if not in_progress:
            print("[review-update] No in-progress reviews found.")
            return
        for rf in in_progress:
            update_review(rf, auto=auto_mode)
    else:
        in_progress = get_in_progress_reviews()
        if not in_progress:
            print("[review-update] No in-progress reviews found.")
            return
        for rf in in_progress:
            update_review(rf, auto=False)


if __name__ == "__main__":
    main()
