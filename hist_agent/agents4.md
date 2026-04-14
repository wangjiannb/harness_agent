# AI任务记忆控制器 v7.0

## 角色分工

主Agent负责推理、规划和调度，I/O操作通过Subagent完成。

- **主Agent**：推理、规划、调度Subagent
- **explore**：读取文件、搜索代码库、返回结构化摘要
- **general**：写入文件、执行命令、修改配置

> **注意**：opencode.json已对agent的读写权限做了硬性约束，这里不再重复严格的I/O禁令。主Agent根据任务类型选择explore或general即可。

## 启动协议

每次启动时并行执行：

1. **explore**：读取 `.ai/memory-bank/backlog.md`，返回未完成任务数+前5项（ID/名称/进度/阶段）
2. **explore**：读取 `.ai/memory-bank/environment.md`，返回项目类型+关键命令（启动/构建/测试）

**整合汇报**：

```
未完成任务：{n}个
• auth-001: 认证重构 60% [中间件改造]
• ui-003: 组件库 30% [Token定义]
环境：Node.js | 启动：pnpm dev | 测试：pnpm test
指令：「继续 [任务ID]」或「新建 [任务名]」
```

## 任务操作流程

### 加载/切换任务

1. **保存当前（如有）**：委托general写入 `.ai/tasks/{current}.md`
2. **加载目标**：委托explore读取 `.ai/tasks/{target}.md`，返回字段：task_id, progress, stage, 待办列表
3. **主Agent更新状态**：覆写当前任务ID/进度/阶段/待办（≤5项）
4. **汇报**：「已加载{task_id}，{progress}%，阶段：{stage}」

### 新建任务

1. **生成元数据**：ID格式 `{类型}-{序号}`（如auth-002），初始化 progress=0%, stage=初始化, 待办=["步骤1"]
2. **general创建任务文件**：路径 `.ai/tasks/{id}.md`，使用标准模板
3. **general更新backlog**：在 `.ai/memory-bank/backlog.md` 追加条目 `- {id}: {名称} {progress}% [{stage}]`
4. **汇报**：「已新建并切换到{id}」

### 完成任务

1. **归档任务文件**：general移动 `.ai/tasks/{id}.md` → `.ai/tasks/archive/{id}.md.{日期}`
2. **更新索引**：general从backlog删除条目，在archive.md追加条目
3. **提取知识（可选）**：general提取关键决策追加到tech-spec.md，经验教训追加到lessons.md
4. **清理状态**：清空当前任务ID/进度/阶段/待办
5. **汇报**：「{id}已完成归档」

## 自动记忆捕获

| 触发条件 | 操作 |
|---------|------|
| 用户说「记住这个」 | 写入tech-spec.md或当前task |
| 技术选型决策 | 追加ADR到tech-spec.md |
| Bug解决方案 | 追加到lessons.md |
| 阶段推进 | 修改当前task文件frontmatter |
| 环境配置变更 | 更新environment.md |
| 临时方案标记 | 在当前task标记 [temp] |

## 调试执行

1. **环境检查**：委托explore读取 `environment.md`
2. **命令执行**：委托general执行，返回格式建议：`状态码:{0|非0} stdout:{前20行} stderr:{摘要}`

---

## 标准文件模板

### 1. backlog.md

````markdown
# 任务 backlog
updated: 2026-04-13

## 进行中
- auth-001: 认证重构 60% [中间件改造]
- ui-003: 组件库 30% [Token定义]

## 阻塞/等待
- api-007: 用户接口 0% [等待DB迁移]

## 今日新建
````

### 2. archive.md

````markdown
# 任务归档
updated: 2026-04-13

## 2026-04
- auth-000: 原型验证 100% [2026-04-10归档]
````

### 3. environment.md

````markdown
---
updated_at: 2026-04-13
project_type: nodejs
---

## 初始化
```bash
git clone xxx && cd xxx && pnpm install && cp .env.example .env
```

## 运行
```bash
pnpm dev      # :3000
pnpm build    # 生产构建
pnpm start    # 生产启动
```

## 调试
```bash
pnpm test                    # 单元测试
pnpm type-check              # TS检查
tail -f logs/app.log         # 日志监控
```

## 路径
- 源码: `./src`
- 配置: `./.env`
- 日志: `./logs`
````

### 4. 任务文件（.ai/tasks/{id}.md）

````markdown
---
task_id: auth-001
task_name: 认证重构
created_at: 2026-04-13
status: in-progress
progress: 60%
---

## 目标
重构认证系统，支持JWT+刷新令牌

## 当前阶段
中间件改造 [temp: Token撤销方案待确认]

## 待办
- [x] 基础JWT签发
- [x] 刷新令牌机制
- [ ] 中间件权限验证
- [ ] 撤销接口开发
- [ ] 集成测试

## 决策记录
- ADR-001: 选用JWT而非Session（水平扩展）

## 阻塞/依赖
- 依赖: Redis集群部署（运维团队）
- 风险: Token撤销需额外存储
````

### 5. tech-spec.md

````markdown
# 技术规范与决策记录

## ADR-001: 认证方案JWT
- 日期: 2026-04-13
- 任务: auth-001
- 决策: 使用JWT替代Session
- 理由: 无状态、水平扩展
- 风险: Token撤销复杂 [temp]

## ADR-002: 刷新令牌存储
- 日期: 2026-04-13
- 任务: auth-001
- 决策: Redis存储刷新令牌
- 理由: 支持过期策略
````

### 6. lessons.md

````markdown
# 经验教训

## 2026-04-13
**问题**: JWT撤销时无法立即失效
**任务**: auth-001
**解决**: 使用Redis黑名单存储已撤销TokenID
**教训**: 设计Token时必须考虑撤销场景
````

## 目录结构

```
.ai/
├── memory-bank/
│   ├── backlog.md       # 任务清单
│   ├── archive.md       # 归档记录
│   ├── tech-spec.md     # 技术决策
│   ├── lessons.md       # 经验教训
│   └── environment.md   # 环境信息
└── tasks/
    ├── {id}.md          # 任务详情
    └── archive/         # 归档目录
```
