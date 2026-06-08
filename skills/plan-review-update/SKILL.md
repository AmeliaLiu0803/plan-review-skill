---
name: plan-review:update
description: Use when updating an existing review document with latest execution progress. Trigger when: user says "/plan-review:update", "/review:update", "更新回顾", "update review", "同步review", "review更新", or after a Phase completes, at session end, or when plan execution has progressed and the review needs syncing. Also trigger when plan file has been modified — detect diff and record it.
---

# Review Update

更新已有的回顾文档，将实际执行进展同步到 review 文件中。

## STRICT EXECUTION CHECKLIST

1. **Locate the review** (Step 1)
2. **Check for plan diff** (Step 2) — 如果 plan 被修改，记录 diff
3. **Gather execution data** (Step 3)
4. **Update the review** (Step 4)
5. **Report changes** (Step 5)

**不得跳过任何步骤。**

---

## Step 1: Locate the Review

找到要更新的 review 文件：
- 如果用户指定了 plan 名 → 找到对应的 review 文件
- 如果不指定 → 扫描 `~/.claude/reviews/` 中**状态为"进行中"**的所有 review

## Step 2: Check for Plan Diff

**这一步确保规划变更被完整记录。**

### 2A. 找到最新 baseline
```bash
ls -t ~/.claude/plans/.baselines/<plan-filename>.*.md | head -1
```

### 2B. 计算 diff
```bash
diff -u <latest-baseline> ~/.claude/plans/<plan-filename>
```

### 2C. 如果有变更
- 创建新的 baseline 快照（时间戳命名）
- 在 review 的"规划变更记录"表格中追加一行：

```markdown
| YYYY-MM-DD HH:MM | 变更摘要（一句话） | 见下方 diff |
```

- 在表格下方追加折叠的 diff 块：

```markdown
<details>
<summary>diff: 变更摘要</summary>

```diff
+ 新增行
- 删除行
```
</details>
```

### 2D. 如果没有变更
跳过此步骤，在更新日志中标记"plan 无变更"。

## Step 3: Gather Execution Data

收集以下数据源：

### 3A. Git 提交历史
```bash
git log --oneline --since="YYYY-MM-DD" --no-merges 2>/dev/null
```

### 3B. 文件变更
```bash
find <project-dirs> -name "*.py" -newer <last-update-timestamp> 2>/dev/null
```

### 3C. Memory 记录
```bash
ls -lt ~/.claude/projects/-home-amelialiu/memory/ 2>/dev/null | head -10
```

### 3D. 用户手动输入
询问用户：「自上次更新以来，有什么重要进展或偏差需要记录吗？」

## Step 4: Update the Review

### 4A. 必填更新项（每次更新都必须执行）

1. **实际时间**：根据 git commit 日期和 memory 更新，推算实际起止时间
2. **实际执行**：对比 plan 中的 Task 列表，标记 ✅已完成 / 🔄进行中 / ⬜未开始
3. **偏差原因**：如果有任务跳过、延期、或新增，记录原因
4. **犯错教训**：如果发现了执行过程中的问题或教训，追加到对应 Phase 的"经验教训"和整体"犯错教训"区域

### 4B. 完整更新时额外执行（Phase 完成 / 用户手动触发）

5. **Phase 完成标记**：将对应 Phase 的"实际"列填入完成状态和实际用时
6. **偏差分析**：对比计划 vs 实际的差异，写进偏差原因
7. **教训总结**：根据执行结果，总结可复用的教训

### 更新规则
- **不要覆盖**用户手动填写的内容（如经验教训中的个人总结）
- **追加而非替换**：新的进展追加到现有内容之后
- **标记时间戳**：每次更新在末尾追加 `## 更新日志` 记录更新时间和变更摘要
- 如果 Phase 完成，更新整体进度百分比

## Step 5: Report Changes

告知用户：
- 更新了哪些字段
- Plan 是否有变更（以及变更内容）
- 识别出的偏差（计划 vs 实际不一致的地方）
- 需要用户确认的待确认项

---

## 自动触发时机

以下四种触发方式同时生效（A + B + C 结合 + plan 变更自动触发）：

1. **每次 Session 结束时**：轻量更新 — 仅更新实际时间、完成状态、检查 plan diff
2. **每个 Phase 完成后**：完整更新 — 包含偏差分析、教训总结、plan diff
3. **用户手动触发**：`/plan-review:update [plan-name]` — 完整更新
4. **Plan 文件变更时**：如果检测到 plan 文件被修改，自动触发 diff 记录 + 轻量更新

## 更新日志格式

在 review 文件末尾维护一个更新日志：

```markdown
## 更新日志

| 时间 | 变更 | 触发方式 |
|------|------|----------|
| 2026-06-07 10:00 | 创建初始骨架 | /plan-review:init |
| 2026-06-07 12:00 | Phase 0 完成，更新实际时间 | 自动（Phase 完成） |
| 2026-06-07 15:00 | plan diff: Phase 2 时间 7天→10天 | 自动（Plan 变更） |
```

## 关联技能：错题本系统

更新 review 后，可继续使用 plan-review-companion 沉淀新发现的教训：

| 命令 | 描述 |
|------|------|
| `/plan-review:extract` | 从历史 review 和 memory 中提取教训入库 |
| `/plan-review:recall "任务描述"` | 为当前任务召回相关教训 |
| `/plan-review:list` | 列出所有已存储教训 |
| `/plan-review:status` | 查看知识库统计 |

Session 结束时，Stop hook 自动把 review 中的新教训提取到错题本知识库。
