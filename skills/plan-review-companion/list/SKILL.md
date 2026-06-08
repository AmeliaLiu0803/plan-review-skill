---
name: plan-review:list
description: Use when listing all stored lessons in the lesson-memo knowledge base. Trigger: "/plan-review:list".
---

# /plan-review:list — 列出所有教训

列出错题本知识库中的所有已存储教训。

## 命令

```bash
python3 -c "
import json; from pathlib import Path
reg = json.loads(Path('~/.claude/lesson-memo/registry.json').expanduser().read_text())
for l in reg.get('lessons', []):
    print(f'[{l.get(\"confidence\", 0):.2f}] {l[\"id\"]} | domain={l.get(\"domain\",\"?\")} | {l.get(\"title\",\"?\")[:60]}')
print(f'Total: {len(reg.get(\"lessons\", []))} lessons')
"
```

## 输出

按信心值排序显示所有教训，包含 id、domain 和标题。
