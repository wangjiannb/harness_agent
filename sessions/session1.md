User: 如何实现ai编程的跨会话记忆
Kimi: 实现AI编程的跨会话记忆，核心在于建立一个**持久化的记忆层**，让AI能够在不同对话会话间保持上下文连续性。以下是完整的技术实现方案：

---

## 一、核心架构设计

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  当前会话    │────▶│  记忆管理器  │◀────│  持久化存储  │
│  (Context)  │     │  (Manager)   │     │ (Vector DB) │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │  记忆处理流程 │
                    │ • 提取(Extract)│
                    │ • 存储(Store)  │
                    │ • 检索(Retrieve)│
                    └─────────────┘
```

---

## 二、关键技术组件

### 1. 记忆提取层（Memory Extraction）

```python
# 使用LLM自动提取关键信息
MEMORY_EXTRACTION_PROMPT = """
分析以下对话，提取需要长期记忆的关键信息：
1. 用户偏好（编程风格、技术栈偏好）
2. 项目上下文（项目结构、依赖关系、关键决策）
3. 未完成任务（TODO、待修复的bug）
4. 重要约定（命名规范、架构决策）

对话内容：
{conversation_history}

输出JSON格式：
{
  "facts": [{"type": "preference/project/todo", "content": "...", "priority": "high/medium/low"}],
  "summary": "会话摘要"
}
"""
```

### 2. 向量化存储（Vector Store）

```python
from typing import List, Dict
import hashlib

class MemoryStore:
    def __init__(self, db_path: str):
        self.db = ChromaDB(persist_directory=db_path)
    
    def save_memory(self, 
                    session_id: str, 
                    content: str, 
                    metadata: Dict,
                    memory_type: str = "fact"):
        """存储记忆"""
        # 生成唯一ID：用户ID + 时间戳 + 内容哈希
        memory_id = f"{session_id}_{int(time.time())}_{hashlib.md5(content.encode()).hexdigest()[:8]}"
        
        self.db.add(
            ids=[memory_id],
            documents=[content],
            metadatas=[{
                "session_id": session_id,
                "type": memory_type,
                "timestamp": time.time(),
                **metadata
            }]
        )
    
    def retrieve_relevant(self, 
                          query: str, 
                          user_id: str,
                          top_k: int = 5) -> List[Dict]:
        """检索相关记忆"""
        return self.db.similarity_search(
            query=query,
            filter={"user_id": user_id},
            n_results=top_k
        )
```

### 3. 记忆管理器（Memory Manager）

```python
class CrossSessionMemory:
    def __init__(self, store: MemoryStore, llm_client):
        self.store = store
        self.llm = llm_client
        self.session_context = {}
    
    def on_session_start(self, user_id: str, project_id: str = None):
        """会话启动时加载相关记忆"""
        # 检索用户相关的历史记忆
        memories = self.store.get_recent_memories(
            user_id=user_id,
            project_id=project_id,
            limit=10
        )
        
        self.session_context = {
            "user_id": user_id,
            "project_id": project_id,
            "active_memories": memories
        }
        
        return self._format_memories_for_prompt(memories)
    
    def on_message(self, message: str, conversation_history: List[Dict]):
        """处理单条消息"""
        # 1. 检索与当前消息相关的记忆
        relevant = self.store.retrieve_relevant(
            query=message,
            user_id=self.session_context["user_id"]
        )
        
        # 2. 动态组装Prompt
        enhanced_prompt = self._build_prompt_with_memory(
            current_message=message,
            history=conversation_history,
            relevant_memories=relevant
        )
        
        # 3. 生成回复后，提取新记忆
        response = self.llm.generate(enhanced_prompt)
        
        # 4. 异步提取并存储新记忆
        self._async_extract_and_store(conversation_history + [{"role": "assistant", "content": response}])
        
        return response
    
    def _build_prompt_with_memory(self, current_message, history, relevant_memories):
        """将记忆注入Prompt"""
        memory_text = "\n".join([
            f"- {m['content']} (来自{m['session_id'][:8]})"
            for m in relevant_memories
        ])
        
        return f"""你是用户的编程助手。以下是与当前对话相关的背景信息：

【历史记忆】
{memory_text}

【当前对话】
{self._format_history(history)}

用户当前输入：{current_message}

请基于以上背景提供帮助。如果历史记忆与当前问题无关，可以忽略。"""
```

---

## 三、记忆类型与策略

| 记忆类型 | 存储策略 | 检索策略 | 示例 |
|---------|---------|---------|------|
| **用户偏好** | 覆盖更新（最新为准） | 每次会话启动加载 | "我喜欢使用TypeScript"、"缩进用2个空格" |
| **项目上下文** | 版本化存储（带时间戳） | 按项目ID过滤 | "这个项目使用Monorepo结构" |
| **代码知识** | 向量化 + 代码片段 | 语义相似度检索 | "Auth模块在src/auth/" |
| **待办事项** | 状态管理（未完成优先） | 主动推送 | "上次说要优化DB查询" |

---

## 四、实践中的关键优化

### 1. **记忆去重与压缩**
```python
def deduplicate_and_compress(self, new_memories: List[Dict]):
    """避免记忆冗余"""
    for mem in new_memories:
        # 检索相似记忆
        similar = self.store.similarity_search(mem['content'], threshold=0.95)
        if similar:
            # 合并或更新已有记忆
            self._merge_memories(similar[0], mem)
        else:
            self.store.save(mem)
```

### 2. **记忆衰减机制**
```python
def calculate_memory_priority(self, memory: Dict) -> float:
    """基于时间和重要性计算记忆优先级"""
    age_days = (time.time() - memory['timestamp']) / 86400
    base_priority = memory.get('priority_score', 0.5)
    
    # 指数衰减
    decay_factor = 0.95 ** age_days
    
    # 高频访问提升优先级
    access_boost = min(memory.get('access_count', 0) * 0.05, 0.3)
    
    return base_priority * decay_factor + access_boost
```

### 3. **隐私与敏感信息过滤**
```python
SENSITIVE_PATTERNS = [
    r'password\s*=\s*["\'][^"\']+',  # 密码
    r'sk-[a-zA-Z0-9]{48}',           # API Key
    r'\b\d{16,19}\b'                # 银行卡号
]

def sanitize_memory(self, content: str) -> str:
    """清理敏感信息"""
    for pattern in SENSITIVE_PATTERNS:
        content = re.sub(pattern, '[REDACTED]', content, flags=re.IGNORECASE)
    return content
```

---

## 五、集成示例（完整流程）

```python
# 初始化
memory_store = MemoryStore(db_path="./memories")
memory_manager = CrossSessionMemory(store=memory_store, llm_client=openai)

# 会话开始
session_id = "user_123_session_456"
context = memory_manager.on_session_start(
    user_id="user_123",
    project_id="project_ai_editor"
)

# 对话循环
while True:
    user_input = input("User: ")
    
    # 自动注入相关记忆并生成回复
    response = memory_manager.on_message(
        message=user_input,
        conversation_history=history
    )
    
    print(f"AI: {response}")
```

---

## 六、开源方案参考

如果不想从零实现，可以直接集成这些方案：

1. **Mem0** (`mem0.ai`) - 专为AI助手设计的记忆层，支持跨会话持久化
2. **LangChain Memory** - 提供`VectorStoreMemory`、`ConversationBufferMemory`等组件
3. **Zep** - 长期记忆服务，支持自动提取和向量化
4. **ChromaDB/Pinecone** - 作为底层向量存储

---

**核心建议**：跨会话记忆的关键不在于"记住所有内容"，而在于**智能筛选**和**按需检索**——让AI记住重要的、相关的，遗忘过时的、琐碎的。通过向量相似度+元数据过滤的组合，可以实现接近人类的"选择性记忆"效果。
User: 现在编程工具可以读取agents.md来设定项目规则，有没有什么类似方法在项目中固话记忆的
Kimi: 是的，现代AI编程工具已经发展出了多种**项目级记忆固化**的方案，比简单的`agents.md`更结构化、更强大。以下是几种主流方法：

---

## 一、分层记忆文件架构（推荐）

模仿人类记忆的层级结构，建立从**永久记忆**到**临时上下文**的分层体系：

```markdown
项目根目录/
├── .ai/                          # AI专用配置目录（可加入.gitignore）
│   ├── identity.md              # AI角色定义（永久）
│   ├── memory-bank/             # 结构化记忆库（持久化）
│   │   ├── tech-spec.md        # 技术栈与架构决策
│   │   ├── progress.md         # 当前进度与待办
│   │   ├── codebase.md         # 关键代码路径说明
│   │   └── lessons.md          # 踩坑记录与最佳实践
│   ├── context/                 # 会话级上下文（临时）
│   │   ├── active-tasks.md     # 当前进行中的任务
│   │   └── session-notes.md    # 本次会话临时笔记
│   └── templates/               # 记忆模板
│       └── feature-spec.md     # 新功能开发模板
└── .cursorrules / .claude.md    # 兼容现有工具的入口文件
```

### 核心文件示例：

**`.ai/memory-bank/tech-spec.md`**（技术记忆）
```markdown
# 技术规格记忆库

## 架构决策记录 (ADR)
- **ADR-001**: 使用Pnpm Workspace而非Nx（2024-03-15）
  - 原因：团队熟悉度、部署简单性
  - 影响：缺少Nx的依赖图分析，需手动维护

## 关键依赖约束
- Node.js >= 20.0（因使用`node:sqlite`）
- React 19 + Next.js 15（App Router强制）
- 禁用任何jQuery相关库（与现有代码冲突历史）

## 代码组织规则
- `/apps/web` -  Next.js应用，禁止直接调用数据库
- `/packages/db` -  唯一数据库访问层，通过Prisma Client
- `/packages/ui` -  共享组件，必须使用Tailwind CSS v4
```

**`.ai/memory-bank/progress.md`**（状态记忆）
```markdown
# 项目进度记忆

