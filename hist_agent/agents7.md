# AI任务记忆控制器 v9.0

## 核心原则

1. **确定性原则**
   所有 `.ai/` 文件的状态变更必须通过单一原子入口完成，禁止多步编辑。

2. **接口契约**
   `harness.py` 是唯一的格式化层。AI 只传递原始内容，不控制 frontmatter、缩进、分段等格式细节。

3. **读写分离原则**
   AI 不直接读取 `.ai/` 文件。状态恢复信息由 `task resume` 通过 stdout 交付，AI 解析输出即可。

4. **扩展规则**
   如需新增记忆类型，必须同时修改 `harness.py`（原子操作）和 `harness-agent skill`（AI 行为指令），不得在协议外增加手工步骤。

5. **回滚原则**
   `archive` 操作必须保留带时间戳的原始文件副本，archive 记录不可删除只可追加。

6. **上下文约束**
   snapshot 的 focus/context 仅指向业务代码路径，不内嵌大段代码（snippet ≤ 80 字符）。

## 目录结构

```
.ai/
├── memory-bank/
│   ├── backlog.md       # CLI 维护
│   ├── archive.md       # CLI 维护
│   ├── tech-spec.md     # CLI 维护
│   ├── lessons.md       # CLI 维护
│   └── environment.md   # CLI 维护
├── tasks/
│   ├── {id}.md          # CLI 生成和更新
│   └── archive/         # CLI 归档
└── snapshots/
    ├── {id}.md          # CLI 生成和更新
    └── archive/         # CLI 归档
```

## 与 Skill 的关系

`agents7.md` 定义架构与约束。
**具体操作指令见 `skills/harness-agent/SKILL.md`。**
