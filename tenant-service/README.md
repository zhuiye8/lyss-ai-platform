# Lyss AI Platform - Tenant Service

租户管理服务：负责租户管理、用户管理、供应商凭证管理等核心业务数据操作。

## 🎯 服务概述

Tenant Service 是 Lyss AI Platform 的核心业务数据管理服务，提供以下功能：

- **租户管理**：租户的创建、配置和生命周期管理
- **用户管理**：用户注册、资料管理、状态控制  
- **供应商凭证管理**：AI供应商API密钥的加密存储和管理
- **工具配置管理**：租户级别的EINO工具开关配置
- **用户偏好管理**：个性化设置和记忆开关控制

## 🏗️ 技术栈

- **框架**：FastAPI + Python 3.11
- **数据库**：PostgreSQL + SQLAlchemy（异步）
- **加密**：pgcrypto（供应商凭证加密）
- **验证**：Pydantic v2
- **日志**：structlog（JSON格式）

## 🚀 快速开始

### 环境要求

- Python 3.11+
- PostgreSQL 14+（需要pgcrypto扩展）
- 虚拟环境（venv）

### 安装依赖

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 配置环境

复制并修改环境配置：

```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库连接和加密密钥
```

### 启动服务

```bash
# 使用开发脚本启动
python scripts/start_dev.py

# 或者直接使用uvicorn
uvicorn tenant_service.main:app --host 0.0.0.0 --port 8002 --reload
```

### 访问服务

- **API文档**：http://localhost:8002/docs
- **健康检查**：http://localhost:8002/health
- **服务信息**：http://localhost:8002/

## 📊 项目结构

```
tenant-service/
├── tenant_service/              # 主应用包
│   ├── core/                   # 核心组件
│   │   ├── database.py         # 数据库连接
│   │   ├── encryption.py       # pgcrypto加密
│   │   ├── security.py         # 安全组件
│   │   └── tenant_context.py   # 租户上下文
│   ├── models/                 # 数据模型
│   │   ├── database/           # SQLAlchemy模型
│   │   └── schemas/            # Pydantic模型
│   ├── routers/                # API路由
│   ├── services/               # 业务服务
│   ├── repositories/           # 数据访问层
│   ├── utils/                  # 工具模块
│   ├── config.py               # 配置管理
│   └── main.py                 # 应用入口
├── tests/                      # 测试
├── scripts/                    # 脚本
├── venv/                       # 虚拟环境
├── requirements.txt            # 依赖
└── .env                        # 环境配置
```

## 🔐 安全特性

### pgcrypto 加密存储

供应商API密钥使用PostgreSQL的pgcrypto扩展进行列级加密：

```sql
-- 加密存储
INSERT INTO supplier_credentials (encrypted_api_key) 
VALUES (pgp_sym_encrypt('sk-xxxxx', 'encryption_key'));

-- 解密读取
SELECT pgp_sym_decrypt(encrypted_api_key, 'encryption_key') 
FROM supplier_credentials;
```

### 多租户数据隔离

所有业务查询都包含tenant_id过滤，确保数据严格隔离：

```python
# 强制租户隔离的查询示例
SELECT * FROM users 
WHERE tenant_id = ? AND is_active = true;
```

### 密码安全

- 使用bcrypt进行密码哈希（12轮）
- 密码强度策略可配置
- 支持账户锁定机制

## 📡 API接口

### 健康检查

```http
GET /health
```

返回服务健康状态和依赖检查结果。

### 租户管理

```http
POST /api/v1/admin/tenants     # 创建租户
GET  /api/v1/admin/tenants     # 获取租户列表
PUT  /api/v1/admin/tenants/:id # 更新租户
```

### 用户管理

```http
POST /api/v1/admin/users       # 创建用户
GET  /api/v1/admin/users       # 获取用户列表  
PUT  /api/v1/admin/users/:id   # 更新用户
```

### 供应商凭证管理

```http
POST /api/v1/admin/suppliers     # 添加供应商凭证
GET  /api/v1/admin/suppliers     # 获取供应商列表
POST /api/v1/admin/suppliers/:id/test # 测试连接
```

### 内部服务接口

```http
POST /internal/users/verify     # 用户验证（Auth Service使用）
GET  /internal/tool-configs     # 工具配置（EINO Service使用）
```

## 🔧 开发工具

### 代码检查

```bash
# 类型检查
mypy tenant_service/

# 代码格式化
black tenant_service/
isort tenant_service/

# 代码检查
flake8 tenant_service/
```

### 测试

```bash
# 运行测试
pytest tests/ --cov=tenant_service

# 测试覆盖率报告
pytest tests/ --cov=tenant_service --cov-report=html
```

## 📝 环境变量

主要配置项：

```bash
# 服务配置
TENANT_SERVICE_PORT=8002
TENANT_SERVICE_HOST=0.0.0.0

# 数据库配置
DB_HOST=localhost
DB_USERNAME=lyss_user
DB_PASSWORD=your_password
DB_DATABASE=lyss_platform

# 加密密钥（⚠️ 生产环境必须使用强密钥）
PGCRYPTO_KEY=32字符以上的强加密密钥

# 密码策略
MIN_PASSWORD_LENGTH=8
REQUIRE_SPECIAL_CHARS=true
REQUIRE_NUMBERS=true
```

## ⚠️ 重要注意事项

1. **加密密钥安全**：生产环境的`PGCRYPTO_KEY`必须使用至少32字符的强随机密钥
2. **多租户隔离**：所有数据查询都必须包含tenant_id过滤
3. **API密钥保护**：供应商凭证绝不能以明文形式记录到日志
4. **权限验证**：所有管理操作都需要验证用户角色权限

## 📄 许可证

MIT License

## 🤝 贡献

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: 添加某项功能'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

---

**🔐 安全提醒**：Tenant Service管理平台最敏感的数据，包括用户信息和供应商凭证。任何修改都必须经过严格的安全审查和多租户隔离测试。