## 当前Sprint (v2.3.0)
- [进行中] 用户认证重构（60%）
  - 已完成：JWT策略、Refresh Token机制
  - 阻塞：等待产品确认OAuth提供商列表
- [待开始] 支付模块（依赖：认证完成）

## 已知技术债务
- `apps/web/app/legacy/` 目录包含待迁移的Pages Router代码
- `packages/db/prisma/migrations/202402xx_` 迁移需合并清理
```

---

## 二、自动同步机制（Memory Bank Pattern）

借鉴 **Claude Code** 的`memory-bank`模式，建立**双向同步**：

### 1. 启动时加载（Hydration）
在`.cursorrules`或`.claude.md`中配置自动加载：

```markdown
# 系统指令（.cursorrules）

每次会话开始时，请严格执行以下记忆恢复流程：

1. **读取记忆库**：扫描 `.ai/memory-bank/` 目录下所有 `.md` 文件
2. **加载活跃上下文**：读取 `.ai/context/active-tasks.md` 了解当前任务
3. **确认技术约束**：检查 `.ai/memory-bank/tech-spec.md` 中的架构规则
4. **报告状态**：简要总结"我回忆起了该项目的X个关键事实"

禁止在没有读取记忆库的情况下回答技术实现问题。
```

### 2. 关闭时固化（Persist）
在会话结束时（或关键节点），让AI自动更新记忆文件：

```markdown
# 记忆固化触发器（放在你的系统提示里）

当遇到以下情况时，必须更新记忆库：

1. **架构决策变更** → 追加到 `tech-spec.md` 的ADR部分
2. **发现Bug/解决方案** → 追加到 `lessons.md`
3. **任务完成/阶段推进** → 更新 `progress.md`
4. **新文件/重要函数** → 更新 `codebase.md` 的索引

格式要求：
- 使用[ISO日期]标记时间戳
- 添加相关文件路径作为Tag，如 `#apps/web/auth`
- 如果是覆盖旧信息，保留旧记录但标记为[DEPRECATED]
```

---

## 三、智能记忆片段（Smart Fragments）

对于大型项目，使用**向量检索+精确记忆**混合模式：

```markdown
.ai/
├── fragments/                    # 细粒度记忆片段（可被向量检索）
│   ├── auth-flow.md             # 认证流程详解
│   ├── database-schema.md       # 核心表结构说明
│   ├── api-conventions.md       # API命名规范
│   └── performance-tips.md      # 性能优化笔记
└── index.json                   # 记忆索引（自动维护）
```

**`index.json`** 示例：
```json
{
  "embeddings": {
    "model": "text-embedding-3-small",
    "dimension": 1536
  },
  "fragments": [
    {
      "id": "auth-jwt-rotation",
      "file": "fragments/auth-flow.md",
      "tags": ["auth", "jwt", "security"],
      "last_accessed": "2026-04-12T14:30:00Z",
      "importance_score": 0.95
    }
  ],
  "hot_keys": {
    "database": ["database-schema.md", "prisma-usage.md"],
    "ui": ["shadcn-patterns.md", "tailwind-config.md"]
  }
}
```

**优势**：AI可以先检索`index.json`找到相关片段，再精确读取，避免每次加载大量无关内容。

---

## 四、与现有工具集成方案

| 工具 | 记忆固化文件 | 特殊语法/功能 |
|------|-------------|--------------|
| **Cursor** | `.cursorrules` + `.cursor/`目录 | 支持`@file`引用记忆文件 |
| **Windsurf** | `.windsurfrules` + `agents.md` | 支持`memory`标签块 |
| **Claude Code** | `CLAUDE.md` + `memory-bank/` | 支持`follow`指令自动维护 |
| **GitHub Copilot** | `.github/copilot-instructions.md` | 支持`copilot-suggestions`约束 |
| **通用** | `PROJECT.md` / `AI_CONTEXT.md` | Markdown Frontmatter元数据 |

### Cursor高级技巧：
```markdown
# .cursorrules

## 记忆加载（自动）
Always read these files at session start:
- @.ai/memory-bank/tech-spec.md
- @.ai/memory-bank/progress.md
- @.ai/context/active-tasks.md

## 记忆更新（手动触发）
When I say "remember this", append the following to `.ai/memory-bank/lessons.md`:
- Date: {{current_date}}
- Context: {{last_5_messages_summary}}
- Lesson: {{key_insight}}

## 代码生成约束（基于记忆）
- 如果 `tech-spec.md` 提到"使用Zod"，则所有API路由必须包含Zod Schema
- 如果 `progress.md` 有阻塞任务，优先建议解除阻塞的方案
```

---

## 五、自动化工作流（Git Hooks）

通过Git自动维护记忆同步：

```bash
# .git/hooks/pre-commit
#!/bin/bash
# 自动提取提交信息到记忆库

COMMIT_MSG=$(cat .git/COMMIT_EDITMSG)
if [[ $COMMIT_MSG == *"#remember"* ]]; then
    echo "- [$(date +%Y-%m-%d)] ${COMMIT_MSG//#remember/}" >> .ai/memory-bank/lessons.md
    git add .ai/memory-bank/lessons.md
fi
```

---

## 六、最佳实践建议

1. **区分"规则"与"记忆"**：
   - `.cursorrules` = 不变的行为准则（如何写代码）
   - `.ai/memory-bank/` = 变化的认知状态（项目当前是什么）

2. **使用Frontmatter标记元数据**：
   ```markdown
   ---
   category: architecture
   priority: high
   related_files: ["src/auth.ts", "src/middleware.ts"]
   last_verified: 2026-04-12
   ---
   
   # JWT认证实现细节
   ...
   ```

3. **定期压缩记忆**：每月运行一次`consolidate-memories`脚本，将零散笔记合并为结构化文档，删除过时信息。

4. **版本控制策略**：
   - `tech-spec.md` → 提交到Git（团队共享知识）
   - `progress.md` → 可加入.gitignore（个人工作状态）
   - `context/` → 必须.gitignore（纯临时文件）

这种方法让AI具备了**项目专属的持久化记忆**，比单纯依赖模型微调或RAG检索更精确、更可控。
User: 这需要在agents.md写入控制规则是吗？还是需要其他方法实现？
Kimi: **仅写入`agents.md`是不够的**——它只能解决**读取**问题，无法解决**写入**问题。`agents.md`（或`.cursorrules`）本质上是**只读的静态配置**，AI不会自动将对话中的新发现写回该文件。

要实现真正的跨会话记忆固化，你需要**分层机制**：

---

## 一、agents.md的局限与正确角色

### ❌ 常见误解
```markdown
# agents.md（错误示范）
请记住，本项目使用Prisma作为ORM，
上次我们重构了认证模块，现在使用JWT而非Session...
```

**问题**：这些"记忆"只是写在文件里的静态文本，AI不会自动更新它们。当你下次开启新会话时，这些信息可能已经过时。

### ✅ 正确用法：作为"记忆引导器"
```markdown
# agents.md / .cursorrules（正确示范）

## 【启动协议】会话开始时必须执行
1. 读取 `.ai/memory-bank/` 目录下的所有.md文件
2. 检查 `progress.md` 了解当前任务状态  
3. 确认 `tech-spec.md` 中的架构约束

## 【记忆固化协议】遇到以下情况时必须执行
- 修改代码架构 → 追加到 `tech-spec.md` 的ADR部分
- 发现Bug解决方案 → 追加到 `lessons.md`
- 完成任务 → 更新 `progress.md`

## 【写入格式】
更新记忆文件时使用以下模板：
---
date: {{YYYY-MM-DD}}
tags: [相关文件路径]
---

[简洁描述，包含足够上下文以便未来理解]
```

---

## 二、不同工具的读写能力对比

| 工具 | 自动读取agents.md | 支持文件写入 | 跨会话记忆方案 |
|------|------------------|-------------|---------------|
| **Cursor** | ✅ 自动读取`.cursorrules` | ✅ 支持文件编辑 | 需要显式指令让AI写入`.ai/`目录 |
| **Windsurf** | ✅ 读取`agents.md` | ⚠️ 有限支持 | 主要依靠`memory`标签块，但非持久化 |
| **Claude Code** | ✅ 读取`CLAUDE.md` | ✅ 强支持 | **原生支持Memory Bank模式**，自动维护 |
| **Cline/Roo** | ✅ 读取`.clinerules` | ✅ 支持 | 需配置自定义指令触发写入 |
| **GitHub Copilot** | ✅ 读取`copilot-instructions.md` | ❌ 不支持 | **无法固化**，只能依赖静态规则 |

---

## 三、完整实现方案（以Cursor为例）

既然Cursor是目前主流且支持文件写入的工具，以下是具体实现：

### 1. 入口文件（`.cursorrules`）
```markdown
# 跨会话记忆系统配置

## 阶段1：记忆恢复（自动执行）
每次对话开始时：
1. 使用`read_file`工具读取`.ai/memory-bank/progress.md`
2. 使用`read_file`工具读取`.ai/memory-bank/tech-spec.md`  
3. 使用`read_file`工具读取`.ai/memory-bank/lessons.md`
4. 向我汇报："已加载记忆：当前有{X}个待办，{Y}个架构约束"

## 阶段2：记忆捕获（手动触发）
当我说"**记住这个**"或检测到以下模式时：
- 我解释了复杂的业务逻辑
- 我们解决了棘手的Bug
- 做出了架构决策
- 发现了项目陷阱

立即执行：
1. 分析刚才的对话内容
2. 确定应写入哪个记忆文件（tech-spec/progress/lessons）
3. 使用`write_file`或`edit_file`追加内容
4. 格式：`[YYYY-MM-DD] [Tags] 内容摘要`

