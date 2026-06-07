# Plan Review Skill

> Automatically track plan changes, compare planned vs. actual execution, and record lessons learned — for Claude Code.

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-8B5CF6)](https://claude.ai/code)

## The Problem

You write a plan. Then it changes — 10 times over the course of a project.

- **What changed?** You forgot.
- **What was the original plan?** You can't remember.
- **Planned vs. actual?** You estimate from memory.
- **Lessons learned?** Somewhere in a file you can't find.

Especially for researchers, project managers, and students — plan iterations are normal. But without systematic tracking, you lose all the context of *why* things changed and *what* you learned.

## The Solution

**Plan Review** is a pair of Claude Code skills that automatically:

1. **Generates review documents** from your plan files — pre-filled with expected phases, timelines, deliverables, and open questions.
2. **Tracks plan changes with diffs** — every time your plan is modified, the skill records a git-style diff, timestamp, and summary.
3. **Compares planned vs. actual** — structured tables for each phase: planned time, actual time, deliverables, quality gates, and deviation reasons.
4. **Records lessons learned** — structured sections for each phase and overall project, so mistakes and insights are never lost.
5. **Auto-triggers** — updates at session end, phase completion, or plan change detection.

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

### File Layout

Your files live in `~/.claude/`:

```
~/.claude/
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
    └── plan-review-update/
        ├── SKILL.md
        └── scripts/update_review.py
```

## Features

### Automatic Plan Diff Tracking

Every time `plan-review:update` runs, it compares the current plan against the last saved baseline. If changes are detected:

- A new row is added to the "规划变更记录" (Plan Change Log) table
- A collapsible diff block is appended
- A new baseline snapshot is saved (5 most recent per plan are kept)

### Structured Review Document

Each review document contains:

| Section | Content |
|---------|---------|
| **基本信息** | Planned vs. actual start/end dates, total days, current status |
| **Phase 回顾** | Per-phase comparison: planned time, deliverables, quality gates, actual results, deviation reasons |
| **经验教训** | Lessons learned per phase |
| **待确认问题** | Open questions extracted from the plan's `[待核实]` markers |
| **整体总结** | What was done vs. plan, mistakes/lessons, next improvements |
| **规划变更记录** | Timestamped log of all plan changes with diffs |
| **更新日志** | Log of all review updates with trigger source |

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

## 基本信息
| 项目 | 计划 | 实际 |
|------|------|------|
| 开始日期 | 2026-06-07 | 2026-06-07 |
| 结束日期 | 2026-08-01 | 进行中 |
| 总天数 | 52 天 | 进行中 |
| 当前状态 | — | 进行中 |

## Phase 回顾

### Phase 0: 环境搭建 + Repo 初始化（3 天）
| 维度 | 预期 | 实际 | 偏差原因 |
|------|------|------|----------|
| 时间 | 3 天 | 4 天 | +1 天：conda 环境依赖冲突 |
| Deliverable | 三个 repo + conda 环境 | ✅ 完成 | |

## 规划变更记录
| 时间 | 变更摘要 | diff |
|------|---------|------|
| 2026-06-10 14:00 | Phase 2 时间从 7天→10 天 | 见下方 diff |

<details>
<summary>diff: Phase 2 时间调整</summary>

```diff
- ### Phase 2: 3 个 Toy 实验（7 天）
+ ### Phase 2: 3 个 Toy 实验（10 天）
```
</details>
```

## Who Is This For?

- **Researchers** running experiments with evolving plans
- **Project managers** tracking planned vs. actual progress
- **Students** managing thesis/experiment timelines
- **Anyone using Claude Code** who wants systematic plan-vs-actual tracking
- **Teams** who want structured lessons-learned documentation

## License

MIT
