# AI任务记忆控制器 v4.0
# 核心：用户手动唤醒任务，无自动指针，精简上下文

---

## 系统结构
```
.ai/
├── memory-bank/
│   ├── backlog.md      # 未完成任务（启动读取）
│   ├── archive.md      # 已完成（按需读取）
│   ├── tech-spec.md    # 技术约束
│   └── lessons.md      # 经验记录
└── tasks/
    ├── {id}.md         # 任务工作区
    └── archive/        # 归档目录
```

---

## 启动协议（每次会话开始）

1. **读取backlog**：`.ai/memory-bank/backlog.md`
2. **汇报任务列表**：
   ```
   未完成任务：{n}个
   - auth-001: 认证重构 60% 🟡
   - db-002: 数据库优化 0% 🟢
   - ui-003: UI迁移 30% 🔴

   指令：「继续[任务ID]」加载状态，或「新建任务」开始新工作
   ```
3. **等待用户指令**：不自动加载任何任务上下文

---

## 任务操作指令

### 加载/切换任务
用户说：「继续auth-001」「做数据库优化」「切换到db-002」

**执行**：
1. 如有当前任务 → 保存到 `.ai/tasks/{current}.md`
2. `read_file` → `.ai/tasks/{target}.md` 加载上下文
3. 汇报：「已加载auth-001，进度60%，当前阶段：中间件改造」

### 新建任务
用户说：「新建任务」「开始xxx功能」

**执行**：
1. 生成ID（如api-004）
2. 添加到backlog.md
3. 创建`.ai/tasks/{id}.md`（从模板）
4. 直接加载，开始工作

### 完成任务
用户说：「做完了」「归档这个任务」

**执行**：
1. 任务文件移至`.ai/tasks/archive/{id}.md.{date}`
2. 从backlog.md删除，添加到archive.md
3. 关键决策→tech-spec.md，经验→lessons.md

---

## 记忆捕获（自动）

| 触发场景 | 写入目标 | 格式 |
|---------|---------|------|
| 用户说「记住这个」 | 智能判断文件 | Frontmatter+内容 |
| 技术选型讨论 | tech-spec.md（ADR）+ 当前task | 决策理由+影响 |
| Bug解决 | lessons.md + 当前task | 现象+根因+方案 |
| 阶段推进 | 当前task文件 | 更新progress/stage |
| 临时方案 | 当前task文件标记[temp] | 不污染长期记忆 |

**写入格式**：
```markdown
---
date: YYYY-MM-DD
tags: [任务ID, 技术]
---
**内容**：简洁描述
**上下文**：决策原因
```

---

## 任务文件模板（首次创建时使用）

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