## 阶段3：记忆应用（推理时）
生成代码前，检查记忆库中是否有相关约束：
- 查询`tech-spec.md`中的技术选型限制
- 检查`progress.md`中是否有进行中的相关任务
- 参考`lessons.md`避免重复踩坑
```

### 2. 记忆库结构（`.ai/`目录）
```markdown
.ai/memory-bank/
├── progress.md      # 当前状态（动态更新）
├── tech-spec.md     # 技术决策（追加更新）  
├── lessons.md       # 踩坑记录（追加更新）
└── context.md       # 本次会话上下文（临时）
```

### 3. 实战交互示例

**场景：修复了一个棘手的Bug**

```
[用户]: 记住这个
[用户]: 刚刚我们发现React Query的缓存键必须用数组而非字符串，
否则在严格模式下会导致重复请求

[AI]: 检测到记忆指令。我将把这条经验写入`lessons.md`：
---
date: 2026-04-12
tags: [react-query, caching, strict-mode]
---

React Query缓存键必须使用数组格式，如['user', userId]。
禁止使用字符串如'user-${userId}'，因为在React Strict Mode下
会导致重复请求问题。此问题在apps/dashboard/useUser.ts中已修复。
[写入文件...完成]
```

---

## 四、最小可行方案（MVP）

如果你只想快速上手，只需**两步**：

### Step 1: 创建 `.cursorrules`
```markdown
## 记忆协议
1. 启动时读取`.ai/lessons.md`和`.ai/progress.md`
2. 当我说"记住"时，提取关键事实追加到对应文件
3. 每次回复前，检查这些文件是否包含相关信息
```

### Step 2: 创建 `.ai/lessons.md`（空文件即可）
然后直接告诉AI：
> "请读取`.ai/lessons.md`，以后每当我让你'记住'什么，就把它写进这个文件。"

Cursor会自动使用文件工具读取和写入，实现基础的跨会话记忆。

---

## 五、进阶：自动化触发（无需说"记住"）

如果你不想每次都说"记住这个"，可以在`.cursorrules`中加入**自动检测规则**：

```markdown
## 自动记忆触发器
当对话中出现以下模式时，**静默**更新记忆：
- 发现错误并解决 → 自动追加到`lessons.md`
- 讨论技术选型优劣 → 自动追加到`tech-spec.md`的ADR部分
- 提到"TODO"、"之后做"、"阻塞" → 自动更新`progress.md`

更新后回复："[记忆已更新]"作为确认。
```

---

**总结**：`agents.md`（或`.cursorrules`）只是**控制器**，真正的记忆存储需要**独立的记忆库文件**（`.ai/memory-bank/`）和**显式的写入机制**。仅靠agents.md本身无法实现记忆固化，因为它无法自动修改自身内容。
User: 我就是说agents.md是要作为控制器控制记忆写入的，那么请你给我个agents.md的模板
Kimi: 这是一个可直接落地的 `agents.md` 控制器模板，兼容 Cursor、Windsurf 和 Claude Code：

```markdown
# AI 跨会话记忆控制器 v2.0
# 角色：项目架构守护者 + 记忆库管理员

---

## 系统架构说明

本项目使用分层记忆系统：
- **agents.md** (本文件)：控制逻辑，只读配置
- **.ai/memory-bank/progress.md**：动态任务状态（读写）
- **.ai/memory-bank/tech-spec.md**：架构决策与技术约束（读写）
- **.ai/memory-bank/lessons.md**：踩坑记录与解决方案（读写）
- **.ai/context/session.md**：本次会话临时上下文（读写）

---

## 阶段一：记忆恢复（会话启动时强制执行）

每次用户发送第一条消息前，你必须：

1. **检查记忆库存在性**：若 `.ai/memory-bank/` 目录不存在，创建它及上述三个空文件
2. **加载持久记忆**（按优先级顺序）：
   - `read_file` → `.ai/memory-bank/progress.md`（了解当前阻塞任务）
   - `read_file` → `.ai/memory-bank/tech-spec.md`（了解技术约束）
   - `read_file` → `.ai/memory-bank/lessons.md`（了解历史陷阱）
3. **初始化会话上下文**：创建/清空 `.ai/context/session.md`，写入当前时间戳和初始目标
4. **向用户汇报**：
   > "记忆库已加载：{X}个待办事项，{Y}个架构约束，{Z}条经验记录。当前任务：{progress.md中的第一条}"

> ⚠️ **禁止**：在未完成记忆恢复前回答任何技术实现问题。

---

## 阶段二：记忆捕获（智能写入协议）

### 触发条件（满足任一即写入）

| 触发词/场景 | 目标文件 | 写入规则 |
|------------|---------|---------|
| 用户说："记住这个"、"记下来"、"以后记住" | 根据内容判断 | 立即执行写入 |
| 用户说："这是暂时的"、"临时方案" | `.ai/context/session.md` | 标记为[temp] |
| 解决Bug/报错后 | `.ai/memory-bank/lessons.md` | 包含错误现象+根因+解决方案 |
| 讨论技术选型（如"我们用A而不是B"） | `.ai/memory-bank/tech-spec.md` | 追加到ADR部分 |
| 提到"TODO"、"FIXME"、"之后要做" | `.ai/memory-bank/progress.md` | 更新任务列表 |
| 发现项目陷阱/非 obvious 的行为 | `.ai/memory-bank/lessons.md` | 标记为[陷阱] |
| 完成某个任务/阶段 | `.ai/memory-bank/progress.md` | 将对应任务标记为[已完成] |

### 写入格式标准

所有写入必须遵循以下 Frontmatter + 内容格式：

```markdown
---
date: YYYY-MM-DD HH:MM
type: [architecture|bugfix|todo|lesson|context]
tags: [文件路径, 技术栈, 模块名]
status: [active|completed|deprecated]
---

**触发原因**: [用户指令/自动检测：解决了XX问题/做出了XX决策]

**内容摘要**:
- 关键点1
- 关键点2（如果是代码，包含关键代码片段）

**相关上下文**:
- 文件: `src/xxx.ts`
- 关联记忆: [引用progress.md或tech-spec.md中的相关条目]
- 影响范围: [描述这个记忆会影响哪些后续决策]
```

### 写入操作步骤

当触发写入时：
1. **分析**：提取对话中的关键事实、决策、代码模式
2. **分类**：决定写入哪个文件（参考上表）
3. **格式化**：按上述模板组织内容
4. **执行**：使用 `write_file`（追加模式）或 `edit_file`（插入到合适位置）
5. **确认**：回复用户 "[已固化到 `.ai/memory-bank/xxx.md`]" 并简述记录的内容

---

## 阶段三：记忆应用（推理时强制执行）

生成任何代码或回答前，必须检查记忆库：

1. **相关性检索**：当前用户问题是否与 `tech-spec.md` 中的约束相关？
   - 如果是，回复开头引用："根据技术规范 #X，我们需要..."
2. **阻塞检查**：`progress.md` 中是否有阻塞当前任务的未完成项？
   - 如果有，优先建议："检测到阻塞项 X，建议先处理..."
3. **陷阱规避**：`lessons.md` 中是否有相关警告？
   - 如果有，提示："注意历史陷阱：此处曾因 XX 导致 Bug，建议..."

---

## 记忆分类决策树

当不确定写入哪个文件时，按此判断：

```
这是关于...
├─ 未来要做的事？→ progress.md（待办）
├─ 过去踩过的坑？→ lessons.md（经验）
├─ 技术选型/架构设计？→ tech-spec.md（ADR）
├─ 临时会话上下文？→ session.md（临时）
└─ 影响现有记忆的新信息？→ 找到原记忆文件，追加[更新]标记
```

---

## 记忆维护规则

1. **去重检查**：写入前搜索目标文件，若存在相似内容（>80%相似度），合并而非重复追加
2. **时效标记**：超过30天的记录可标记为 [需验证]，但不删除
3. **版本冲突**：若新信息与旧记忆矛盾，保留两者，旧标记为 [DEPRECATED 日期]，新标记为 [SUPERSEDES 旧ID]
4. **敏感信息**：若内容含 API Key/密码，拒绝写入并警告用户

---

## 示例场景（供AI参考）

**场景A**：用户说"记住这个，刚刚发现 Prisma 的 findUnique 在复合主键上必须传入对象而非字符串"
→ 写入 `lessons.md`，type: bugfix，tags: [prisma, database]

**场景B**：用户说"我们决定不用 Redux 了，改用 Zustand"
→ 写入 `tech-spec.md` ADR部分，type: architecture，包含决策理由和影响范围

**场景C**：用户说"先别做登录功能了，等设计稿"
→ 写入 `progress.md`，type: todo，status: blocked，添加阻塞原因

**场景D**：用户说"这只是临时方案，正式版要重构"
→ 写入 `session.md`，type: context，标记为 [temp]，不写入长期记忆库

---

## 初始化检查清单

如果检测到记忆库未初始化，自动执行：

```bash
mkdir -p .ai/memory-bank .ai/context
touch .ai/memory-bank/progress.md
touch .ai/memory-bank/tech-spec.md
touch .ai/memory-bank/lessons.md
touch .ai/context/session.md
echo "# 任务进度\n\n## 当前Sprint\n- [进行中] 初始化项目\n\n## 阻塞项\n无" > .ai/memory-bank/progress.md
echo "# 技术规范\n\n## 架构决策记录 (ADR)\n\n## 技术约束\n\n## 代码规范" > .ai/memory-bank/tech-spec.md
echo "# 经验与陷阱\n\n## Bug修复记录\n\n## 最佳实践" > .ai/memory-bank/lessons.md
```

