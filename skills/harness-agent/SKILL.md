---
name: harness-agent
description: 在需要通过 harness.py CLI 操作 AI 任务记忆（.ai/ 目录）时使用，确保文件操作原子化、确定性
---

# Harness Agent 操作手册

## 铁律

**严禁** 直接对 `.ai/` 目录下的任何文件使用 `Read/Edit/Write` 工具。
所有与 `.ai/` 的交互，必须通过 `python skills/harness-agent/harness.py` 原子化完成。

## 何时使用

- 新建、继续、归档任务
- 保存任务检查点（checkpoint）
- 记录经验教训、技术决策、环境变更
- 任何意图触碰 `.ai/tasks/`、`.ai/snapshots/` 或 `.ai/memory-bank/` 的场景

## 命令速查

### 初始化（每个项目一次）
```bash
python skills/harness-agent/harness.py init [--project-name "项目名"]
```

### 任务生命周期
```bash
python skills/harness-agent/harness.py task create "任务名" --prefix auth
python skills/harness-agent/harness.py task resume auth-001
python skills/harness-agent/harness.py task archive auth-001
```

### 检查点（同时更新 task + snapshot）
```bash
python skills/harness-agent/harness.py checkpoint auth-001 \
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
python skills/harness-agent/harness.py lesson "Redis连接池需设置超时"
python skills/harness-agent/harness.py tech --title "ADR-001" --content "..."
```

### 环境
```bash
python skills/harness-agent/harness.py env
python skills/harness-agent/harness.py env --key python --value 3.12
```

## 操作流程

### 新建任务
1. 执行 `python skills/harness-agent/harness.py task create "{名称}" --prefix {前缀}`
2. CLI 输出新 ID（如 `auth-001`）
3. 汇报：「已新建 {id}」

### 继续任务
1. 执行 `python skills/harness-agent/harness.py task resume {id}`
2. 解析 stdout：task_name、stage、progress、focus_file、focus_line、focus_function、next_action、blocker、context_count
3. 按需读取业务源码恢复上下文
4. 汇报：「已恢复 {id}，阶段 {stage}，当前在 {focus_file}:{focus_line}，下一步：{next_action}」

### 归档任务
1. 执行 `python skills/harness-agent/harness.py task archive {id}`
2. 汇报：「{id} 已完成归档」

## 自动记忆捕获

| 触发条件 | 操作 |
|---------|------|
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
- AI 不负责 frontmatter 格式，只向 CLI 传原始内容

## 红灯警告

| 想法 | 事实 |
|------|------|
| "我直接看一眼 .ai 文件" | **停。** 用 `resume` 或 `env` 命令。 |
| "手动改 backlog 更快" | **停。** 必须用 `task create` / `archive`。 |
| "就改这一次，不会有问题" | **停。** 所有修改必须走 CLI，原子化执行。 |
