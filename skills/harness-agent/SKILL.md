---
name: harness-agent
description: 在需要通过 harness.py CLI 操作 AI 任务记忆（.ai/ 目录）时使用，确保文件操作原子化、确定性
---

# Harness Agent 操作手册

当你看到或即将执行任何涉及 `.ai/` 目录、任务创建/恢复/归档/检查点的操作时，必须完整阅读并执行本 skill 的每一条指令。同时遵守 `agents7.md` 中的架构约束。

## 铁律

- **严禁** 主 Agent 直接执行任何 `Read/Edit/Write/Bash` 工具。
- **严禁** 任何 agent 直接触碰 `.ai/` 目录下的文件。
- 所有 `.ai/` 交互和 harness-agent skill 调用，必须通过本 skill 规定的 subagent 分工完成。

## 角色分工

- **主Agent**：负责理解用户意图、推理决策、调度 subagent。不直接执行任何工具。
- **explore subagent**：负责读取业务代码、搜索代码库、返回结构化摘要。
- **general subagent**：负责执行 `Bash`（包括所有 harness-agent skill CLI 命令）、`Edit`、`Write`。

## 命令速查

### 初始化（每个项目一次）
```bash
python harness.py init [--project-name "项目名"]
```

### 任务生命周期
```bash
python harness.py task create "任务名" --prefix auth
python harness.py task resume auth-001
python harness.py task archive auth-001
```

### 检查点（同时更新 task + snapshot）
```bash
python harness.py checkpoint auth-001 \
  --stage "中间件改造" \
  --progress 60 \
  --todo "第一行\n第二行" \
  --file src/auth/middleware.ts \
  --line 45 \
  --function verifyToken \
  --snippet "const payload = jwt.verify(token, secret)" \
  --next-action "修复 TS 类型报错" \
  --blocker "等待 Redis 部署" \
  --note "用户要求记住这个" \
  --context "src/auth/service.ts|120-135|callee|被 verifyToken 调用"
```

### 知识库
```bash
python harness.py lesson "Redis连接池需设置超时"
python harness.py tech --title "ADR-001" --content "..."
```

### 环境
```bash
python harness.py env
python harness.py env --key python --value 3.12
```

## 操作流程

### 新建任务
1. 主Agent 调度 general subagent 执行：
   ```bash
   python harness.py task create "{名称}" --prefix {前缀}
   ```
2. general subagent 将 CLI 输出的新 ID（如 `auth-001`）返回给主Agent
3. 主Agent 汇报：「已新建 {id}」

### 继续任务
1. 主Agent 调度 general subagent 执行：
   ```bash
   python harness.py task resume {id}
   ```
2. general subagent 解析 stdout，将以下字段返回给主Agent：
   task_name、stage、progress、focus_file、focus_line、focus_function、next_action、blocker、context_count
3. 主Agent 根据 focus/context 信息，调度 explore subagent 读取相关源码
4. 主Agent 汇报：「已恢复 {id}，阶段 {stage}，当前在 {focus_file}:{focus_line}，下一步：{next_action}」

### 归档任务
1. 主Agent 调度 general subagent 执行：
   ```bash
   python harness.py task archive {id}
   ```
2. general subagent 确认 CLI 执行成功
3. 主Agent 汇报：「{id} 已完成归档」

## 自动记忆捕获

| 触发条件 | general subagent 操作 |
|---------|----------------------|
| 用户说「记住这个」 | `checkpoint {id} --note "..."` |
| 技术选型决策 | `tech --title "ADR-xxx" --content "..."` |
| Bug 解决方案 | `lesson "..."` |
| 阶段推进 | `checkpoint {id} --stage "..." --progress xx` |
| 环境配置变更 | `env --key xxx --value yyy` |
| 临时方案标记 | `checkpoint {id} --stage "... [temp]"` |

## 约束

- `focus` 只能有 1 个
- `context` 最多 5 项
- `snippet` 单行 ≤ 80 字符
- explore / general subagent 不负责 frontmatter 格式，只向 CLI 传原始内容

## 红灯警告

| 想法 | 事实 |
|------|------|
| "我直接执行 Bash/Read/Edit" | **停。** 主Agent 必须调度 explore 或 general subagent。 |
| "我直接看一眼 .ai 文件" | **停。** 调度 general subagent 执行 `resume` 或 `env`。 |
| "手动改 backlog 更快" | **停。** 必须调度 general subagent 执行 `task create` / `archive`。 |
| "就改这一次，不会有问题" | **停。** 所有修改必须走 CLI，原子化执行。 |