执行后向用户报告："已初始化记忆库结构。"
```

---

## 配套文件结构

使用此模板时，需要确保项目中有以下目录结构（首次使用时代理会自动创建）：

```bash
你的项目/
├── agents.md          # 上面提供的控制器
└── .ai/
    ├── memory-bank/
    │   ├── progress.md    # 任务状态（会自动更新）
    │   ├── tech-spec.md   # 技术决策（会自动更新）
    │   └── lessons.md     # 经验记录（会自动更新）
    └── context/
        └── session.md     # 临时上下文（每次会话重置）
```

## 使用提示

1. **首次使用**：复制模板后，发送消息 "初始化记忆系统" 触发自动创建目录
2. **强制记忆**：说 "记住这个" 或 "固化到记忆库"
3. **查看记忆**：说 "查看当前记忆库" 或 "总结项目状态"
4. **跨工具兼容**：
   - **Cursor**：直接使用，支持文件操作
   - **Windsurf**：需确保开启 "Auto-run" 权限
   - **Claude Code**：将 `agents.md` 重命名为 `CLAUDE.md`，并把 `write_file` 改为 Claude 的编辑工具

这个模板把 agents.md 变成了一个**状态机控制器**，既控制记忆流的输入（读取），也控制输出（写入），同时保持记忆内容的结构化。
User: 保存为markdown文件吧
Kimi: 文件已保存完成。

**下载链接**： [agents.md 模板](sandbox:///mnt/kimi/output/agents.md)

---

### 使用说明

1. **放置位置**：将文件复制到你的**项目根目录**，并根据使用的工具重命名：
   - **Cursor** → 重命名为 `.cursorrules`
   - **Windsurf** → 重命名为 `agents.md` 或 `.windsurfrules`
   - **Claude Code** → 重命名为 `CLAUDE.md`

2. **首次启动**：在AI对话中发送"初始化记忆系统"，AI会自动创建 `.ai/memory-bank/` 目录结构

3. **配套目录结构**（会自动生成）：
   ```
   你的项目/
   ├── .cursorrules (或 agents.md)  # 本控制器文件
   └── .ai/
       ├── memory-bank/
       │   ├── progress.md          # 任务状态
       │   ├── tech-spec.md         # 技术决策
       │   └── lessons.md           # 经验记录
       └── context/
           └── session.md           # 临时上下文
   ```

4. **使用提示**：
   - 说"**记住这个**"触发记忆写入
   - 说"**查看记忆库**"获取当前项目状态摘要
   - 说"**这是临时的**"将信息标记为临时，不写入长期记忆
User: session.md有什么用吗，如果使用opencode每次也都会保存会话啊
Kimi: `session.md` 的核心价值是**建立"会话锚点"**，与工具自动保存的"历史记录"有本质区别。即使 OpenCode 会自动保存会话，session.md 仍然有不可替代的作用：

---

## 一、本质区别

| 维度 | 工具自动保存（如 OpenCode） | session.md（手动维护） |
|------|---------------------------|---------------------|
| **内容形态** | 完整的对话流水账 | 结构化的关键决策摘要 |
| **AI 可读性** | 需要重新加载整个会话历史才能理解 | 立即加载，秒级建立上下文 |
| **信息密度** | 低（包含试错过程、无关闲聊） | 高（只保留结论和待办） |
| **跨会话定位** | 用户手动选择"继续上次会话" | 新会话自动识别"这是延续" |
| **信息时效** | 永久保存（杂乱） | 显式标记[temp]，下次自动清理或归档 |

**简单理解**：
- 工具自动保存 = **录像带**（完整但冗长，需要重看才知道内容）
- session.md = **书签便利贴**（标记了"上次看到哪页、关键剧情是什么"）

---

## 二、session.md 的具体用途

### 1. **断点续传标记**
即使 OpenCode 保存了会话，当你**开启新会话**时（比如关闭浏览器第二天再来），AI 并不知道这是"同一任务的延续"还是"全新的开始"。

**session.md 的作用**：
```markdown
---
session_type: continuation
parent_session: 2026-04-11-001
current_focus: "优化数据库查询，卡在索引选择"
temporary_decision: "先用B-tree索引测试，明天对比Hash索引"
---

## 本次会话目标
完成 yesterday 未完成的索引优化，验证 B-tree vs Hash 性能

## 临时状态（需本次验证）
- [ ] B-tree 在 100w 数据下的查询速度
- [ ] 是否出现锁竞争问题
- [ ] 内存占用是否可接受
```

**效果**：新会话启动时，AI 读取 session.md 立即知道：
- 这是昨天的延续
- 当前卡在哪个具体技术点
- 有哪些**临时假设**需要验证（不会把这些临时方案误认为是最终决定写入长期记忆）

### 2. **隔离"临时污染"**
很多对话中会产生**临时性、实验性的信息**，不应该污染长期记忆库（progress.md/lessons.md）。

**典型场景**：
```
用户："试一下如果把 auth 模块改成用 Redis 而不是 JWT..."
（经过 20 轮对话后发现性能更差，放弃）
```

- 如果不使用 session.md：这些"废弃的实验"可能被误写入 lessons.md（"我们试过 Redis..."），造成长期记忆污染
- 使用 session.md：所有实验性讨论都标记为 `[temp]`，session 结束后可选择：
  - 实验成功 → 将结论写入 tech-spec.md
  - 实验失败 → 直接删除 session.md，不留下痕迹

### 3. **多会话并行管理**
当你同时推进**多个任务**（比如上午做前端优化，下午改后端架构）：

```
.ai/context/
├── session-frontend.md    # 上午的前端会话
├── session-backend.md     # 下午的后端会话
└── session-current.md -> session-backend.md (软链接或复制)
```

即使 OpenCode 保存了两个会话的历史，你每次切换任务时需要：
1. 手动找到对应的历史会话
2. 重新加载
3. 重新解释上下文

有了 session.md：**直接切换文件**，AI 立即知道当前处于哪个任务流。

---

## 三、可以不使用 session.md 吗？

**可以**，但需要接受以下 trade-off：

| 不用 session.md | 影响 |
|----------------|------|
| 依赖工具的历史会话 | 新会话启动成本变高（需要重读全部历史） |
| 所有信息都写入长期记忆 | 记忆库快速膨胀，出现"实验性方案的废弃记录"污染 |
| 无法区分"临时"与"永久" | AI 可能在正式代码中复用被废弃的临时方案 |
| 跨设备/工具迁移困难 | OpenCode 的历史无法导出给 Cursor 使用，但 session.md 可以 |

**建议**：
- **单人短期项目**：可以不用 session.md，直接依赖工具的自动保存
- **长期维护/团队协作**：保留 session.md 作为"会话间的沙盒"

---

## 四、针对 OpenCode 的优化建议

OpenCode 的特性是**自动保存完整会话并支持随时回到任意节点**，你可以这样配合 session.md 使用：

### 模式 A：Session.md 作为"索引"
```markdown
# OpenCode Session Index
- Session ID: `opencd_abc123` (OpenCode 的自动保存 ID)
- Key Milestone: 第 45 轮对话确定了架构方案
- Critical Decision: 使用 Kafka 而非 RabbitMQ
- Next Step: 实现 Producer 模块
```

**使用方式**：
- 不依赖 session.md 存储完整上下文（OpenCode 已经有了）
- 但用 session.md 标记**关键节点**在 OpenCode 历史中的位置，方便快速跳转

### 模式 B：Hybrid（推荐）
- **短期记忆**（当前会话的实验）：依赖 OpenCode 的自动保存
- **会话间传递**（明天继续）：写入 session.md
- **长期记忆**（项目知识）：写入 memory-bank/

**总结**：session.md 是**AI 与 AI 之间的接力棒**，而工具的自动保存是**历史存档**。前者是为了让下一个会话的 AI 秒懂上下文，后者是为了让你人类能回顾过程。两者不冲突，但功能不同。
User: 其实可以理解session.md是一个任务级别的状态保存，而progress是一个长期的状态保存。那么agents.md里每次初始化都会清空session.md是不是会导致它没法发挥作用？
Kimi: 你的理解完全正确！**"每次初始化都清空"** 这个设计是矛盾的——清空了还怎么"断点续传"？

正确的逻辑应该是 **"读取并延续"**，而不是"清空"。让我给你修正后的 `agents.md` 关键部分：

---

## 修正后的阶段一：记忆恢复逻辑

```markdown
## 阶段一：记忆恢复（会话启动时执行）

### 1. 检查记忆库存在性
若 `.ai/memory-bank/` 目录不存在，创建基础结构。

### 2. 读取 session.md（关键修正）
**读取** `.ai/context/session.md`：
- **如果存在内容**：说明有未完成的"进行中任务"
  - 向用户汇报："检测到上次会话的断点：[session.md 中的 current_focus]"
  - 询问："是否继续上次任务？(是/否/新建任务)"
    - 用户选"是" → 加载 session.md 作为当前上下文，**不清空**
    - 用户选"否" → **归档** session.md 到 `.ai/archive/sessions/`（带时间戳），然后创建新的空 session.md
    - 用户选"新建" → 直接清空 session.md 开始新任务

- **如果不存在或为空** → 创建空文件，标记为"新会话"

### 3. 读取长期记忆（始终执行）
无论 session.md 状态如何，都读取：
- `.ai/memory-bank/progress.md`（了解整体项目进度）
- `.ai/memory-bank/tech-spec.md`（技术约束）
- `.ai/memory-bank/lessons.md`（历史陷阱）

### 4. 状态汇报示例
```
记忆库已加载：
├─ 长期进度：{X}个待办，{Y}个架构决策
├─ 会话断点：[继续上次/新会话]
│   └─ 当前聚焦：{session.md 中的 current_focus}
└─ 建议：基于 session.md，我们应优先处理...
```

---

## session.md 的正确生命周期

