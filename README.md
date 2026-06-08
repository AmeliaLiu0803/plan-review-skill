# Plan Review Skill

> A three-skill closed-loop system for tracking plan changes, auditing execution, and reusing lessons learned in Claude Code.

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-8B5CF6)](https://claude.ai/code)

English | [Chinese](README_CN.md)

## Problem

You write a plan. Then it changes - 10 times over the course of a project.

The three most painful patterns in long-horizon work:

1. **Context drift** - The AI session grows, compaction fires, and every plan change you made is gone. "Last week the AI knew about this approach... now it forgot."
2. **No way to verify AI execution against the plan** - The AI says "done." But what did it actually do? Does it match the plan? You can't audit every line of code.
3. **Wishes into the void** - You say "remember to do X" mid-session. The AI says "sure." Then the session ends and nobody follows up. Nobody recorded it. Nobody confirmed it happened.

For anyone managing long-horizon tasks - developers, researchers, project managers, students - plan iterations are normal. But without systematic tracking, you lose all the context of *why* things changed and *what* you learned.

## Solution

**Plan Review** is a complete three-skill closed loop:

1. **Initialize** with `/plan-review:init` - generate a structured review document from a plan, including expected phases, timelines, deliverables, quality gates, and open questions.
2. **Update** with `/plan-review:update` - compare planned vs. actual execution, record progress, capture plan diffs, and keep the review current across sessions.
3. **Extract and recall** with `/plan-review:extract` and `/plan-review:recall` - turn review lessons into a lesson-memo knowledge base, then retrieve relevant lessons before the next planning or execution step.

The loop is simple:

```text
plan -> /plan-review:init -> review skeleton
review + changed plan -> /plan-review:update -> audited progress + diffs + new lessons
reviews + memories -> /plan-review:extract -> lesson-memo knowledge base
new task -> /plan-review:recall -> relevant historical lessons injected back into planning
```

Together, the three skills make plan history persistent, execution auditable, and lessons reusable.

## Quick Start

### Install

```bash
git clone https://github.com/AmeliaLiu0803/plan-review-skill.git
cp -r plan-review-skill/skills/* ~/.claude/skills/
```

### Commands

**Create a review document** from an existing plan:

```text
/plan-review:init                          # create reviews for all plans without reviews
/plan-review:init my-plan.md               # create review for a specific plan
```

**Update a review** with latest progress:

```text
/plan-review:update                        # update all in-progress reviews
/plan-review:update my-review.md           # update a specific review
```

**Manage the lesson-memo knowledge base**:

```text
/plan-review:extract                       # extract lessons from historical reviews and memories
/plan-review:recall "task description"     # recall relevant lessons for a task
/plan-review:list                          # list all stored lessons
/plan-review:status                        # show knowledge base statistics
```

## Architecture

```text
+----------------------+
| plan-review-init     |
| /plan-review:init    |
| plan -> review       |
+----------+-----------+
           |
           | creates review skeleton
           v
+----------------------+
| plan-review-update   |
| /plan-review:update  |
| review + diffs       |
+----------+-----------+
           |
           | records lessons
           v
+----------------------+
| plan-review-companion|
| extract/recall/list  |
| lesson-memo knowledge|
+----------+-----------+
           |
           | recalls lessons for the next task
           +------------> /plan-review:init and future execution
```

## File Layout

Your files live in `~/.claude/`:

```text
~/.claude/
├── lesson-memo/
│   ├── lessons/                       # one YAML file per lesson
│   ├── registry.json                  # lesson index
│   ├── config.json                    # recall thresholds
│   └── .last_session_state.json       # session extraction state
├── plans/
│   ├── .baselines/                    # auto-managed plan snapshots, 5 most recent per plan
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
    ├── plan-review-companion/         # shared scripts for extract/recall/list/status
    │   └── scripts/
    │       ├── extract.py
    │       ├── recall.py
    │       └── session_extract.py
    ├── plan-review-extract/
    │   └── SKILL.md
    ├── plan-review-recall/
    │   └── SKILL.md
    ├── plan-review-list/
    │   └── SKILL.md
    └── plan-review-status/
        └── SKILL.md
```

## Features

### Structured Review Documents

Each review document contains:

| Section | Content |
|---------|---------|
| **Basic Info** | Planned vs. actual start/end dates, total days, current status |
| **Phase Review** | Per-phase comparison: planned time, deliverables, quality gates, actual results, deviation reasons |
| **Lessons Learned** | Lessons learned per phase |
| **Open Questions** | Open questions extracted from plan file markers, such as `[pending verification]` tags |
| **Overall Summary** | What was done vs. plan, mistakes/lessons, next improvements |
| **Plan Change Log** | Timestamped log of all plan changes with diffs |
| **Update Log** | Log of all review updates with trigger source |

### Automatic Plan Diff Tracking

Every time `/plan-review:update` runs, it compares the current plan against the last saved baseline. If changes are detected:

- A new row is added to the "Plan Change Log" table
- A collapsible diff block is appended
- A new baseline snapshot is saved, with the 5 most recent snapshots kept per plan

### Lesson-Memo Knowledge Base

`plan-review-companion` extracts mistakes, lessons, and next-step improvements from historical reviews and feedback memories.

| Command | Purpose |
|---------|---------|
| `/plan-review:extract` | Extract lessons from historical reviews and feedback memories |
| `/plan-review:recall "task description"` | Retrieve the most relevant lessons for the current task |
| `/plan-review:list` | List every stored lesson with confidence and domain |
| `/plan-review:status` | Show lesson count and domain statistics |

When `/plan-review:init` creates a review, recall can append a "Historical Lessons Reference" section to the review. At session end, `session_extract.py` can capture fresh lessons through the Stop hook so the knowledge base keeps improving across projects.

### Auto-Trigger Rules

| Trigger | Mode | What it updates |
|---------|------|-----------------|
| Session end | Light | Time, status, plan diff check, new lesson extraction |
| Phase completion | Full | Deviation analysis, lessons learned, plan diff |
| Manual command | Full | Everything requested by the command |
| Plan file change | Light | Diff recording only |
| Review creation | Recall | Historical lessons injected into the new review |

## Example

````markdown
# Implementation Plan: MARL RCA MVP - Review

## Basic Info
| Item | Planned | Actual |
|------|---------|--------|
| Start Date | 2026-06-07 | 2026-06-07 |
| End Date | 2026-08-01 | In Progress |
| Total Days | 52 days | In Progress |
| Status | - | In Progress |

## Phase Review

### Phase 0: Environment Setup + Repo Init (3 days)
| Dimension | Expected | Actual | Deviation Reason |
|-----------|----------|--------|-------------------|
| Time | 3 days | 4 days | +1 day: conda environment dependency conflict |
| Deliverable | Three repos + conda env | Complete | |

## Historical Lessons Reference
| Lesson | Action |
|--------|--------|
| Check platform-specific path handling before scripting. | Validate paths on the active shell before running automation. |

## Plan Change Log
| Time | Change Summary | Diff |
|------|----------------|------|
| 2026-06-10 14:00 | Phase 2 time from 7d to 10d | See diff below |

<details>
<summary>diff: Phase 2 time adjustment</summary>

```diff
- ### Phase 2: 3 Toy Experiments (7 days)
+ ### Phase 2: 3 Toy Experiments (10 days)
```
</details>
````

## Who Is This For?

Anyone managing **long-horizon tasks**: work that unfolds in phases and where plans evolve over time.

- **Developers** tracking feature iterations, spec changes, and timeline deviations
- **Researchers** running experiments with evolving protocols and reproducibility logs
- **Project managers** comparing planned vs. actual milestones across sprints
- **Students** managing thesis, dissertation, or experiment timelines
- **Teams** who want structured lessons-learned documentation across plan iterations
- **Anyone using Claude Code** who wants systematic plan-vs-actual tracking that persists across sessions

## License

MIT
