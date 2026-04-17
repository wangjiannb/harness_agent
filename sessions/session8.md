User: 我创建一个agents.md和skill，用于代码开发的记忆管理，但是实际使用过程中并不令人满意，ai并不会主动调用我的skill，帮我检查原因并给出修改办法。以下是我的agents和skill.md

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
Kimi: 基于你的技术背景和对 **7×24 小时无人工干预开发** 的需求，我诊断出三个核心失效原因：

1. **触发信号太弱**：`description` 描述模糊（"在需要时"），AI 无法识别何时算"需要"
2. **架构假设错误**："subagent 分工"在 Kimi/ChatGPT 等环境中不存在实际执行实体，AI 会困惑"我是谁我在哪我该调用谁"
3. **缺少强制挂钩**：没有将 `.ai/` 目录变更与 skill 调用绑定，AI 看到目录文件不会自动触发

以下是可直接落地的修改方案：

---

## 1. 修正 Skill 元数据（关键）

将文件名改为与 `name` 完全一致（如 `harness-agent.md`），并修改 frontmatter 增强触发概率：

```markdown
---
name: harness-agent
description: |
  当满足以下任一条件时必须调用：
  1. 用户提及 .ai/ 目录、任务记忆、checkpoint、task resume/archive
  2. 检测到 .ai/ 目录下的 backlog.md, tasks/, snapshots/ 等文件变更
  3. 用户说"记住这个"、"归档"、"恢复任务"、"记录技术决策"
  4. 需要执行 python harness.py 相关命令时
  
  绝对禁止：直接读取/修改 .ai/ 目录下任何文件
  必须操作：通过 harness.py CLI 原子化执行所有记忆操作
---
```

---

## 2. 重构操作流程（去除 Subagent 幻觉）

**删除所有 "explore subagent / general subagent" 描述**，改为直接指令集。当前 AI 架构无法创建真正的子代理，描述过于复杂会导致 AI 放弃执行：

```markdown
## 立即执行流程

### 判断逻辑（自检）
在每次回复前自检：
- [ ] 用户是否要求操作 .ai/ 目录？
- [ ] 是否涉及任务创建/恢复/检查点/归档？
- [ ] 是否要将技术决策写入记忆库？
- **任一勾选 → 立即执行下方 CLI 命令，禁止直接编辑文件**

### 新建任务
```bash
python harness.py task create "{名称}" --prefix {前缀}
```
然后汇报：「已新建 {id}，建议立即执行检查点记录当前焦点」

### 继续任务（自动恢复上下文）
```bash
python harness.py task resume {id}
```
解析输出后，**立即**执行：
```bash
cat {focus_file}  # 读取焦点文件
```
然后汇报恢复状态及代码片段

### 检查点捕获（最重要）
当用户说"记住这个"或完成阶段性工作时，**必须**执行：
```bash
python harness.py checkpoint {current_task_id} \
  --stage "{当前阶段}" \
  --progress {0-100} \
  --next-action "{下一步}" \
  --file {当前文件} \
  --line {行号} \
  --snippet "{关键代码片段}"
```

### 知识归档
技术决策 → `python harness.py tech --title "ADR-xxx" --content "..."`
Bug 方案 → `python harness.py lesson "..."`
环境变更 → `python harness.py env --key {k} --value {v}`
```

---

## 3. 修改 agents.md（添加强制触发器）

在文件顶部添加元数据标记，让 AI 识别这是控制系统：

