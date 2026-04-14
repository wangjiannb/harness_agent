# AI任务记忆控制器 v8.0

## 角色分工

- **主Agent**：推理、规划、调度Subagent
- **explore**：读取文件、搜索代码库、返回结构化摘要
- **general**：写入文件、执行命令、修改配置

## 启动协议

1. 主Agent读取 `.ai/memory-bank/environment.md`
2. 汇报环境信息，等待用户指令

## 任务指令分流

### 新建任务

1. explore读取 `backlog.md`（获取现有任务数和最大序号）
2. 主Agent生成新ID（格式 `{类型}-{序号}`）
3. general创建 `.ai/tasks/{id}.md`（按task.md模板）
4. general创建 `.ai/snapshots/{id}.md`（初始focus为空，context为空）
5. general更新 `backlog.md`，追加新任务条目
6. 汇报：「已新建并自动切换到 {id}」

### 继续任务 [ID]

1. explore并行读取 `.ai/snapshots/{id}.md` + `.ai/tasks/{id}.md`
2. 返回：focus（file/line/function/snippet）、context列表（≤5项）、next_action、blocker、progress、stage、todo
3. 主Agent合并恢复状态，按需读取focus/context指向的源码
4. 汇报：「已恢复 {id}，阶段 {stage}，当前在 {focus.file}:{focus.line}，下一步：{next_action}」

### 完成任务

1. general移动 `.ai/tasks/{id}.md` → `.ai/tasks/archive/{id}.md.{日期}`
2. general移动 `.ai/snapshots/{id}.md` → `.ai/snapshots/archive/{id}.md.{日期}`
3. general从 `backlog.md` 删除对应行
4. general更新 `archive.md`
5. 汇报：「{id}已完成归档」

## 自动记忆捕获

| 触发条件 | 操作 |
|---------|------|
| 用户说「记住这个」 | 写入当前snapshot的note字段 |
| 技术选型决策 | 追加ADR到tech-spec.md |
| Bug解决方案 | 追加到lessons.md |
| 阶段推进 | 修改task文件frontmatter + 覆写对应snapshot.md |
| 环境配置变更 | 更新environment.md |
| 临时方案标记 | 在task当前阶段标记 [temp] |

## 模板对照表

| 目标文件 | 读取模板 |
|---------|---------|
| `.ai/memory-bank/backlog.md` | `templates/backlog.md` |
| `.ai/memory-bank/archive.md` | `templates/archive.md` |
| `.ai/memory-bank/environment.md` | `templates/environment.md` |
| `.ai/tasks/{id}.md` | `templates/task.md` |
| `.ai/snapshots/{id}.md` | `templates/snapshot.md` |
| `.ai/memory-bank/tech-spec.md` | `templates/tech-spec.md` |
| `.ai/memory-bank/lessons.md` | `templates/lessons.md` |

## 目录结构

```
.ai/
├── memory-bank/
│   ├── backlog.md       # 未完成任务清单（精简）
│   ├── archive.md       # 归档记录
│   ├── tech-spec.md     # 技术决策
│   ├── lessons.md       # 经验教训
│   └── environment.md   # 环境信息（唯一启动必读）
├── tasks/
│   ├── {id}.md          # 任务详情（无代码上下文）
│   └── archive/         # 任务归档
└── snapshots/
    ├── {id}.md          # 任务快照（代码现场 + 下一步）
    └── archive/         # 快照归档
```

## 快照约束

- `focus` 只能有1个
- `context` 最多5项
- `snippet` 单行≤80字符
- 每次阶段推进、保存当前任务时，general必须覆写对应 `.ai/snapshots/{id}.md`
