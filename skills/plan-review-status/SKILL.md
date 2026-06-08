---
name: plan-review:status
description: Use when viewing knowledge base statistics of the lesson-memo system. Trigger: "/plan-review:status".
---

# /plan-review:status — 知识库统计

查看错题本知识库的统计信息。

## 命令

```bash
python3 -c "
import json; from pathlib import Path; from collections import Counter
reg = json.loads(Path('~/.claude/lesson-memo/registry.json').expanduser().read_text())
lessons = reg.get('lessons', [])
domains = Counter(l.get('domain','?') for l in lessons)
confs = Counter(round(l.get('confidence',0), 1) for l in lessons)
print(f'Total lessons: {len(lessons)}')
print(f'Domains: {dict(domains)}')
print(f'Confidence distribution: {dict(confs)}')
core = sum(1 for l in lessons if l.get('confidence',0) >= 0.9)
dormant = sum(1 for l in lessons if l.get('confidence',0) < 0.3)
print(f'Core (>=0.9): {core}')
print(f'Dormant (<0.3): {dormant}')
"
```

## 输出

包含总条数、domain 分布、confidence 分布、core 和 dormant 教训数量。