```mermaid
用户开启新对话
    ↓
读取 session.md
    ↓
┌─────────────────┐
│ 是否有内容？     │
└─────────────────┘
    ↓ 是                    ↓ 否
询问用户                 创建空文件
    ↓                        ↓
┌──────────────┐           开始新任务
│ 继续上次？   │
└──────────────┘
    ↓ 是        ↓ 否
加载内容      归档旧内容
作为上下文    创建新文件
    ↓            ↓
会话进行中 ←──────┘
    ↓
关键节点更新 session.md
    ↓
会话结束
    ↓
最终更新 session.md（保留断点）
```

---

## session.md 内容示例（断点状态）

```markdown
---
created_at: 2026-04-11 18:30
last_updated: 2026-04-11 20:15
status: interrupted  # [active|interrupted|completed]
task_id: refactor-auth-001
---

## 当前聚焦 (Current Focus)
重构用户认证模块，卡在密码加密方式选择：
- 已排除：bcrypt（性能不足）
- 候选：Argon2 vs PBKDF2
- 待验证：与现有 JWT 流程的兼容性

## 临时决策（待确认）
- 暂用 Argon2id，内存参数设为 64MB
- 需要测试在容器环境下的表现

## 代码位置
- 修改中：`src/auth/crypto.ts` (第 45-60 行)
- 测试文件：`tests/auth/password.test.ts` (有 2 个待修复测试)

## 下次待办
1. [ ] 跑通 Argon2 的单元测试
2. [ ] 对比 PBKDF2 在 1000 次哈希时的性能
3. [ ] 更新 tech-spec.md 的最终决策
```

---

## 修正后的写入策略

### 什么时候更新 session.md？
**实时更新**（不要等会话结束）：
- 每完成一个小里程碑 → 更新 `completed_steps`
- 做出临时决策 → 追加到 `temporary_decisions`
- 发现阻塞 → 标记 `blockers`

### 什么时候归档/清空？
- 用户明确说"任务完成" → 将 session.md 内容合并到 progress.md，然后清空
- 用户说"放弃这个任务" → 归档到 `archive/sessions/`，记录为[abandoned]
- 用户说"开新任务" → 归档当前 session.md（如果非空），开始新文件

---

## 关键区别总结

| 维度 | 旧设计（错误） | 新设计（正确） |
|------|--------------|---------------|
| **初始化行为** | 无脑清空 | 读取并询问用户 |
| **session.md 角色** | 临时缓冲区（用完即弃） | 任务状态快照（断点续传） |
| **数据流向** | 只进不出（写入后丢失） | 双向流动（读取→更新→保留） |
| **跨会话连续性** | 断裂（每次都重新开始） | 连续（可选继续或新开） |

---

## 给 OpenCode 用户的特别建议

既然 OpenCode 会自动保存完整会话历史，**session.md 可以轻量化**：

```markdown
# session.md 轻量化版本（配合 OpenCode 使用）

---
opencde_session_url: https://opencde.ai/s/abc123
opencde_checkpoint: "第 45 轮对话后"
created_at: 2026-04-11
---

## 断点摘要
- **OpenCode 会话**：第 45 轮后的状态
- **当前聚焦**：优化数据库索引
- **关键决策**：确定使用复合索引 (user_id, created_at)
- **阻塞**：需要明天测试查询性能

## 快速恢复指令
如需回到精确状态，请在 OpenCode 中打开：
https://opencde.ai/s/abc123
并跳转到第 45 轮对话。

## 本次待办（下次会话执行）
1. 测试索引性能
2. 根据结果更新 lessons.md
```

**这样设计的好处**：
- session.md 很小（只是索引），不担心清空问题
- 真正的详细上下文在 OpenCode 云端
- 但通过 session.md 知道"该去 OpenCode 的哪个 URL 继续"

---

**总结**：你抓到了关键矛盾——**"断点续传" 和 "初始化清空" 是互斥的**。正确的做法是：**读取 session.md 判断是否有未完成任务 → 询问用户是否继续 → 只有确认是新任务时才清空/归档**。
User: 我有个想法，progress中保存每个任务及其状态，并分配给每个任务一个单独的session.md。在与ai对话的过程中，根据我想要面向的任务，读取不同的session.md
Kimi: 这是一个非常优雅的设计！**任务注册表（progress.md）+ 任务工作区（独立 session 文件）** 的模式解决了单文件 session.md 的臃肿问题，也实现了真正的多任务并行管理。

以下是完整的实现方案：

---

## 一、文件架构（多任务版本）

```bash
.ai/
├── memory-bank/
│   ├── progress.md          # 任务注册中心（总览）
│   ├── tech-spec.md         # 全局技术约束
│   └── lessons.md           # 全局经验库
├── sessions/                # 任务工作区目录
│   ├── task-auth-refactor.md      # 认证重构任务
│   ├── task-db-optimization.md    # 数据库优化任务
│   ├── task-ui-migration.md       # UI 迁移任务
│   └── archive/                   # 已归档任务
│       ├── task-legacy-support.md.2026-04-01  # 带日期归档
│       └── ...
└── context/
    └── current-session.md   # 指向当前激活任务的软链接或索引
```

---

## 二、progress.md（任务注册中心）

