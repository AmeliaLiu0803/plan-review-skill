# Plan Review Skill

> Automatically track plan changes, compare planned vs. actual execution, and record lessons learned — for Claude Code.

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-8B5CF6)](https://claude.ai/code)

English | [中文](README_CN.md)

## The Problem

You write a plan. Then it changes — 10 times over the course of a project.

The three most painful patterns in long-horizon work:

1. **Context drift** — The AI session grows, compaction fires, and every plan change you made is gone. "Last week the AI knew about this approach… now it forgot."
2. **No way to verify AI execution against the plan** — The AI says "done." But what did it actually do? Does it match the plan? You can't audit every line of code.
3. **Wishes into the void** — You say "remember to do X" mid-session. The AI says "sure." Then the session ends and nobody follows up. Nobody recorded it. Nobody confirmed it happened.

For anyone managing long-horizon tasks — developers, researchers, project managers, students — plan iterations are normal. But without systematic tracking, you lose all the context of *why* things changed and *what* you learned.

## The Solution

**Plan Review** is a pair of Claude Code skills that automatically:

1. **Generates review documents** from your plan files — pre-filled with expected phases, timelines, deliverables, and open questions.
2. **Tracks plan changes with diffs** — every time your plan is modified, the skill records a git-style diff, timestamp, and summary. **Session compacted? Change history persists.**
3. **Compares planned vs. actual** — structured tables for each phase: planned time, actual time, deliverables, quality gates, and deviation reasons. **AI says "done" — this shows whether what was done matches the plan.**
4. **Records lessons learned** — structured sections for each phase and overall project, so mistakes and insights are never lost.
5. **Auto-triggers** — updates at session end, phase completion, or plan change detection. **No more wishes into the void: progress is captured and confirmed automatically.**

## Quick Start

### Install

```bash
git clone https://github.com/AmeliaLiu0803/plan-review-skill.git
cp -r plan-review-skill/skills/* ~/.claude/skills/
```

That's it. Two new commands are now available in Claude Code.

### Usage

**Create a review document** from an existing plan:

```
/plan-review:init                          # create reviews for all plans without reviews
/plan-review:init my-plan.md               # create review for a specific plan
```

**Update a review** with latest progress:

```
/plan-review:update                        # update all in-progress reviews
/plan-review:update my-review.md           # update a specific review
```

**Manage the lesson-memo knowledge base**:

```
/lesson-memo:extract                       # extract lessons from historical reviews and memories
/lesson-memo:recall "task description"     # recall relevant lessons for a task
/lesson-memo:list                          # list all stored lessons
/lesson-memo:status                        # show knowledge base statistics
```

### File Layout

Your files live in `~/.claude/`:

```
~/.claude/
├── lesson-memo/
│   ├── lessons/                       # one YAML file per lesson
│   ├── registry.json                  # lesson index
│   ├── config.json                    # recall thresholds
│   └── .last_session_state.json       # session extraction state
├── plans/
│   ├── .baselines/                    # auto-managed plan snapshots (5 most recent per plan)
│   │   ├── my-plan.md.20260607-1000.md
│   │   └── my-plan.md.20260607-1500.md
│   └── my-plan.md                     # your current plan
├── reviews/
│   └── my-review.md                   # the generated review document
└── skills/
    ├── plan-review-init/
    │   ├── SKILL.md
    │   └── scripts/init_review.py
    ├── plan-review-update/
    │   ├── SKILL.md
    │   └── scripts/update_review.py
    └── plan-review-companion/
        ├── SKILL.md
        └── scripts/
            ├── extract.py
            ├── recall.py
            └── session_extract.py
```

## Features

### Automatic Plan Diff Tracking

Every time `plan-review:update` runs, it compares the current plan against the last saved baseline. If changes are detected:

- A new row is added to the "Plan Change Log" table
- A collapsible diff block is appended
- A new baseline snapshot is saved (5 most recent per plan are kept)

### Lesson-Memo Companion

`plan-review-companion` adds a lesson-memo system: a lightweight knowledge base that extracts mistakes, lessons, and next-step improvements from historical reviews and memory files.

It supports four commands:

| Command | Purpose |
|---------|---------|
| `/lesson-memo:extract` | Extract lessons from historical reviews and feedback memories |
| `/lesson-memo:recall "task description"` | Retrieve the most relevant lessons for the current task |
| `/lesson-memo:list` | List every stored lesson with confidence and domain |
| `/lesson-memo:status` | Show lesson count and domain statistics |

The companion also supports automatic lesson injection. When `/plan-review:init` creates a review, the recall script can search the lesson-memo knowledge base and append a "Historical Lessons Reference" section to the review. At session end, `session_extract.py` can capture fresh lessons through the Stop hook so the knowledge base keeps improving across projects.

### Structured Review Document

Each review document contains:

| Section | Content |
|---------|---------|
| **Basic Info** | Planned vs. actual start/end dates, total days, current status |
| **Phase Review** | Per-phase comparison: planned time, deliverables, quality gates, actual results, deviation reasons |
| **Lessons Learned** | Lessons learned per phase |
| **Open Questions** | Open questions extracted from plan file markers (e.g. `[pending verification]` tags) |
| **Overall Summary** | What was done vs. plan, mistakes/lessons, next improvements |
| **Plan Change Log** | Timestamped log of all plan changes with diffs |
| **Update Log** | Log of all review updates with trigger source |

### Auto-Trigger Rules

| Trigger | Mode | What it updates |
|---------|------|-----------------|
| Session end | Light | Time, status, plan diff check |
| Phase completion | Full | Deviation analysis, lessons learned, plan diff |
| Manual command | Full | Everything |
| Plan file change | Light | Diff recording only |

## Example

Here's what a filled-out review document looks like:

```markdown
# Implementation Plan: MARL RCA MVP — Review

## Basic Info
| Item | Planned | Actual |
|------|---------|--------|
| Start Date | 2026-06-07 | 2026-06-07 |
| End Date | 2026-08-01 | In Progress |
| Total Days | 52 days | In Progress |
| Status | — | In Progress |

## Phase Review

### Phase 0: Environment Setup + Repo Init (3 days)
| Dimension | Expected | Actual | Deviation Reason |
|-----------|----------|--------|-------------------|
| Time | 3 days | 4 days | +1 day: conda environment dependency conflict |
| Deliverable | Three repos + conda env | ✅ Complete | |

## Plan Change Log
| Time | Change Summary | diff |
|------|---------------|------|
| 2026-06-10 14:00 | Phase 2 time from 7d → 10d | See diff below |

<details>
<summary>diff: Phase 2 time adjustment</summary>

```diff
- ### Phase 2: 3 Toy Experiments (7 days)
+ ### Phase 2: 3 Toy Experiments (10 days)
```
</details>
```

## Who Is This For?

Anyone managing **long-horizon tasks** — work that unfolds in phases and where plans evolve over time:

- **Developers** tracking feature iterations, spec changes, and timeline deviations
- **Researchers** running experiments with evolving protocols and reproducibility logs
- **Project managers** comparing planned vs. actual milestones across sprints
- **Students** managing thesis, dissertation, or experiment timelines
- **Teams** who want structured lessons-learned documentation across plan iterations
- **Anyone using Claude Code** who wants systematic plan-vs-actual tracking that persists across sessions

## License

MIT
