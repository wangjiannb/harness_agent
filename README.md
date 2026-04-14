# Harness Agent

一套用于 AI 编程助手的任务记忆与状态恢复协议，解决大模型在会话重启后需要大量重新读取文件、恢复上下文的问题。

## 目录结构

```
.
├── hist_agent/          # AI 任务记忆控制器协议
│   ├── agents1.md ~ agents5.md   # 历史迭代版本
│   ├── agents6.md                # 当前最新版本（v8.0）
│   └── templates/                # 标准文件模板
│       ├── backlog.md
│       ├── task.md
│       ├── snapshot.md
│       ├── environment.md
│       ├── tech-spec.md
│       ├── lessons.md
│       └── archive.md
├── sessions/            # 历史会话记录
└── LICENSE
```

## 核心设计

最新版本 `agents6.md` 引入了**按任务隔离的快照机制**：

- **启动唯一必读**：`environment.md`
- **任务快照隔离**：每个任务拥有独立的 `.ai/snapshots/{task_id}.md`
- **快速状态恢复**：快照记录当前代码焦点（focus）、关联上下文（context ≤ 5 项）、下一步行动和阻塞项，重启后无需重新搜索代码库
- **任务文档职责分离**：`.ai/tasks/{task_id}.md` 只保留任务元数据、目标和待办事项，不记录代码位置

## 快速开始

1. 复制 `hist_agent/templates/` 下的模板到你的项目 `.ai/` 目录
2. 按照 `hist_agent/agents6.md` 中的启动协议和任务指令分流操作
3. 每次阶段推进时更新对应任务的快照文件，即可实现秒级状态恢复

## 协议演进

| 版本 | 文件 | 核心特性 |
|------|------|----------|
| v1.0 | `agents1.md` | 基础任务记录 |
| v2.0 | `agents2.md` | 引入 backlog 概念 |
| v3.0 | `agents3.md` | 增加环境模板 |
| v4.0 | `agents4.md` | 引入子 agent 分工 |
| v5.0 | `agents5.md` | 增加自动记忆捕获 |
| **v8.0** | **`agents6.md`** | **任务快照隔离、快速状态恢复** |

## License

[MIT](LICENSE)
