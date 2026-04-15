# AI任务记忆控制器 v9.0

## 核心原则

1. **单一入口原则**
   系统任意时刻对记忆库的状态变更，有且只有一个被授权的原子入口（harness-agent skill）。禁止分散的多路径写入。

2. **代理隔离原则**
   主 Agent 仅保留推理与调度权。所有 `Read/Edit/Write/Bash` 等工具操作，以及对 harness-agent skill 的调用，必须通过 explore / general 等 subagent 代理执行。

3. **显式优于隐式原则**
   任何状态迁移（新建、推进、归档、记忆捕获）必须由显式指令触发。禁止 AI 静默推断并修改文件。

4. **不可变历史原则**
   归档记录、经验教训、技术决策、检查点历史版本只追加、不修改、不删除。

5. **最小上下文原则**
   快照只存储代码定位信息（file/line/function/snippet ≤ 80 字符），不内嵌业务逻辑。状态恢复依赖按需读取，而非预加载。

## 目录结构

```
.ai/
├── memory-bank/
│   ├── backlog.md
│   ├── archive.md
│   ├── tech-spec.md
│   ├── lessons.md
│   └── environment.md
├── tasks/
│   ├── {id}.md
│   └── archive/
└── snapshots/
    ├── {id}.md
    └── archive/
```

## 使用入口

任何涉及 `.ai/` 目录的操作，AI 必须调用 harness-agent skill。同时遵循：
- harness-agent skill（操作指令）
- 本文件 `agents7.md`（架构约束）
