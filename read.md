# 角色与最终目标 (Role & Ultimate Goal)

你是一位经验丰富的首席工程师（Principal Engineer），你的核心任务是为“Lyss AI Platform”项目制定一套全面、严格且清晰的开发规范。这套规范将作为项目所有团队成员（包括AI编程助手）必须遵守的“根本大法”，旨在确保代码质量、提升开发效率、降低维护成本。

你的最终产出应该是一个名为 `STANDARDS.md` 的单一、格式精美的Markdown文件。此文件应内容完整、结构清晰，可以直接提交到项目的代码仓库根目录。

---

# 背景与核心上下文 (Background & Core Context)

* **项目名称：** Lyss AI Platform
* **项目愿景：** 一个企业级的AI服务聚合与管理平台。
* **核心架构：** 微服务架构。
* **已知服务列表：**
    * `Frontend`: (React, Ant Design) - 前端用户界面。
    * `API Gateway`: (Python, FastAPI) - 所有请求的统一入口。
    * `Auth Service`: (Python, FastAPI) - 负责认证和JWT。
    * `Tenant Service`: (Python, FastAPI) - 负责租户、用户和供应商凭证管理。
    * `EINO Service`: (Go) - 负责AI工作流编排。
    * `Memory Service`: (Python, FastAPI) - 负责对话记忆和Mem0AI集成。
* **数据库技术：** PostgreSQL, Redis。

---

# 具体任务：生成 `docs/STANDARDS.md` 文件

请根据以下大纲，为“Lyss AI Platform”项目编写一份详尽的 `STANDARDS.md` 开发规范文档。

---
# Lyss AI Platform 开发规范总纲 (STANDARDS.md)

## 1. 全局命名规范 (Global Naming Conventions)

### 1.1. 服务与仓库 (Services & Repositories)
* **格式：** 采用小写kebab-case（短横线连接）。
* **示例：** `lyss-api-gateway`, `lyss-eino-service`。

### 1.2. 数据库 (Database)
* **表名 (Tables):** 小写snake_case（下划线连接），使用复数形式。示例：`users`, `supplier_credentials`。
* **列名 (Columns):** 小写snake_case。示例：`user_id`, `created_at`。
* **索引名 (Indexes):** `idx_<table_name>_<column_names>`。示例：`idx_users_email`。

### 1.3. API
* **路径 (Paths):** 小写kebab-case，资源名用复数。示例：`/api/v1/tenant-users`。
* **查询参数 (Query Params):** 小写snake_case。示例：`?user_id=123&page_size=10`。

### 1.4. 代码变量 (Code Variables)
* **Python:** `snake_case`。
* **Go:** `camelCase`。
* **TypeScript/JavaScript:** `camelCase`。

### 1.5. 环境变量 (Environment Variables)
* **格式：** 大写 `SCREAMING_SNAKE_CASE`，并以服务名作为前缀。
* **示例：** `API_GATEWAY_PORT=8000`, `MEMORY_SERVICE_MEM0_LLM_PROVIDER=...`。

## 2. API 设计与响应规范 (API Design & Response Standards)

### 2.1. 通用原则
* **协议：** 所有API必须使用HTTPS。
* **版本：** API版本必须在URL路径中体现，如 `/api/v1/`。
* **认证：** 所有需要认证的接口，必须通过 `Authorization: Bearer <JWT>` 请求头进行。
* **请求体/响应体：** 必须使用JSON格式。

### 2.2. 成功响应结构 (Success Response)
* 所有 `2xx` 状态码的响应体，必须遵循以下结构：
    ```json
    {
      "success": true,
      "data": <any>,
      "request_id": "string (UUID)",
      "timestamp": "string (ISO 8601)"
    }
    ```

### 2.3. 失败响应结构 (Error Response)
* 所有 `4xx` 和 `5xx` 状态码的响应体，必须遵循以下结构：
    ```json
    {
      "success": false,
      "error": {
        "code": "string (e.g., 2001)",
        "message": "string (Human-readable error description)"
      },
      "request_id": "string (UUID)",
      "timestamp": "string (ISO 8601)"
    }
    ```

