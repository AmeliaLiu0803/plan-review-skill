---
name: plan-review:init
description: Use when creating a new session review document that compares planned vs. actual execution. Trigger when: user says "/plan-review:init", "/review:init", "创建回顾", "session review", "建立 review", "plan执行回顾", or when a new plan has been created and a corresponding review file is needed. Also triggers when user wants to start tracking execution against a plan.
---

# Review Init

创建一个新的回顾文档，对照 plan 的预期和实际执行情况。

## STRICT EXECUTION CHECKLIST

1. **Run the init script** (Step 1)
2. **Show the result** (Step 2)
3. **Confirm with user** (Step 3)

**不得跳过任何步骤。**

---

## Step 1: Run Init Script

```bash
python ~/.claude/skills/plan-review-init/scripts/init_review.py [plan-filename]
```

- `<plan-filename>` 是 `~/.claude/plans/` 下的文件名（不含路径）。
- 如果不带参数，脚本自动扫描 `~/.claude/plans/` 中**还没有对应 review** 的所有 plan，为每个生成 review 骨架。

脚本行为：
- 读取 plan 文件，提取各 Phase/Task 的预期内容、时间规划、deliverable
- 在 `~/.claude/reviews/` 下创建同名 review 文件：
  - plan 文件名含 `plan` → 替换为 `review`（如 `xxx-plan.md` → `xxx-review.md`）
  - 不含 `plan` → 在扩展名前加 `-review`（如 `xxx.md` → `xxx-review.md`）
- 预填以下内容：
  - 计划时间 vs 实际时间（实际时间初始为 "未开始"）
  - 预期任务列表（从 plan 提取）vs 实际执行（初始为 "待填写"）
  - 教训总结区域（初始为空）
  - 待确认问题（从 plan 中的 `[待核实]` 标记提取）
- 在 `~/.claude/plans/` 下建立 plan 的 **baseline 快照**（用于后续 diff 对比）：
  - 复制 plan 原文件到 `~/.claude/plans/.baselines/<plan-filename>.<timestamp>.md`
  - 记录 baseline 路径到 review 的"更新日志"中

## Step 2: Show the Result

告知用户：
- 创建了哪些 review 文件
- 文件路径
- 哪些信息已预填，哪些需要手动补充
- baseline 快照已保存

## Step 3: Confirm

询问用户是否需要调整 review 模板内容（如增加特定关注点、调整结构等）。

---

## 规划变更追踪

当 plan 文件被修改时，必须记录变更 diff：

### 如何检测 plan 变更
每次 `/plan-review:update` 触发时，运行：
```bash
diff ~/.claude/plans/.baselines/<plan>.<last-timestamp>.md ~/.claude/plans/<plan>.md
```

### 如何记录 diff
在 review 的更新日志下方追加变更记录：

```markdown
### 规划变更记录

| 时间 | 变更摘要 | diff |
|------|---------|------|
| YYYY-MM-DD HH:MM | Phase 2 时间从 7天→10天 | 见下方 diff 块 |

<details>
<summary>diff: Phase 2 时间调整</summary>

```diff
- ### Phase 2: 3 个 Toy 实验（7 天）
+ ### Phase 2: 3 个 Toy 实验（10 天）
```
</details>
```

### baseline 维护
- 每次 plan 变更后，自动创建新的 baseline 快照
- 保留最近 5 个 baseline（最早的自动清理）
- baseline 路径: `~/.claude/plans/.baselines/<plan-filename>.<YYYYMMDD-HHmm>.md`

---

## Review 文档结构

```markdown
# [Title] Review

## 基本信息
| 项目 | 计划 | 实际 |
|------|------|------|
| 开始日期 | YYYY-MM-DD | |
| 结束日期 | YYYY-MM-DD | |
| 总天数 | N 天 | |
| 当前状态 | | 进行中/已完成/暂停 |

## Phase 回顾

### Phase N: [名称]

| 维度 | 预期 | 实际 | 偏差原因 |
|------|------|------|----------|
| 时间 | X 天 | | |
| Deliverable | | | |
| 质量门槛 | | | |

### 经验教训

- 

### 待确认问题

- [ ] ...

---

## 整体总结

### 做了什么（vs plan）

| 计划事项 | 实际执行 | 偏差 |
|---------|---------|------|

### 犯错教训

1. 

### 下期改进

1. 

---

## 规划变更记录

（当 plan 被修改时，追加 diff 记录）

---

## 更新日志

| 时间 | 变更 | 触发方式 |
|------|------|----------|
```

## 自动触发

- plan 创建后（与 Step 2.A 结合）：每次在 `~/.claude/plans/` 中创建新的 plan 文件后，**自动运行** `/plan-review:init <plan-filename>` 生成对应 review 骨架。
- 用户手动触发 `/plan-review:init`：为指定或所有尚无 review 的 plan 创建回顾。