```markdown
---
type: system-prompt
trigger: |
  任何涉及 .ai/ 目录、任务状态、记忆库的操作
  触发动作: 立即加载 harness-agent skill 并执行
enforce: true
---

# AI任务记忆控制器 v9.1

## 强制触发条件（满足任一即调用 harness-agent）

1. **文件检测触发**：检测到 `.ai/` 目录存在或其中文件变更
2. **语义触发**：用户提及 "task"、"checkpoint"、"归档"、"恢复任务"、"记住这个"、"技术决策"
3. **操作意图触发**：用户意图涉及任务生命周期管理或知识沉淀

## 失效防护机制

若无法执行 `python harness.py`，立即报告：
- 检查 harness.py 是否存在于项目根目录
- 确认 Python 环境可用
- **严禁** 因 CLI 不可用而转为直接编辑文件，这是安全红线

## 简化执行模型（去 Subagent）

实际执行时，你（AI）按以下模式操作：
1. **分析**：解析用户意图和当前记忆状态
2. **路由**：判断需要 harness-agent 操作 → 生成对应 CLI 命令
3. **执行**：通过 Bash 工具执行 CLI 命令
4. **反馈**：基于 CLI 输出更新对话上下文
```

---

## 4. 给你的 CLI 工具增强点（工程化建议）

作为关注 **token 效率** 的工程师，建议给 `harness.py` 添加以下接口，降低 AI 调用成本：

```bash
# 添加 query 接口，让 AI 快速判断是否需要激活
python harness.py query --status    # 返回当前活跃任务 ID 或空
python harness.py query --focus     # 返回当前焦点文件/行号
python harness.py smart-checkpoint  # 自动从 git diff + 最近文件推断参数
```

这样 AI 可以先执行轻量 query 判断状态，再决定是否全量调用。

---

## 5. 验证清单（部署后测试）

修改完成后，用以下 prompt 验证系统是否生效：

```
1. "初始化项目记忆系统" → 应触发 harness init
2. "创建登录模块任务" → 应触发 task create，返回 task id
3. "记住这个：用 Redis 做 session" → 应触发 checkpoint --note 或 lesson
4. "刚才的 auth-001 继续" → 应触发 task resume 并读取相关文件
5. "把 auth-001 归档" → 应触发 task archive
```

如果 AI 仍不执行，在 prompt 中追加：**"严格遵守 agents.md 中的强制触发条件，立即调用 harness-agent skill"** 强制激活。

需要我基于你的 `harness.py` 实际代码结构，生成更具体的 skill 调用模板吗？
User: 有个问题，agent的实现不是很规范，agent作为顶层规则设置，不应该直接声明skill中的py文件调用场景，它应该声明skill的调用而不是skill中python工具的调用
Kimi: 你说得对，我混淆了架构层级。规范驱动的核心就是**严格分离约束声明层（agents.md）和实现细节层（skill）**。

以下是修正后的分层架构：

---

## 1. agents.md（纯约束层，无实现细节）

```markdown
---
type: system-prompt
enforce: true
---

# AI任务记忆控制器 v9.1

## 核心原则

1. **单一入口原则**
   所有 `.ai/` 目录的状态变更，**必须**通过调用 `harness-agent` skill 完成。禁止任何直接文件操作。

2. **显式优于隐式原则**
   状态迁移（新建、推进、归档、记忆捕获）必须由显式指令触发。禁止静默推断修改。

3. **不可变历史原则**
   归档记录、经验教训、技术决策只追加、不修改、不删除。

## 强制触发条件（满足任一即调用 harness-agent）

| 场景 | 动作 |
|------|------|
| 用户提及 `.ai/` 目录操作 | 调用 harness-agent |
| 涉及任务生命周期（创建/恢复/归档） | 调用 harness-agent |
| 用户说"记住这个"、"记录技术决策" | 调用 harness-agent |
| 需要查询当前任务状态或焦点 | 调用 harness-agent |
| 环境配置变更需持久化 | 调用 harness-agent |

## 禁止清单（红灯）

- [ ] **严禁** 使用 Read/Edit/Write 工具直接操作 `.ai/` 下任何文件
- [ ] **严禁** 在主上下文直接解析 `.ai/` 文件内容后手动修改
- [ ] **严禁** 绕过 harness-agent 直接执行记忆相关 Bash 命令

## 失效处理

若 harness-agent 调用失败，报告错误并停止操作。**禁止**因失败转为直接文件编辑。
```

---

## 2. harness-agent.md（实现层，包含具体 CLI）