### 2.4. 分页 (Pagination)
* 对于返回列表的GET请求，必须支持分页。
* **请求参数：** `page` (页码, 从1开始) 和 `page_size` (每页数量)。
* **响应结构：** `data` 字段应为以下结构：
    ```json
    {
      "items": [<any>],
      "pagination": {
        "page": 1,
        "page_size": 20,
        "total_items": 150,
        "total_pages": 8
      }
    }
    ```

## 3. 统一错误代码规范 (Unified Error Code Standards)

* **1000-1999: 通用错误** (如：`1001: INVALID_INPUT`)
* **2000-2999: 认证与授权错误** (如：`2001: UNAUTHORIZED`, `2002: TOKEN_EXPIRED`)
* **3000-3999: 业务逻辑错误** (如：`3001: TENANT_NOT_FOUND`, `3002: USER_ALREADY_EXISTS`)
* **4000-4999: 外部服务错误** (如：`4001: AI_PROVIDER_ERROR`, `4002: MEMORY_SERVICE_UNAVAILABLE`)
* **5000-5999: 内部系统与数据错误** (如：`5001: DATABASE_ERROR`, `5002: CACHE_ERROR`)

## 4. 数据库设计规范 (Database Design Standards)

### 4.1. 表设计 (Table Design)
* **主键：** 每个表必须有主键，推荐使用UUID类型，命名为`id`。
* **时间戳：** 每个表必须包含 `created_at` 和 `updated_at` 两个时间戳字段，并由数据库自动管理。
* **外键：** 必须定义明确的外键约束和级联操作（如 `ON DELETE SET NULL`）。
* **多租户隔离：** 任何存储在**共享数据库**中的表，**必须**包含一个非空的 `tenant_id` 字段。所有对这些表的查询**必须**在WHERE子句中包含 `tenant_id` 过滤。

### 4.2. 索引 (Indexing)
* 所有外键字段必须建立索引。
* 经常用于查询、排序、连接的字段必须建立索引。

## 5. 日志与追踪规范 (Logging & Tracing Standards)

### 5.1. 日志格式
* 所有服务的所有日志输出，**必须**为**结构化JSON**格式。

### 5.2. 日志内容
* 每一条日志记录，**必须**包含以下字段：
    * `timestamp`: 日志时间 (ISO 8601)
    * `level`: 日志级别 (`DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`)
    * `service`: 服务名称 (如 `lyss-api-gateway`)
    * `request_id`: 全链路追踪ID (从 `X-Request-ID` 请求头获取)
    * `message`: 日志核心信息
    * `data`: (可选) 包含附加上下文信息的对象

### 5.3. 日志规范
* **严禁**在日志中以明文形式记录任何敏感信息（密码、API Key、PII等）。
* `INFO`级别用于记录关键业务流程节点。
* `ERROR`级别用于记录所有捕获到的、需要关注的异常。

## 6. 代码提交与版本控制规范 (Code Submission & Version Control Standards)

### 6.1. 分支模型 (Branching Model)
* 采用简化的GitFlow模型：
    * `main`: 生产环境分支，受保护。
    * `develop`: 开发主分支，所有功能分支的合并目标。
    * `feature/<feature-name>`: 功能开发分支，从`develop`创建。
    * `hotfix/<fix-name>`: 紧急生产修复分支，从`main`创建。

### 6.2. 提交信息 (Commit Messages)
* **必须**遵循**Conventional Commits**规范。
* **格式：** `<type>(<scope>): <subject>`
* **示例：**
    * `feat(auth): add JWT refresh token endpoint`
    * `fix(eino): correct tool node execution order`
    * `docs(standards): update database naming conventions`
    * `refactor(tenant): simplify user creation logic`

## 7. 环境与配置管理规范 (Environment & Configuration Management Standards)

### 7.1. 环境定义
* `local`: 本地开发环境。
* `development`: 共享的开发/测试环境。
* `staging`: 预生产环境。
* `production`: 生产环境。

### 7.2. 配置与密钥
* **严禁**将任何包含密钥或敏感配置的文件（如 `.env`）提交到Git仓库。
* 本地开发（`local`）使用 `.env` 文件进行配置。
* 所有其他环境（`development`, `staging`, `production`）的配置和密钥，**必须**通过环境变量或专用的密钥管理服务（如HashiCorp Vault, AWS KMS）在运行时注入。
---