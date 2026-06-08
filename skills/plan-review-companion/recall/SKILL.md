---
name: plan-review:recall
description: Use when recalling relevant lessons from the lesson-memo knowledge base for a task. Trigger: "/plan-review:recall" with a task description, or automatically after /plan-review:init to inject historical lessons into a new review document.
---

# /plan-review:recall — 智能召回

为当前任务检索错题本知识库中的相关教训。

## 命令

```bash
python3 ~/.claude/skills/plan-review-companion/scripts/recall.py --query "任务描述" --top 5
```

## 行为

1. 接收 query 描述（从 plan 文件名/内容中提取主题，或用户手动输入）
2. 按 domain 标签 + 关键词 + 标题/教训文本匹配检索 registry
3. 按 confidence 降序 + 相关性评分排序，取 Top-N（默认 5）
4. 输出 Markdown 格式教训摘要

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--query` | 任务描述（必需） | — |
| `--top` | 返回条数 | 5 |
| `--min-confidence` | 最低 confidence 阈值 | 0.3 |
| `--lesson-dir` | 覆盖教训目录 | `~/.claude/lesson-memo/lessons` |

## 自动触发

`/plan-review:init` 完成后，自动运行 recall 脚本，检索相关教训并注入到刚创建的 review 文档中。

## 输出格式

```markdown
## 历史教训参考（自动检索自错题本）

1. **[0.70] 教训标题**（来自来源）
   触发条件：触发描述
   教训：教训内容
   行动：行动建议
```
