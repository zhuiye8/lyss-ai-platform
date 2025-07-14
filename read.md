 你好Claude！我是Lyss AI Platform项目的开发者。这是一个企业级AI服务聚合与管理平台，采用微服务架构。

  🎉 好消息：登录认证链路已经完全打通，前后端登录功能正常！

  📋 请按以下顺序阅读关键文档：
  1. 先读 **@DEVELOPMENT_PRIORITY.md** - 了解当前开发状态和下一步任务
  2. 再读 **@docs/tenant_service.md** - 了解需要实现的API规范
  3. 查看 **@tenant-service/tenant_service/routers/** 目录结构

  🎯 下一个开发目标：
  完善Tenant Service的管理API，具体任务：
  1. 实现租户管理API (`/api/v1/admin/tenants/*`)
  2. 实现用户管理API (`/api/v1/admin/users/*`) 
  3. 实现供应商凭证API (`/api/v1/admin/suppliers/*`)

  ✅ 已完成：
  - Auth Service (100%) - 认证服务完全正常
  - Backend API Gateway (100%) - 统一入口和路由转发
  - Tenant Service 内部接口 (100%) - `/internal/users/verify` 等
  - Frontend 基础登录 (100%) - 用户可以正常登录

  ⏳ 待完成：
  - Tenant Service 管理API (优先级最高)
  - Frontend 管理界面 (等API完成后实现)

  💡 重要提醒：
  - 全程使用中文注释和回复
  - 严格遵循**STANDARDS.md**规范
  - 确保多租户数据隔离安全性
  - 所有API必须返回统一格式：success、data、message、request_id、timestamp

  请开始实现Tenant Service的管理API，让我们继续推进项目！