# Harness Agent

一套用于 AI 编程助手的任务记忆与状态恢复协议，解决大模型在会话重启后需要大量重新读取文件、恢复上下文的问题。

## 目录结构

```
.
├── skills/
│   └── harness-agent/   # AI 任务记忆控制器 skill
│       ├── SKILL.md     # AI 行为指令
│       └── harness.py   # 原子化 CLI 入口
├── hist_agent/          # 协议文档
│   ├── agents1.md ~ agents6.md   # 历史迭代版本
│   └── agents7.md                # 当前最新版本（v9.0）
├── sessions/            # 历史会话记录
└── LICENSE
```

## 核心设计

最新版本 `agents7.md` 引入了**原子化 CLI 操作层**：

- **唯一入口**：harness-agent skill 是 AI 操作 `.ai/` 记忆库的唯一方式，其底层通过原子化 CLI 完成所有文件变更
- **禁止直接文件操作**：AI 不得使用 `Read/Edit/Write` 直接修改 `.ai/` 下任何文件
- **任务快照隔离**：每个任务拥有独立的 `.ai/snapshots/{task_id}.md`
- **快速状态恢复**：`task resume` 输出结构化信息，主Agent按需恢复上下文
- **确定性操作**：新建、继续、归档、检查点全部原子化，彻底消除文件遗漏

## 快速开始

1. 将 harness-agent skill 安装到你的 OpenCode 全局 skill 路径
2. 初始化记忆库：从 skill 目录执行 `python harness.py init`
3. 将 harness-agent skill 注入你的 AI 系统提示
4. 所有任务操作由 AI 自动调用 harness-agent skill 完成

## 设计理念

- **人机边界清晰**：`agents7.md` 是机器遵守的架构约束，`SKILL.md` 是机器执行的操作指令，而 README 是人类理解系统的入口。操作细节归 skill，设计理念归文档，协议归规则，三者职责不重叠。
- **原子化操作**：通过 `harness.py` CLI 消除 AI 在多步文件编辑中的遗漏风险。
- **状态按需恢复**：不预加载整个代码库，而是通过快照中的精确定位快速恢复上下文。

## 协议演进

| 版本 | 文件 | 核心特性 |
|------|------|----------|
| v1.0 | `agents1.md` | 基础任务记录 |
| v2.0 | `agents2.md` | 引入 backlog 概念 |
| v3.0 | `agents3.md` | 增加环境模板 |
| v4.0 | `agents4.md` | 引入子 agent 分工 |
| v5.0 | `agents5.md` | 增加自动记忆捕获 |
| v8.0 | `agents6.md` | 任务快照隔离、快速状态恢复 |
| **v9.0** | **`agents7.md`** | **原子化 CLI、skill 封装、确定性文件操作** |

## License

[MIT](LICENSE)
