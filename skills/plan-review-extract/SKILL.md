---
name: plan-review:extract
description: Use when extracting lessons from reviews/memories into the plan-review lesson-memo knowledge base. Trigger: "/plan-review:extract" or after plan-review:update completes with new lessons.
---

# Plan Review: Extract & Recall — 错题本系统

从历史 review 和 memory 中提取教训，在每次规划/执行时智能检索并注入相关教训，降低重复犯错概率。

## 命令

| 命令 | 描述 |
|------|------|
| `/plan-review:extract` | 从历史 review 和 memory 中提取教训入库 |
| `/plan-review:recall "任务描述"` | 为当前任务召回相关教训 |
| `/plan-review:list` | 列出所有已存储教训 |
| `/plan-review:status` | 查看知识库统计 |

## STRICT EXECUTION CHECKLIST

1. **Run the requested command** (Step 1-4)
2. **Show the result** (Step 5)

**不得跳过任何步骤。**

---

## Step 1: /plan-review:extract — 历史教训提取

**触发：** 用户输入 `/plan-review:extract`

```bash
python3 ~/.claude/skills/plan-review-companion/scripts/extract.py
```

行为：
- 扫描 `~/.claude/reviews/*.md` 提取「犯错教训」和「下期改进」章节
- 扫描 memory files (type=feedback)
- 每条教训生成 YAML 文件（id, title, domain, trigger, lesson, action, evidence, confidence=0.7）
- domain 启发式映射关键词：
  - 手写/clone/官方/复现 → `research-reproduction`
  - 依赖/接口/源码/分析 → `dependency-analysis`
  - WSL/兼容/平台/路径 → `cross-platform`
  - Codex/SSH/权限/集群 → `tool-access`
  - Phase/Gate/审查/流程 → `project-management`
  - settings/claude.md/hook → `claude-workflow`
- 写入 `~/.claude/lesson-memo/lessons/`，更新 registry.json

## Step 2: /plan-review:recall — 智能召回

**触发：** 用户输入 `/plan-review:recall "任务描述"`

```bash
python3 ~/.claude/skills/plan-review-companion/scripts/recall.py --query "任务描述" --top 5
```

## Step 3: /plan-review:list — 列出所有教训

```bash
python3 -c "
import json; from pathlib import Path
reg = json.loads(Path('~/.claude/lesson-memo/registry.json').expanduser().read_text())
for l in reg.get('lessons', []):
    print(f'[{l.get(\"confidence\", 0):.2f}] {l[\"id\"]} | domain={l.get(\"domain\",\"?\")}')
print(f'Total: {len(reg.get(\"lessons\", []))} lessons')
"
```

## Step 4: /plan-review:status — 知识库统计

```bash
python3 -c "
import json; from pathlib import Path; from collections import Counter
reg = json.loads(Path('~/.claude/lesson-memo/registry.json').expanduser().read_text())
lessons = reg.get('lessons', [])
print(f'Total: {len(lessons)}')
print(f'Domains: {Counter(l.get(\"domain\",\"?\") for l in lessons)}')
"
```

## Step 5: 自动注入（配合 /plan-review:init）

当 `/plan-review:init` 完成创建 review 骨架后，自动运行 recall 脚本，将结果作为"历史教训参考"章节追加到刚创建的 review 文档中。

---

## 自动触发

1. **Session 结束时（Stop hook）：** 自动运行 session_extract.py，对比 review 文档找出新增教训并入库
2. **/plan-review:init 完成后：** 自动运行 recall 脚本，检索相关教训并注入 review 文档

## Confidence 演化

| 事件 | confidence 变化 |
|------|----------------|
| 新教训入库（extract） | 初始 0.7 |
| 新教训入库（Stop hook） | 初始 0.5 |
| 被成功引用（用户未反驳） | +0.05 |
| 被用户明确标记为不适用 | -0.15 |
| 30 天未被引用 | -0.05 |
| 90 天未被引用 | -0.15 → 可能 dormant |
| confidence ≥ 0.9 | core（每次 init 必注入） |

## 目录结构

```
~/.claude/lesson-memo/
├── lessons/           # 每条教训一个 YAML 文件
├── registry.json      # 索引
├── config.json        # 阈值配置
└── .last_session_state.json  # Stop hook 快照（自动生成）
```
