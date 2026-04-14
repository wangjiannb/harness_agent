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
