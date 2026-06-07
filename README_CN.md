# Plan Review 技能

> 自动追踪计划变更、对比计划与实际执行情况、记录经验教训 —— 专为 Claude Code 设计。

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-8B5CF6)](https://claude.ai/code)

[English README](README.md) | 中文文档

## 问题

你写了一个计划。然后它变了——整个项目期间改了 10 次。

- **改了什么？** 你忘了。
- **最初的计划是什么？** 想不起来了。
- **计划 vs 实际？** 凭记忆估算。
- **经验教训？** 藏在某个找不到的文件里。

对研究人员、项目经理和学生来说，计划反复修改很正常。但如果没有系统追踪，你就会丢失所有关于 *为什么改* 和 *学到了什么* 的上下文。

## 解决方案

**Plan Review** 是一对 Claude Code 技能，能够自动：

1. **从计划文件生成 review 文档** —— 预填预期阶段、时间线、交付物和待确认问题。
2. **用 diff 追踪计划变更** —— 每次修改计划，技能都会记录 git 风格的 diff、时间戳和摘要。
3. **对比计划与实际** —— 每个阶段的结构化表格：计划时间、实际时间、交付物、质量门控、偏差原因。
4. **记录经验教训** —— 每个阶段和整个项目的结构化章节，错误和洞察永远不会丢失。
5. **自动触发** —— 会话结束、阶段完成或检测到计划变更时自动更新。

## 快速开始

### 安装

```bash
git clone https://github.com/AmeliaLiu0803/plan-review-skill.git
cp -r plan-review-skill/skills/* ~/.claude/skills/
```

就这样。两个新命令即可使用。

### 使用

**从现有计划创建 review 文档：**

```
/plan-review:init                          # 为所有没有 review 的计划创建 review
/plan-review:init my-plan.md               # 为特定计划创建 review
```

**用最新进展更新 review：**

```
/plan-review:update                        # 更新所有进行中的 review
/plan-review:update my-review.md           # 更新特定 review
```

### 文件布局

你的文件存放在 `~/.claude/` 下：

```
~/.claude/
├── plans/
│   ├── .baselines/                    # 自动管理的计划快照（每个计划保留最近 5 份）
│   │   ├── my-plan.md.20260607-1000.md
│   │   └── my-plan.md.20260607-1500.md
│   └── my-plan.md                     # 你当前的计划
├── reviews/
│   └── my-review.md                   # 生成的 review 文档
└── skills/
    ├── plan-review-init/
    │   ├── SKILL.md
    │   └── scripts/init_review.py
    └── plan-review-update/
        ├── SKILL.md
        └── scripts/update_review.py
```

## 功能

### 自动计划 Diff 追踪

每次运行 `plan-review:update` 时，它会将当前计划与上次保存的基线进行比较。如果检测到变更：

- 在「规划变更记录」表中新增一行
- 追加一个可折叠的 diff 区块
- 保存新的基线快照（每个计划保留最近 5 份）

### 结构化 Review 文档

每个 review 文档包含：

| 章节 | 内容 |
|------|------|
| **基本信息** | 计划 vs 实际开始/结束日期、总天数、当前状态 |
| **Phase 回顾** | 逐阶段对比：计划时间、交付物、质量门控、实际结果、偏差原因 |
| **经验教训** | 每个阶段的经验教训 |
| **待确认问题** | 从计划的 `[待核实]` 标记中提取的待确认问题 |
| **整体总结** | 做了什么 vs 计划、错误/教训、下一步改进 |
| **规划变更记录** | 所有计划变更的时间戳记录，附带 diff |
| **更新日志** | 所有 review 更新的记录，包含触发来源 |

### 自动触发规则

| 触发条件 | 模式 | 更新内容 |
|----------|------|----------|
| 会话结束 | 轻量 | 时间、状态、计划 diff 检查 |
| 阶段完成 | 完整 | 偏差分析、经验教训、计划 diff |
| 手动命令 | 完整 | 所有内容 |
| 计划文件变更 | 轻量 | 仅记录 diff |

## 示例

以下是填写好的 review 文档示例：

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

## 适合谁

- **研究人员** —— 执行计划不断演进的研究项目
- **项目经理** —— 追踪计划 vs 实际进度
- **学生** —— 管理论文/实验时间线
- **任何使用 Claude Code 的人** —— 想要系统化的计划 vs 实际追踪
- **团队** —— 需要结构化的经验教训文档

## License

MIT