```markdown
---
name: harness-agent
description: |
  实现 .ai/ 记忆系统的原子化操作入口。接收上层 agents.md 的调用指令，执行具体的 harness.py CLI 操作。
  
  职责：
  1. 任务生命周期管理（create/resume/archive）
  2. 检查点捕获（checkpoint）
  3. 知识库沉淀（tech/lesson）
  4. 环境状态记录（env）
  
  约束：所有操作必须通过 python harness.py CLI，禁止直接文件写入
---

# Harness Agent 实现手册

## 初始化项目
```bash
python harness.py init [--project-name "项目名"]
```

## 任务生命周期
```bash
# 创建
python harness.py task create "任务名" --prefix {前缀}

# 恢复（返回上下文）
python harness.py task resume {task-id}

# 归档
python harness.py task archive {task-id}
```

## 检查点捕获
```bash
python harness.py checkpoint {task-id} \
  --stage "{阶段名}" \
  --progress {0-100} \
  --todo "待办1\n待办2" \
  --file {焦点文件} \
  --line {行号} \
  --function {函数名} \
  --snippet "{代码片段}" \
  --next-action "{下一步}" \
  --blocker "{阻塞点}" \
  --note "{用户要求记住的内容}" \
  --context "{关联文件}|{行范围}|{类型}|{描述}"
```

## 知识库
```bash
# 技术决策
python harness.py tech --title "{ADR-xxx}" --content "{决策内容}"

# 经验教训
python harness.py lesson "{内容}"
```

## 环境记录
```bash
python harness.py env
python harness.py env --key {key} --value {value}
```

## 上下文恢复流程

当执行 `task resume` 后，按以下步骤恢复：
1. 解析 CLI 输出的 focus_file、focus_line、focus_function
2. 使用 Read 工具读取 focus_file 相关内容
3. 解析 context 列出的关联文件，按需读取
4. 向主上下文汇报恢复状态

## 数据格式约束

- focus: 单文件单点
- context: 最多 5 项，格式 `文件|行范围|类型|描述`
- snippet: ≤ 80 字符
- todo: 换行分隔
```

---

## 3. 关键修正点对比

| 层级 | 错误做法（之前） | 正确做法（现在） |
|------|-----------------|-----------------|
| **agents.md** | 出现 `python harness.py task create` 等具体命令 | 只声明"调用 harness-agent"，无具体命令 |
| **agents.md** | 描述 explore/general subagent 分工 | 只声明约束和触发条件 |
| **skill** | 简单描述用途 | 包含全部 CLI 实现细节、参数格式、操作流程 |

---

## 4. 给你的使用建议

为了让 AI 更可靠地遵循这个分层架构，建议在你的项目根目录添加 `.kimi/agents.md`（或类似），并在对话开始时明确引用：

```
请严格遵守项目根目录 .kimi/agents.md 中的约束。涉及 .ai/ 目录的任何操作，必须调用 harness-agent skill 完成，禁止直接文件操作。
```

这样 AI 会先加载顶层约束，在触发条件满足时自动寻找 harness-agent skill，形成**约束→触发→实现**的完整链条。

这个分层现在符合 Harness Engineering 的规范了吗？需要我调整 skill 内部的具体命令格式吗？
User: 保存为markdown文件供我下载吧
Kimi: 已为你创建规范分层后的两个文件：

**约束层（放置于项目根目录或 .kimi/）：**
[agents.md](sandbox:///mnt/kimi/output/agents.md)

**实现层（放置于 skill 目录）：**
[harness-agent.md](sandbox:///mnt/kimi/output/harness-agent.md)

---

**使用建议：**

1. **agents.md** 放在项目根目录或 `.kimi/` 下，作为顶层规则被自动加载
2. **harness-agent.md** 放入你的 skill 目录（如 `.kimi/skills/`）
3. 对话开始时引用：*"请严格遵守 agents.md 中的约束，涉及 .ai/ 操作必须调用 harness-agent skill"*

这样 AI 会遵循 **约束层声明触发条件 → 实现层执行具体 CLI** 的规范架构，避免 agents.md 直接侵入 skill 的实现细节。