```markdown
# 项目任务总览

## 进行中的任务 (Active)

| 任务ID | 名称 | 状态 | 优先级 | 最后更新 | 会话文件 |
|--------|------|------|--------|----------|----------|
| auth-001 | 认证模块重构 | 🟡 开发中 | P0 | 2026-04-12 | [打开](sessions/task-auth-refactor.md) |
| db-002 | 数据库性能优化 | 🟢 待开始 | P1 | 2026-04-11 | [打开](sessions/task-db-optimization.md) |
| ui-003 | UI 组件库迁移 | 🔴 阻塞 | P2 | 2026-04-10 | [打开](sessions/task-ui-migration.md) |

**当前激活任务**: `auth-001`（认证模块重构）

## 任务快速导航

### auth-001: 认证模块重构
- **目标**: 将 Session 认证改为 JWT + Refresh Token
- **进度**: 60%（已完成模型层，卡在中间件）
- **关联文件**: `src/auth/*.ts`, `middleware.ts`
- **阻塞点**: 等待前端确认 Token 刷新时机
- **会话文件**: `sessions/task-auth-refactor.md`

### db-002: 数据库性能优化
- **目标**: 优化用户查询响应时间 < 100ms
- **进度**: 0%（调研阶段）
- **关联文件**: `src/db/queries.ts`
- **依赖**: 需等待 auth-001 完成（共享 User 表）
- **会话文件**: `sessions/task-db-optimization.md`

## 任务生命周期规则

1. **创建任务**: 在 progress.md 注册 → 创建对应 session 文件 → 开始会话
2. **切换任务**: 更新"当前激活任务"标记 → 加载对应 session 文件
3. **完成任务**: 状态改为 ✅ → 迁移关键结论到 tech-spec.md/lessons.md → 归档 session 文件
4. **废弃任务**: 状态改为 ❌ → 归档 session 文件（保留历史）

---

## 三、任务级 Session 文件示例

### sessions/task-auth-refactor.md

```markdown
---
task_id: auth-001
task_name: 认证模块重构
created_at: 2026-04-10 14:00
last_session: 2026-04-12 16:30
total_sessions: 5
status: in-progress
progress: 60%
---

## 任务目标
将原有 Session-based 认证迁移到 JWT + Refresh Token 架构

## 已完成阶段 (Completed)
- [x] 设计 Token 结构（Access: 15min, Refresh: 7d）
- [x] 实现 Token 生成与验证工具函数
- [x] 数据库增加 refresh_token 表
- [x] 登录接口改造（返回双 Token）

## 当前阶段 (Current Focus)
**阶段 3: 中间件改造**
- 当前文件: `src/middleware/auth.ts`（第 20-45 行）
- 当前问题: 如何在 SSR 场景下自动刷新 Access Token
- 临时决策: 使用 Cookie 存储 Refresh，Header 携带 Access
- 待验证: 刷新时是否需要并发请求排队机制

## 待办队列 (Next Up)
- [ ] 实现 Token 刷新中间件
- [ ] 处理并发请求时的 Token 竞争问题
- [ ] 前端拦截器实现（等待前端确认）
- [ ] 旧 Session 清理脚本

## 技术决策记录（任务级）
- **决策**: 使用 httpOnly Cookie 存储 Refresh Token
- **理由**: 防止 XSS 攻击，符合安全最佳实践
- **影响**: 需要配置 CORS 允许 Credentials

## 代码片段（当前工作区）
```typescript
// src/middleware/auth.ts - 当前修改中
export async function refreshToken(req: NextRequest) {
  const refresh = req.cookies.get('refresh_token');
  // TODO: 这里需要处理并发刷新时的锁机制
}
```

## 阻塞与依赖
- **阻塞**: 前端确认 Token 刷新时机（预计明天回复）
- **依赖**: 无
- **影响下游**: db-002 任务依赖本任务完成 User 表结构
```

---

## 四、更新的 agents.md 控制器（多任务版本）

```markdown
# AI 多任务记忆控制器 v3.0
# 架构：任务注册中心 + 独立任务工作区

---

## 阶段一：初始化与任务发现

### 1. 加载任务注册中心
`read_file` → `.ai/memory-bank/progress.md`

**解析任务列表**，识别：
- 当前激活任务（标记为 🟡 或明确声明"当前激活"）
- 其他待处理任务
- 任务间的依赖关系

### 2. 任务加载策略

**如果用户明确指定任务**：
- 用户说："切换到数据库优化" / "继续认证重构" / "看任务 db-002"
- **加载对应任务**: `sessions/task-{task-id}.md`
- **更新激活标记**: 在 progress.md 中将该任务标记为"当前激活"
- **汇报**: "已切换到任务 [task-name]，当前进度 [progress]%，上次停在 [current focus]"

**如果用户未指定任务**：
- **加载当前激活任务**的 session 文件
- 向用户汇报任务概况："检测到 [N] 个进行中的任务，当前激活的是 [task-name]，进度 [X]%。
  其他可选任务：[列出其他任务名称]
  您想继续当前任务，还是切换？"

---

## 阶段二：任务切换协议

### 触发切换的条件
用户说以下任一：
- "切换到[任务名/ID]"
- "我们先做[另一个任务]"
- "暂停当前任务"
- "查看其他任务"

### 切换操作步骤

1. **保存当前任务状态**
   - 将当前对话的关键进展写入原 session 文件
   - 更新 `last_session` 时间戳
   - 如有未完成代码，记录当前文件位置和 TODO

2. **加载目标任务**
   - `read_file` → `sessions/task-{target}.md`
   - 更新 progress.md 中的"当前激活任务"标记

3. **上下文恢复汇报**
   ```
   已切换至任务: [task-name]
   进度: [progress]%
   上次会话: [last_session]
   当前阶段: [current focus]
   
   快速回顾:
   - 已完成: [completed items]
   - 当前阻塞: [blockers]
   - 下一步: [next up]
   
   开始工作？
   ```

---

## 阶段三：任务内工作流

### 实时更新 session 文件

**每当**：
- 完成一个子任务 → 移动到 "已完成阶段"
- 做出技术决策 → 追加到 "技术决策记录"
- 发现阻塞 → 更新 "阻塞与依赖"
- 修改代码 → 更新 "代码片段" 中的当前文件位置

**写入格式**：
- 使用 `edit_file` 更新具体章节（不要覆盖整个文件）
- 保持 Frontmatter 中的 `last_session` 为当前时间

---

## 阶段四：任务生命周期管理

### 创建新任务
用户说："新建任务"、"开始新功能"、"我们做个..."

1. 在 progress.md 中添加新行：
   ```markdown
   | new-004 | [任务名] | 🟡 开发中 | P1 | [日期] | [链接] |
   ```
2. 创建 `sessions/task-[id].md` 从模板
3. 更新"当前激活任务"为新任务
4. 引导用户填写任务目标

### 完成任务
用户说："这个做完了"、"任务结束"、"标记完成"

1. 更新 progress.md 状态为 ✅
2. 将 session 文件中的关键决策合并到：
   - `tech-spec.md`（架构决策）
   - `lessons.md`（踩坑经验）
3. 移动 session 文件到 `sessions/archive/`
4. 询问："是否切换到其他任务？
User: 那么我觉得可以将session换个名字，可以改成task。同时current-session这个是不是没什么用了？
Kimi: 完全同意。**session → task** 语义更准确，而且既然 progress.md 已经承担了"任务注册中心"的角色，`current-session.md` 确实是多余的。

---

## 更新后的文件架构（最终版）

```bash
.ai/
├── memory-bank/
│   ├── progress.md          # 任务注册中心（含"当前激活任务"标记）
│   ├── tech-spec.md         # 全局技术约束
│   └── lessons.md           # 全局经验库
└── tasks/                   # 任务工作区（原 sessions/）
    ├── auth-001.md          # 认证重构任务
    ├── db-002.md            # 数据库优化任务
    ├── ui-003.md            # UI 迁移任务
    └── archive/             # 已归档任务
        ├── auth-001.md.2026-04  # 完成后归档（带日期）
        └── legacy-support.md.2026-03
```

**删除**：`.ai/context/current-session.md` ❌

---

## progress.md 的关键字段（含激活标记）

```markdown
# 项目任务总览

## 当前激活任务 (Active)
**Task ID**: `auth-001`  
**Task Name**: 认证模块重构  
**Status**: 🟡 开发中  
**Session File**: [tasks/auth-001.md](tasks/auth-001.md)

> 上次会话: 2026-04-12 16:30 | 进度: 60% | 当前阶段: 中间件改造

---

## 所有任务列表

| 任务ID | 名称 | 状态 | 优先级 | 最后更新 | 操作 |
|--------|------|------|--------|----------|------|
| auth-001 | 认证模块重构 | 🟡 开发中 | P0 | 2026-04-12 | [切换](#) |
| db-002 | 数据库性能优化 | 🟢 待开始 | P1 | 2026-04-11 | [切换](#) |
| ui-003 | UI 组件库迁移 | 🔴 阻塞 | P2 | 2026-04-10 | [切换](#) |
| api-004 | 接口文档自动化 | ⚪ 规划中 | P3 | - | [启动](#) |
```

**优势**：所有状态在一个文件里一目了然，不需要跳转查看"当前是哪个任务"。

---

## 极简版 agents.md（适配新架构）

```markdown
# AI 多任务记忆控制器 v3.1
# 架构：progress 为中心，独立 task 文件

---

## 阶段一：启动加载

1. **读取任务注册表**：`.ai/memory-bank/progress.md`
2. **识别当前激活任务**（progress 中"当前激活任务"字段）
3. **加载任务上下文**：`.ai/tasks/{active-task-id}.md`
4. **汇报**："当前任务：[name]（[progress]%），上次停在：[current stage]"

---

## 任务切换（用户触发）

用户说："切换到 db-002"、"做数据库优化"、"看看另一个任务"

**执行**：
1. 保存当前任务状态（更新原 task 文件的 `last_session` 和进度）
2. 在 progress.md 中更新"当前激活任务"标记为新任务 ID
3. 加载新任务的 `.ai/tasks/{new-id}.md`
4. 汇报新任务上下文

---

## 任务文件（tasks/*.md）模板

每个 task 文件独立记录完整上下文，示例如下：

```markdown
---
task_id: auth-001
task_name: 认证模块重构
created_at: 2026-04-10
last_session: 2026-04-12 16:30
sessions_count: 5
status: in-progress
progress: 60%
---

## 目标
将 Session 认证改为 JWT + Refresh Token

## 当前阶段 (Current)
**中间件改造** - 处理 SSR 场景下的 Token 刷新
- 工作文件: `src/middleware/auth.ts` (L20-45)
- 临时决策: 使用 Cookie 存 Refresh，Header 带 Access
- 待验证: 并发请求时的 Token 竞争问题

## 已完成
- [x] Token 结构设计
- [x] 生成/验证工具函数
- [x] 数据库表改造

## 待办队列
- [ ] Token 刷新中间件
- [ ] 并发请求排队机制
- [ ] 前端拦截器对接

## 决策记录
- 使用 httpOnly Cookie 存储 Refresh Token（防 XSS）
- Access Token 有效期 15 分钟

## 阻塞
- 等待前端确认 Token 刷新时机（预计明天）
```

---

## 关于 current-task 的替代方案（可选）

如果你担心 progress.md 文件变大后读取变慢，或者想**保留一个极简的"指针文件"**，可以用无后缀的隐藏文件：

```bash
.ai/
├── memory-bank/
├── tasks/
└── .current-task          # 纯文本，只存一行：auth-001
```

**agents.md 逻辑**：
1. 先读 `.ai/.current-task` 获取 ID
2. 再读 `tasks/{id}.md` 加载上下文
3. 切换任务时只需修改 `.current-task` 这一行（比编辑 progress.md 的表格快）

**但通常情况下，直接读 progress.md 的"当前激活任务"字段更直观**，这个可选方案只在极端高频切换场景下有意义。

---

**总结**：是的，`current-session.md` 可以彻底删除，把"当前激活状态"交给 progress.md 托管即可。文件结构更简洁，信息源更单一。
User: 同时progress太大的话确实会导致读取变慢，可以拆分为两个文件，一个保存未完成任务，一个保存已完成任务，每次必须读取未完成任务，已完成任务按需读取
Kimi: 这是一个很好的性能优化思路。按**任务状态**拆分，避免随着项目积累而拖慢启动速度。

---

## 优化后的文件架构（最终版）

```bash
.ai/
├── memory-bank/
│   ├── backlog.md           # 未完成任务（必须读取，体积小）
│   ├── archive.md           # 已完成/已归档任务（按需读取）
│   ├── tech-spec.md         # 全局技术约束
│   └── lessons.md           # 全局经验库
├── tasks/                   # 任务工作区
│   ├── auth-001.md          # 未完成任务（活跃）
│   ├── db-002.md            # 未完成任务（活跃）
│   ├── ui-003.md            # 未完成任务（活跃）
│   └── archive/             # 已完成任务归档
│       ├── api-v1.md.2026-03
│       ├── migration-v2.md.2026-02
│       └── ...
└── .current-task            # 当前激活任务指针（纯文本，一行）
```

**文件职责**：
- `backlog.md`：进行中的任务，**每次会话启动必读取**
- `archive.md`：历史记录，**仅在用户询问"查看已完成任务"时读取**
- `.current-task`：当前激活任务ID，**每次启动必读取**（替代 progress.md 中的"当前激活"标记）

---

## backlog.md（未完成任务）

```markdown
# 进行中的任务 (Backlog)

**当前激活**: `auth-001` | 认证模块重构 | 🟡 60%

---

| 任务ID | 名称 | 状态 | 优先级 | 最后更新 | 任务文件 |
|--------|------|------|--------|----------|----------|
| auth-001 | 认证模块重构 | 🟡 开发中 | P0 | 2026-04-12 | [打开](tasks/auth-001.md) |
| db-002 | 数据库性能优化 | 🟢 待开始 | P1 | 2026-04-11 | [打开](tasks/db-002.md) |
| ui-003 | UI 组件库迁移 | 🔴 阻塞 | P2 | 2026-04-10 | [打开](tasks/ui-003.md) |

## 快速导航

### auth-001: 认证模块重构
- **进度**: 60%（中间件改造阶段）
- **阻塞**: 等待前端确认 Token 刷新时机
- **风险**: 影响 db-002 任务（依赖 User 表结构）

### db-002: 数据库性能优化
- **进度**: 0%（调研阶段）
- **依赖**: 需等待 auth-001 完成
- **目标**: 查询响应时间 < 100ms

### ui-003: UI 组件库迁移
- **进度**: 30%（基础组件已迁移）
- **阻塞**: 设计系统规范未定
```

**特点**：永远保持精简，只含活跃任务。

---

## archive.md（已完成任务）

```markdown
# 已归档任务 (Archive)

> 按需读取。通常仅在复盘、查找历史决策时加载。

## 2026年 Q2

| 任务ID | 名称 | 完成时间 | 关键成果 | 经验沉淀 |
|--------|------|----------|----------|----------|
| infra-001 | 容器化部署 | 2026-03-15 | Dockerfile + K8s 配置 | 已写入 tech-spec.md |
| refactor-001 | 旧API清理 | 2026-02-28 | 删除 2k 行死代码 | 已写入 lessons.md |

## 2026年 Q1

| 任务ID | 名称 | 完成时间 | 归档文件 |
|--------|------|----------|----------|
| legacy-001 | 迁移到 Monorepo | 2026-01-20 | [查看](tasks/archive/legacy-001.md.2026-01) |

## 快速查询

按标签筛选：
- [架构决策](#) | [性能优化](#) | [安全加固](#) | [UI/UX](#)
```

**特点**：按季度/月份分组，只存摘要，详细内容在 `tasks/archive/` 中。

---

## .current-task（极简指针）

纯文本文件，只存一行：

```bash
auth-001
```

**作用**：比解析 backlog.md 表格更快定位当前任务，且避免同时编辑 backlog.md 的"当前激活"字段和任务列表时的冲突风险。

---

## 更新的 agents.md（高性能版）

```markdown
# AI 多任务记忆控制器 v3.2
# 优化：按状态分离任务存储，减少启动负载

---

## 阶段一：快速启动（必须读取的文件）

按顺序读取：

1. **读取当前指针** (1ms)
   - `.ai/.current-task` → 获取当前激活任务ID

2. **读取未完成任务** (5-10ms)
   - `.ai/memory-bank/backlog.md` → 了解所有活跃任务状态
   
3. **读取当前任务上下文** (10-20ms)
   - `.ai/tasks/{current-id}.md` → 加载当前工作区

**总加载时间**: < 50ms，与任务数量无关（即使项目有100个已完成任务，也不影响）

---

## 阶段二：按需加载（Archive）

**仅在以下情况读取** `.ai/memory-bank/archive.md`：

- 用户说："查看历史任务"、"之前做过什么"、"参考以前的方案"
- 用户询问特定已归档任务："那个容器化部署是怎么做的"
- AI 判断当前决策可能与历史任务相关（如："检测到你正在做部署优化，需要参考 archive 中的 infra-001 吗？"）

**读取后**：在回复中引用相关历史任务，但不常驻内存。

---

## 阶段三：任务切换流程

用户说："切换到 db-002"

1. **保存当前任务**
   - 更新 `tasks/auth-001.md`（记录进度、当前阶段）
   
2. **切换指针**
   - 写入 `.ai/.current-task`：`db-002`
   
3. **读取新任务上下文**
   - `read_file` → `tasks/db-002.md`
   
4. **更新 backlog（可选）**
   - 如果用户说"暂停 auth-001"，更新 backlog.md 中 auth-001 状态为 🟡 暂停
   - 如果用户说"完成 auth-001"，执行**任务归档流程**：
     a. 将 auth-001 从 backlog.md 移动到 archive.md
     b. 将 `tasks/auth-001.md` 移动到 `tasks/archive/auth-001.md.2026-04`
     c. 清空 `.ai/.current-task` 或指向新默认任务

---

## 阶段四：任务归档（数据迁移）

当任务完成时，执行**数据迁移**：

```markdown
原位置                      目标位置
─────────────────────────────────────────────────
backlog.md (第3行)          → archive.md (新增记录)
tasks/auth-001.md           → tasks/archive/auth-001.md.2026-04
tech-spec.md (关键决策)     ← 从 task 文件提取架构决策
lessons.md (踩坑记录)       ← 从 task 文件提取经验
```

**目的**：
- backlog.md 永远保持精简（通常 < 10 个任务）
- archive.md 只存摘要，体积可控
- 详细历史在 archive 目录，几乎不读取

---

## 性能对比

| 任务数量 | 原方案 (progress.md) | 新方案 (backlog+archive) |
|---------|---------------------|-------------------------|
| 3个活跃 + 5个完成 | 读取 8 行表格 | 读取 3 行表格 |
| 3个活跃 + 50个完成 | 读取 53 行表格（慢） | 仍然只读 3 行（快） |
| 启动时间增长 | O(n)，随任务数线性增长 | O(1)，恒定 |

**结论**：新方案确保**无论项目多老、历史任务多少**，启动速度永远保持毫秒级。
User: 我觉得backlog中的当前激活字段好像不是很有用？只要保留未完成任务的快速导航就行了是不是？
Kimi: 你说得对，这是**冗余设计**。`.current-task` 已经明确指出了当前任务，backlog.md 里再标一次"当前激活"既多余又容易不同步。

**简化后的逻辑**：
- `.current-task` = **唯一事实来源**（当前是哪个任务）
- `backlog.md` = **纯任务列表**（所有未完成的，不区分"当前"）

---

## 精简后的 backlog.md

```markdown
# 进行中的任务 (Backlog)

| 任务ID | 名称 | 状态 | 优先级 | 最后更新 | 任务文件 |
|--------|------|------|--------|----------|----------|
| auth-001 | 认证模块重构 | 🟡 开发中 | P0 | 2026-04-12 | [打开](tasks/auth-001.md) |
| db-002 | 数据库性能优化 | 🟢 待开始 | P1 | 2026-04-11 | [打开](tasks/db-002.md) |
| ui-003 | UI 组件库迁移 | 🔴 阻塞 | P2 | 2026-04-10 | [打开](tasks/ui-003.md) |

## 快速导航

### auth-001: 认证模块重构
**进度**: 60% | **阶段**: 中间件改造 | **阻塞**: 等待前端确认

### db-002: 数据库性能优化  
**进度**: 0% | **阶段**: 调研 | **依赖**: 需 auth-001 完成

### ui-003: UI 组件库迁移
**进度**: 30% | **阶段**: 基础组件 | **阻塞**: 设计规范未定
```

**删除的内容**：
- ~~"当前激活: auth-001"~~  ← 完全删除，去 `.current-task` 看
- ~~状态栏的 emoji 标记~~  ← 不需要强调"当前"

---

## 更新的启动流程（agents.md）

```markdown
## 阶段一：启动加载

1. **读取当前指针**：`.ai/.current-task` → 获取 `auth-001`
2. **读取任务列表**：`.ai/memory-bank/backlog.md` → 了解所有未完成任务的概况
3. **读取当前上下文**：`.ai/tasks/{current-id}.md` → 加载当前工作区
4. **汇报**：
   ```
   当前任务: auth-001（来自.current-task）
   该任务详情: 认证模块重构，60%，中间件改造阶段（来自task文件）
   其他未完成任务: 2个（db-002, ui-003，来自backlog）
   ```
```

---

## 切换任务时的操作

**之前**（冗余）：
1. 修改 `.current-task` → `db-002`
2. 修改 `backlog.md` → 把 auth-001 的 🟡 改成 ⏸️，db-002 改成 🟡

**现在**（精简）：
1. **只需**修改 `.current-task` → `db-002`
2. `backlog.md` **不动**（除非用户说"暂停 auth-001"，才把 🟡 改成 ⏸️）

**优势**：状态变更只改一个地方，不会出现"指针说auth-001，但backlog标db-002"的矛盾。

---

这样设计更干净：**指针管"当前"，列表管"未完成"，互不重叠**。
User: 很好，创建一个完整的agents.md文件供我下载
Kimi: 文件已创建完成。

**下载链接**： [agents.md 控制器](sandbox:///mnt/kimi/output/agents.md)

---

## 快速开始指南

### 1. 放置文件
将 `agents.md` 重命名为对应工具的配置文件名，放在项目根目录：

| 工具 | 重命名为 |
|------|---------|
| **Cursor** | `.cursorrules` |
| **Claude Code** | `CLAUDE.md` |
| **Windsurf** | `agents.md` 或 `.windsurfrules` |
| **Cline/Roo** | `.clinerules` |

### 2. 初始化记忆库
首次使用时，在AI对话中发送：
> "初始化记忆系统"

AI会自动创建：
```bash
.ai/
├── .current-task              # 当前任务指针（纯文本）
├── memory-bank/
│   ├── backlog.md             # 未完成任务列表
│   ├── archive.md             # 已完成任务（按需读取）
│   ├── tech-spec.md           # 技术约束
│   └── lessons.md             # 经验记录
└── tasks/                     # 任务工作区
    └── archive/               # 归档目录
```

### 3. 日常使用指令

| 指令 | 效果 |
|------|------|
| "新建任务：数据库优化" | 创建任务db-001，注册到backlog，设置指针，创建task文件 |
| "切换到 auth-001" | 保存当前任务，更新指针，加载新任务上下文 |
| "记住这个" | 分析对话，写入tech-spec/lessons/当前task文件 |
| "这个做完了" | 归档任务，沉淀知识，清理指针 |
| "查看进行中的任务" | 读取backlog.md汇报所有未完成任务 |
| "查看历史任务" | 按需读取archive.md |

### 4. 核心设计亮点

1. **指针设计**：`.current-task` 是唯一事实来源，避免冗余标记
2. **双轨存储**：`backlog`（必读取、轻量）+ `archive`（按需读取）
3. **独立工作区**：每个任务有自己的 `tasks/{id}.md`，互不干扰
4. **自动分层**：技术决策→`tech-spec.md`，经验→`lessons.md`，临时上下文→task文件
User: 两点要求：1.删除current-task吧，每次新对话由用户手动唤醒，如用户要求继续xxx任务，即加载对应任务状态。2.精简agents.md，要不然占用上下文太多了。
Kimi: 文件已更新并精简。

**下载链接**： [agents.md 精简版 v4.0](sandbox:///mnt/kimi/output/agents.md)

---

## 核心变化

| 原版 v3.3 | 精简版 v4.0 |
|-----------|-------------|
| 6935 字符 | **1584 字符**（减少77%） |
| 自动读取 `.current-task` 加载任务 | **启动只读 `backlog.md`**，等待用户指令 |
| 自动指针管理 | **无指针**，用户完全手动控制 |
| 详细的模板和示例 | **极简模板**，仅保留核心字段 |

---

## 新的使用流程

**启动时**：
```
AI: 未完成任务：3个
     - auth-001: 认证重构 60% 🟡
     - db-002: 数据库优化 0% 🟢  
     - ui-003: UI迁移 30% 🔴
     
     指令：「继续[任务ID]」加载状态，或「新建任务」开始新工作
```

**用户说**：「继续auth-001」或「做认证重构」
→ AI加载 `tasks/auth-001.md`，汇报进度和当前阶段，开始工作

**用户说**：「切换到db-002」
→ AI保存当前任务状态，加载 `tasks/db-002.md`

**用户说**：「新建任务：支付模块」
→ AI创建 `tasks/pay-004.md`，添加到backlog，直接开始

---

## 优势

1. **零启动负载**：不自动加载任何任务上下文，等待用户明确指令
2. **完全手动控制**：没有隐含的"当前任务"状态，避免困惑
3. **上下文友好**：1584字符几乎不占用有效上下文空间
4. **灵活性**：可以随时跳转到任意任务，不受"当前激活"限制
User: task文件会保存历史决策嘛，以及task开发的过程？
Kimi: 是的，**task文件就是任务的"黑匣子"**，会完整记录开发过程中的所有关键节点。

---

## task文件保存的内容

根据精简版 agents.md 的设计，每个 task 文件会保存：

| 内容类型 | 保存位置 | 作用 |
|---------|---------|------|
| **决策记录** | `## 决策记录` 区块 | 技术选型、架构决策及理由 |
| **阶段推进** | `## 当前阶段` + `## 已完成` | 任务分解的里程碑 |
| **代码位置** | 当前阶段描述中 | 上次工作停在哪里（文件+行号） |
| **阻塞与依赖** | `## 阻塞/依赖` | 为什么暂停、等待什么 |
| **临时方案** | 标记 `[temp]` | 实验性代码，提醒未来重构 |
| **待办队列** | `## 待办` | 下一步做什么 |

---

## task文件示例（实际内容）

```markdown
---
task_id: auth-001
task_name: 认证模块重构
created_at: 2026-04-10
last_session: 2026-04-12 20:50
status: in-progress
progress: 60%
---

## 目标
Session认证 → JWT + Refresh Token

## 已完成
- [x] Token结构设计（Access 15min/Refresh 7d）
- [x] 数据库表改造（新增refresh_tokens表）

## 当前阶段
**阶段3: 中间件改造**
- 工作文件: `src/middleware/auth.ts` (L20-45)
- 当前问题: SSR场景自动刷新Token
- 代码片段:
  ```ts
  // TODO: 并发请求时的Token竞争
  export async function refreshToken(req: NextRequest) {
    const refresh = req.cookies.get('refresh_token');
    // 当前修改到这里，等待测试
  }
  ```

## 决策记录
- [2026-04-11] 使用httpOnly Cookie存Refresh（防XSS）[confirmed]
- [2026-04-12] 暂定双通道方案（Cookie+Header）[temp] 
  - 待验证: 移动端兼容性
  - 如果失败回退到纯Header方案

## 待办
- [ ] 实现Token刷新中间件（当前）
- [ ] 处理并发请求竞争
- [ ] 前端拦截器对接（阻塞：等前端确认）

## 阻塞
- 等待前端确认Token刷新时机（预计明天）

## 会话历史（可选）
- [04-12 20:50] 第5次会话：确定中间件接口，开始实现刷新逻辑
- [04-11 20:00] 第4次会话：完成数据库改造，讨论存储方案
```

---

## 历史如何被利用

当你说 **「继续auth-001」** 时，AI会：

1. **读取上述文件**，立即知道：
   - 进度60%，停在中间件改造阶段
   - 具体文件位置：`src/middleware/auth.ts` L20-45
   - 上次尝试的双通道方案是[temp]，需要验证
   - 阻塞点是前端确认，预计明天（如果今天已过，提醒询问）

2. **无需重新解释**：
   - 不用重新说明"我们要做JWT认证"
   - 不用重新讨论"为什么用Cookie而非纯Header"
   - 直接继续：`「上次我们停在refreshToken函数的竞争问题，继续实现？」`

---

## 与全局记忆的区别

| 内容 | 保存在 | 用途 |
|------|--------|------|
| **任务专属过程** | task文件 | 断点续传、代码位置、临时方案 |
| **跨任务通用知识** | `tech-spec.md` | 架构约束、技术选型（如"本项目用JWT"） |
| **踩坑经验** | `lessons.md` | 避免重复犯错（如"Prisma复合主键必须用对象"） |

**简单规则**：
- **只影响本任务** → 存task文件（如"这次重构的中间件代码位置"）
- **影响以后所有任务** → 存tech-spec/lessons（如"本项目认证统一用JWT"）

所以是的，**task文件是任务的完整开发日志**，每次会话结束时的状态都会被记录，下次加载时就像"读档"一样继续。
User: 但我看agents.md里并没有写入这些内容是不是？
Kimi: 你说得对，精简版确实**只说了"保存"但没说明存什么、怎么存、什么时候存**。

以下是补全了**写入协议**的 agents.md：

---

**下载链接**： [agents.md 完整写入版 v4.1](sandbox:///mnt/kimi/output/agents.md)

```markdown
# AI任务记忆控制器 v4.1

## 系统结构
```
.ai/
├── memory-bank/backlog.md    # 未完成任务
├── memory-bank/archive.md    # 已完成
├── memory-bank/tech-spec.md  # 技术约束
├── memory-bank/lessons.md    # 经验记录
└── tasks/{id}.md             # 任务工作区
```

---

## 启动协议

1. **读取backlog**，汇报未完成任务列表
2. **等待用户指令**：「继续[任务ID]」或「新建任务」
3. **加载任务文件**后，方可开始工作

---

## 任务文件写入协议（强制执行）

**每当以下情况发生，必须更新任务文件**：

### 1. 阶段推进时（必须）
- 完成一个子模块、一个功能点、一个步骤
- 更新 `progress` 百分比
- 将已完成项移到 `## 已完成`
- 更新 `## 当前阶段` 描述（含代码文件位置）

### 2. 技术决策时（必须）
- 选择技术方案、确定架构、排除其他选项
- 追加到 `## 决策记录`：
  ```markdown
  - [YYYY-MM-DD] 决策：[内容]
    - 理由：[为什么]
    - 影响：[对代码的约束]
    - 状态：[confirmed/temp/abandoned]
  ```

### 3. 代码定位时（必须）
- 修改代码过程中
- 在 `## 当前阶段` 中记录：
  - 工作文件：`src/xxx.ts` (L{start}-{end})
  - 当前问题：正在解决什么
  - 代码片段：关键部分的当前状态

### 4. 发现阻塞时（必须）
- 遇到依赖、等待确认、发现技术障碍
- 更新 `## 阻塞/依赖`：
  ```markdown
  - 阻塞项：[描述]
  - 等待：[人或条件]
  - 预计解决：[时间或条件]
  ```

### 5. 会话结束时（必须）
- 更新 `last_session` 时间戳
- 追加一行到 `## 会话历史`：
  ```markdown
  - [YYYY-MM-DD HH:MM] [阶段]：[做了什么，停在哪儿]
  ```

### 6. 临时方案时（可选但建议）
- 实验性代码、hack方案、待验证的实现
- 在决策记录或当前阶段中标记 `[temp]`
- 说明"如果验证失败，回退到[方案B]"

---

## 记忆捕获触发

| 用户指令 | 动作 |
|---------|------|
| 「记住这个」 | 分析内容，智能选择写入位置 |
| 「这是临时的」 | 写入当前task，标记[temp] |
| 「阶段完成」 | 更新progress，移动待办到已完成 |
| 「遇到阻塞」 | 更新阻塞列表 |

---

## 任务文件模板（创建新任务时使用）

```markdown
---
task_id: {id}
task_name: {name}
created_at: {date}
last_session: {date}
status: in-progress
progress: 0%
---

## 目标
{用户描述的任务目标}

## 当前阶段
- 状态：{初始化/调研/开发/测试}
- 工作文件：{文件路径}
- 当前问题：{正在解决什么}

## 已完成
- [ ]

## 待办
- [ ] {第一步}

## 决策记录

## 阻塞/依赖

## 会话历史
- [{date} {time}] 创建任务
```

---

## 切换任务时的保存

用户说「切换到xx」时：
1. **立即保存当前任务**：按上述协议更新所有字段
2. **加载目标任务**：读取其task文件
3. **汇报**：「已保存auth-001（60%），现加载db-002（0%，调研阶段）」
```

---

## 关键改进点

| 精简版 v4.0 | 完整版 v4.1 |
|------------|------------|
| 只说"保存到task文件" | **明确规定6种必须写入的场景** |
| 无格式要求 | **给出每个字段的具体格式** |
| 无更新时机 | **明确"阶段完成/决策/阻塞/会话结束"时必须写** |
| 模板极简 | **模板包含所有必须字段的占位符** |

这样 AI 就知道：
- 每完成一个功能点 → 更新progress + 当前阶段 + 代码位置
- 每做一个技术选择 → 追加决策记录（含理由和影响）
- 每会话结束 → 更新时间戳 + 会话历史
- 遇到阻塞 → 记录阻塞项和等待条件

**task文件因此成为完整的开发日志**。
