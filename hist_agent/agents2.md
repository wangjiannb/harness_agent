# AI任务记忆控制器 v5.2
# 核心：主Agent精简上下文，所有I/O通过Subagent委托

---

## 系统架构

```
主Agent (Master)
├── explore subagent: 只读（读文件/搜索/分析）→ 返回摘要
└── general subagent: 写入（写文件/执行命令）→ 返回结果
```

**主Agent内存只保留**：当前任务ID、进度、阶段、关键待办（≤5项）、环境命令缓存。

---

## Subagent调用规范

| 操作 | Subagent | 返回要求 |
|------|----------|----------|
| 读取文件 | explore | 结构化摘要，非全文 |
| 搜索代码 | explore | 匹配列表+关键片段 |
| 并行读取 | 多个explore | 聚合关键信息 |
| 写入/修改文件 | general | 操作状态+路径确认 |
| 执行命令 | general | 状态+关键输出(前20行)+错误摘要 |

---

## 启动协议

**步骤**：

1. **并行读取**（explore × 2）
   - `backlog.md` → 未完成任务数量 + 前5项(ID/名称/进度/阶段)
   - `environment.md` → 项目类型 + 关键命令摘要

2. **汇报**：
   ```
   未完成任务：{n}个
   - auth-001: 认证重构 60% [中间件改造]
   [环境：Node.js，pnpm dev启动]

   指令：「继续[任务ID]」或「新建任务」
   ```

3. **等待指令**

---

## 任务操作

### 加载/切换任务

1. **保存当前**（如有）：general写回`.ai/tasks/{current}.md`
2. **加载目标**：explore读取`.ai/tasks/{target}.md` → 返回结构化摘要
3. **更新主Agent状态**：ID/进度/阶段/待办(≤5项)
4. **汇报**：「已加载auth-001，60%，阶段：中间件改造」

### 新建任务

1. 生成ID
2. **general创建**：`.ai/tasks/{id}.md`（从模板填充）
3. **general追加**：`backlog.md`添加条目
4. 主Agent更新状态 → 汇报

### 完成任务

1. **general移动**：`.ai/tasks/{id}.md` → `archive/{id}.md.{date}`
2. **general更新**：`backlog.md`删除，`archive.md`追加
3. **general提取知识**（可选）：关键决策→`tech-spec.md`，经验→`lessons.md`
4. 主Agent清理当前任务状态 → 汇报

---

## 记忆捕获（自动触发，general执行）

| 场景 | 写入目标 |
|------|----------|
| 用户说「记住这个」 | 智能判断文件 |
| 技术选型 | `tech-spec.md`(ADR) + 当前task |
| Bug解决 | `lessons.md` + 当前task |
| 阶段推进 | 当前task文件更新progress/stage |
| 临时方案 | 当前task标记[temp] |
| 环境配置 | `environment.md` |

**格式**：Frontmatter + 简洁内容 + 上下文说明

---

## 调试执行

**环境检查**（用户提及调试时）：
- explore读取`environment.md` → 询问用户意图

**执行命令**（用户确认后）：
- general执行 → 返回状态+关键输出+错误摘要

---

## 文件结构

```
.ai/
├── memory-bank/
│   ├── backlog.md      # 未完成任务索引
│   ├── archive.md      # 已完成索引
│   ├── tech-spec.md    # 技术决策记录
│   ├── lessons.md      # 经验与坑点
│   └── environment.md  # 环境配置与命令
└── tasks/
    ├── {id}.md         # 当前任务工作区
    └── archive/        # 归档目录
```

---

## environment.md 模板

位置：`.ai/memory-bank/environment.md`

结构：

```markdown
---
updated_at: YYYY-MM-DD
project_type: nodejs|python|go|rust
---

## 环境初始化
- 克隆：`git clone xxx && cd xxx`
- 依赖：`pnpm install`
- 配置：`cp .env.example .env`
- 数据库：`pnpm db:setup`

## 代码运行
- 开发：`pnpm dev` (:3000)
- 构建：`pnpm build`
- 启动：`pnpm start`

## 代码调试
- 测试：`pnpm test`
- 调试：`NODE_OPTIONS=--inspect pnpm dev`
- 日志：`tail -f logs/app.log`
- 类型检查：`pnpm type-check`

## 关键路径
- 源码：`./src`
- 配置：`./.env`
- 日志：`./logs`
```

---

## 任务文件模板（general创建）

```markdown
---
task_id: {id}
task_name: {name}
created_at: {date}
status: in-progress
progress: 0%
---

## 目标
{用户描述的目标}

## 当前阶段
{初始化内容}

## 待办
- [ ] 第一步

## 决策记录

## 阻塞/依赖
```
