---
task_id: auth-001
updated_at: 2026-04-13 15:30
---

focus:
  file: src/auth/middleware.ts
  line: 45
  function: verifyToken
  snippet: const payload = jwt.verify(token, secret)

context:
  - file: src/auth/service.ts
    lines: 120-135
    relation: callee
    note: 被 verifyToken 调用的验证逻辑
    status: stable

next_action: 修复 verifyToken 的 TS 类型报错
blocker: ~
