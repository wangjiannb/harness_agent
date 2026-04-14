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
