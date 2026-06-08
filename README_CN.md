# Plan Review 技能

> 为 Claude Code 设计的三技能闭环系统：追踪计划变更、审查执行情况、复用历史教训。

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-8B5CF6)](https://claude.ai/code)

[English README](README.md) | 中文文档

## 问题

你写了一个计划。然后它变了——整个项目期间改了 10 次。

长程任务中最痛的三个问题：

1. **上下文漂移** — AI session 越跑越长，compaction 一压缩，之前改过的计划、调整过的方案全部丢失
2. **难以核实 AI 执行是否与规划一致** — AI 说"已完成"，但实际做了什么？和计划对得上吗？你不可能逐行验证
3. **许愿不知愿望是否真正实现** — session 里说"记得做 X"，AI 说"好的"——然后呢？没人记录，没人确认

对于任何会反复调整计划的长程任务（开发迭代、科研实验、项目管理、论文写作），没有系统追踪 = 丢失所有关于 *为什么改* 和 *学到了什么* 的上下文。

## 解决方案

**Plan Review** 是一个完整的三技能闭环：

1. **初始化**：使用 `/plan-review:init` 从计划生成结构化 review 文档，预填阶段、时间线、交付物、质量门控和待确认问题。
2. **更新**：使用 `/plan-review:update` 对比计划与实际执行，记录进展，捕获计划 diff，并跨 session 保持 review 最新。
3. **提取与召回**：使用 `/plan-review:extract` 和 `/plan-review:recall` 把 review 教训沉淀到错题本知识库，并在下一次规划或执行前召回相关教训。

闭环如下：

```text
plan -> /plan-review:init -> review 骨架
review + 变更后的 plan -> /plan-review:update -> 执行审查 + diff + 新教训
reviews + memories -> /plan-review:extract -> 错题本知识库
新任务 -> /plan-review:recall -> 相关历史教训注入下一轮规划
```

三个技能合在一起，让计划历史可追踪、执行过程可审查、历史教训可复用。

## 快速开始

### 安装

```bash
git clone https://github.com/AmeliaLiu0803/plan-review-skill.git
cp -r plan-review-skill/skills/* ~/.claude/skills/
```

### 命令

**从现有计划创建 review 文档：**

```text
/plan-review:init                          # 为所有没有 review 的计划创建 review
/plan-review:init my-plan.md               # 为特定计划创建 review
```

**用最新进展更新 review：**

```text
/plan-review:update                        # 更新所有进行中的 review
/plan-review:update my-review.md           # 更新特定 review
```

**管理错题本知识库：**

```text
/plan-review:extract                       # 从历史 review 和 memory 中提取教训
/plan-review:recall "任务描述"             # 为当前任务召回相关教训
/plan-review:list                          # 列出所有已保存教训
/plan-review:status                        # 查看知识库统计
```

## 架构

```text
┌────────────────────┐
│ plan-review-init   │
│ /plan-review:init  │
│ plan -> review     │
└─────────┬──────────┘
          │ 创建 review 骨架
          v
┌────────────────────┐
│ plan-review-update │
│ /plan-review:update│
│ review + diffs     │
└─────────┬──────────┘
          │ 记录教训
          v
┌────────────────────────┐
│ plan-review-companion  │
│ extract / recall / list│
│ 错题本知识库           │
└─────────┬──────────────┘
          │ 为下一次任务召回教训
          └──────────────> /plan-review:init 和后续执行
```

## 文件布局

你的文件存放在 `~/.claude/` 下：

```text
~/.claude/
├── lesson-memo/
│   ├── lessons/                       # 每条教训一个 YAML 文件
│   ├── registry.json                  # 教训索引
│   ├── config.json                    # 召回阈值配置
│   └── .last_session_state.json       # session 提取状态
├── plans/
│   ├── .baselines/                    # 自动管理的计划快照，每个计划保留最近 5 份
│   │   ├── my-plan.md.20260607-1000.md
│   │   └── my-plan.md.20260607-1500.md
│   └── my-plan.md                     # 你当前的计划
├── reviews/
│   └── my-review.md                   # 生成的 review 文档
└── skills/
    ├── plan-review-init/
    │   ├── SKILL.md
    │   └── scripts/init_review.py
    ├── plan-review-update/
    │   ├── SKILL.md
    │   └── scripts/update_review.py
    ├── plan-review-companion/         # extract/recall/list/status 共享脚本
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

## 功能

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
| **更新日志** | 所有 review 更新记录，包含触发来源 |

### 自动计划 Diff 追踪

每次运行 `/plan-review:update` 时，它会将当前计划与上次保存的基线进行比较。如果检测到变更：

- 在「规划变更记录」表中新增一行
- 追加一个可折叠的 diff 区块
- 保存新的基线快照，每个计划保留最近 5 份

### 错题本知识库

`plan-review-companion` 会从历史 review 和反馈 memory 中提取错误、教训和下一步改进。

| 命令 | 用途 |
|------|------|
| `/plan-review:extract` | 从历史 review 和反馈 memory 中提取教训 |
| `/plan-review:recall "任务描述"` | 为当前任务召回最相关的教训 |
| `/plan-review:list` | 列出所有已保存教训及其 confidence 和 domain |
| `/plan-review:status` | 查看教训数量和 domain 统计 |

当 `/plan-review:init` 创建 review 后，recall 可以把「历史教训参考」章节追加到 review 中。Session 结束时，`session_extract.py` 可以通过 Stop hook 捕获新的教训，让知识库在项目之间持续积累。

### 自动触发规则

| 触发条件 | 模式 | 更新内容 |
|----------|------|----------|
| Session 结束 | 轻量 | 时间、状态、计划 diff 检查、新教训提取 |
| Phase 完成 | 完整 | 偏差分析、经验教训、计划 diff |
| 手动命令 | 完整 | 当前命令要求的全部内容 |
| 计划文件变更 | 轻量 | 仅记录 diff |
| Review 创建 | 召回 | 把历史教训注入新 review |

## 示例

````markdown
# Implementation Plan: MARL RCA MVP - Review

## 基本信息
| 项目 | 计划 | 实际 |
|------|------|------|
| 开始日期 | 2026-06-07 | 2026-06-07 |
| 结束日期 | 2026-08-01 | 进行中 |
| 总天数 | 52 天 | 进行中 |
| 当前状态 | - | 进行中 |

## Phase 回顾

### Phase 0: 环境搭建 + Repo 初始化（3 天）
| 维度 | 预期 | 实际 | 偏差原因 |
|------|------|------|----------|
| 时间 | 3 天 | 4 天 | +1 天：conda 环境依赖冲突 |
| Deliverable | 三个 repo + conda 环境 | 完成 | |

## 历史教训参考
| 教训 | 行动 |
|------|------|
| 写脚本前先确认平台相关路径处理。 | 在当前 shell 上验证路径后再运行自动化。 |

## 规划变更记录
| 时间 | 变更摘要 | Diff |
|------|----------|------|
| 2026-06-10 14:00 | Phase 2 时间从 7 天调整为 10 天 | 见下方 diff |

<details>
<summary>diff: Phase 2 时间调整</summary>

```diff
- ### Phase 2: 3 个 Toy 实验（7 天）
+ ### Phase 2: 3 个 Toy 实验（10 天）
```
</details>
````

## 适合谁

任何管理 **长程任务** 的人：分阶段执行、计划会反复调整的工作都适用。

- **开发者**：追踪功能迭代、需求变更、进度偏差
- **研究人员**：管理实验方案演进和可追溯记录
- **项目经理**：对比计划 vs 实际里程碑
- **学生**：管理论文、毕业设计、实验时间线
- **团队**：沉淀跨版本的结构化经验教训
- **任何使用 Claude Code 的人**：想要跨 session 持久保存计划与执行审查记录

## License

MIT
