---
name: lesson-memo
description: Use when managing the lesson-memo (错题本) system. Trigger when: user says "/lesson-memo:extract", "/lesson-memo:recall", "/lesson-memo:list", "/lesson-memo:status", or when /plan-review:init completes and historical lessons should be injected. Also triggers automatically at session end via Stop hook.
---

# Lesson Memo — 错题本系统

自动从历史 review 和 memory 中提取教训，在每次规划/执行时智能检索并注入相关教训，降低重复犯错概率。

## STRICT EXECUTION CHECKLIST

1. **Run the requested command** (Step 1-4)
2. **Show the result** (Step 5)

**不得跳过任何步骤。**

---

## Step 1: /lesson-memo:extract — 历史教训提取

**触发：** 用户输入 `/lesson-memo:extract`

\`\`\`bash
python3 ~/.claude/skills/plan-review-companion/scripts/extract.py
\`\`\`

行为：
- 扫描 \`~/.claude/reviews/*.md\` 提取「犯错教训」和「下期改进」章节
- 扫描 memory files (type=feedback)
- 每条教训生成 YAML 文件（id, title, domain, trigger, lesson, action, evidence, confidence=0.7）
- domain 启发式映射关键词：
  - 手写/clone/官方/复现 → \`research-reproduction\`
  - 依赖/接口/源码/分析 → \`dependency-analysis\`
  - WSL/兼容/平台/路径 → \`cross-platform\`
  - Codex/SSH/权限/集群 → \`tool-access\`
  - Phase/Gate/审查/流程 → \`project-management\`
  - settings/claude.md/hook → \`claude-workflow\`
- 写入 \`~/.claude/lesson-memo/lessons/\`，更新 registry.json

## Step 2: /lesson-memo:recall — 智能召回

**触发：** 用户输入 \`/lesson-memo:recall "任务描述"\`

\`\`\`bash
python3 ~/.claude/skills/plan-review-companion/scripts/recall.py --query "任务描述" --top 5
\`\`\`

## Step 3: /lesson-memo:list — 列出所有教训

\`\`\`bash
python3 -c "
import json; from pathlib import Path
reg = json.loads(Path('~/.claude/lesson-memo/registry.json').expanduser().read_text())
for l in reg.get('lessons', []):
    print(f'[{l.get(chr(99)+\"onfidence\", 0):.2f}] {l[\"id\"]} | domain={l.get(\"domain\",\"?\")}')
print(f'Total: {len(reg.get(\"lessons\", []))} lessons')
"
\`\`\`

## Step 4: /lesson-memo:status — 知识库统计

\`\`\`bash
python3 -c "
import json; from pathlib import Path; from collections import Counter
reg = json.loads(Path('~/.claude/lesson-memo/registry.json').expanduser().read_text())
lessons = reg.get('lessons', [])
print(f'Total: {len(lessons)}')
print(f'Domains: {Counter(l.get(\"domain\",\"?\") for l in lessons)}')
"
\`\`\`

## Step 5: 自动注入（配合 /plan-review:init）

当 \`/plan-review:init\` 完成后，自动运行 recall 脚本，将结果作为"历史教训参考"章节追加到 review 文档。

---

## 自动触发

1. **Session 结束时（Stop hook）：** 自动运行 session_extract.py
2. **/plan-review:init 完成后：** 自动运行 recall 脚本注入相关教训

## Confidence 演化

| 事件 | confidence 变化 |
|------|----------------|
| 新教训入库（extract） | 初始 0.7 |
| 新教训入库（Stop hook） | 初始 0.5 |
| 被成功引用 | +0.05 |
| 用户标记不适用 | -0.15 |
| 30 天未引用 | -0.05 |
| >= 0.9 | core（每次必注入） |

## 目录结构

\`\`\`
~/.claude/lesson-memo/
├── lessons/           # 每条教训一个 YAML 文件
├── registry.json      # 索引
├── config.json        # 阈值配置
└── .last_session_state.json  # Stop hook 快照
\`\`\`
