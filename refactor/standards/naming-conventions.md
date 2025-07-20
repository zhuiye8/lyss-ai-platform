# 命名规范标准

## 📋 文档概述

统一的命名规范，确保项目代码的一致性和可维护性。所有开发人员必须严格遵循。

---

## 🏗️ 服务命名规范

### **服务命名**
- **格式**: `lyss-{service-name}`
- **规则**: 小写字母，使用连字符分隔
- **示例**:
  ```bash
  ✅ 正确
  lyss-api-gateway
  lyss-auth-service
  lyss-user-service
  lyss-provider-service
  lyss-chat-service
  lyss-memory-service
  
  ❌ 错误
  LyssAPI
  auth_service
  tenantService
  CHAT-Service
  ```

### **目录命名**
- **格式**: 与服务名保持一致
- **规则**: 项目根目录下的服务目录必须与服务名一致
- **示例**:
  ```
  lyss-ai-platform/
  ├── lyss-api-gateway/
  ├── lyss-auth-service/
  ├── lyss-user-service/
  └── lyss-frontend/
  ```

---

## 🗄️ 数据库命名规范

### **数据库命名**
- **格式**: `lyss_{service}_db`
- **规则**: 小写字母，使用下划线分隔
- **示例**:
  ```sql
  ✅ 正确
  lyss_user_db
  lyss_provider_db
  lyss_chat_db
  lyss_memory_db
  
  ❌ 错误
  LyssUserDB
  lyss-user-db
  user_database
  ```

### **表命名**
- **格式**: `snake_case`，复数形式
- **规则**: 小写字母，使用下划线分隔，表示实体的复数
- **示例**:
  ```sql
  ✅ 正确
  users
  user_groups
  provider_channels
  conversation_messages
  user_memories
  
  ❌ 错误
  User
  userGroup
  provider-channels
  ConversationMessage
  ```

### **字段命名**
- **格式**: `snake_case`
- **规则**: 小写字母，使用下划线分隔，语义明确
- **特殊字段**:
  ```sql
  -- 主键
  id UUID PRIMARY KEY DEFAULT gen_random_uuid()
  
  -- 外键
  user_id UUID NOT NULL REFERENCES users(id)
  tenant_id UUID NOT NULL
  
  -- 审计字段
  created_at TIMESTAMP DEFAULT NOW()
  updated_at TIMESTAMP DEFAULT NOW()
  
  -- 状态字段
  status VARCHAR(20) DEFAULT 'active'
  ```

### **索引命名**
- **格式**: `idx_{table}_{columns}`
- **示例**:
  ```sql
  ✅ 正确
  CREATE INDEX idx_users_tenant_status ON users(tenant_id, status);
  CREATE INDEX idx_conversations_user_created ON conversations(user_id, created_at);
  
  ❌ 错误
  CREATE INDEX user_tenant_idx ON users(tenant_id);
  CREATE INDEX conversations_index ON conversations(user_id);
  ```

---

## 🌐 API命名规范

### **路由命名**
- **格式**: `/api/v{version}/{resource}`
- **规则**: 小写字母，使用连字符分隔，资源使用复数
- **示例**:
  ```
  ✅ 正确
  GET    /api/v1/users
  POST   /api/v1/users
  GET    /api/v1/users/{id}
  PUT    /api/v1/users/{id}
  DELETE /api/v1/users/{id}
  
  GET    /api/v1/provider-channels
  POST   /api/v1/conversations/{id}/messages
  
  ❌ 错误
  GET /api/User
  POST /users/create
  GET /api/v1/getUserById
  ```

### **请求/响应字段命名**
- **格式**: `camelCase` (JSON) 或 `snake_case` (内部)
- **规则**: 前端API使用camelCase，内部服务间使用snake_case
- **示例**:
  ```json
  // 前端API (camelCase)
  {
    "userId": "uuid",
    "fullName": "张三",
    "createdAt": "2025-01-20T10:30:00Z"
  }
  
  // 内部API (snake_case)
  {
    "user_id": "uuid",
    "full_name": "张三", 
    "created_at": "2025-01-20T10:30:00Z"
  }
  ```

---

## 🔧 环境变量命名规范

### **环境变量格式**
- **格式**: `{SERVICE}_{CATEGORY}_{NAME}`
- **规则**: 全大写字母，使用下划线分隔
- **示例**:
  ```bash
  ✅ 正确
  USER_SERVICE_DATABASE_URL=postgresql://...
  CHAT_SERVICE_REDIS_URL=redis://...
  API_GATEWAY_JWT_SECRET=secret
  PROVIDER_SERVICE_ENCRYPTION_KEY=key
  
  ❌ 错误
  userServiceDatabaseUrl=...
  chat-service-redis-url=...
  api_gateway_jwt_secret=...
  ```

### **分类标准**
```bash
# 数据库相关
{SERVICE}_DATABASE_URL
{SERVICE}_DATABASE_POOL_SIZE

# 缓存相关  
{SERVICE}_REDIS_URL
{SERVICE}_REDIS_PASSWORD

# 安全相关
{SERVICE}_JWT_SECRET
{SERVICE}_ENCRYPTION_KEY

# 外部服务
{SERVICE}_{EXTERNAL_SERVICE}_URL
{SERVICE}_{EXTERNAL_SERVICE}_API_KEY

# 应用配置
{SERVICE}_PORT
{SERVICE}_LOG_LEVEL
{SERVICE}_DEBUG
```

---

## 💻 代码命名规范

### **Python命名规范**

#### **模块和包**
```python
# 模块名：小写字母，下划线分隔
user_service.py
auth_middleware.py
database_models.py

# 包名：小写字母，避免下划线
models/
services/
repositories/
```

#### **类命名**
```python
✅ 正确
class UserService:
    pass

class ProviderChannelRepository:
    pass

class AuthMiddleware:
    pass

❌ 错误
class user_service:
    pass

class providerchannelrepository:
    pass
```

#### **函数和变量**
```python
✅ 正确
def create_user(user_data: dict) -> User:
    pass

def get_available_channels(tenant_id: str) -> List[Channel]:
    pass

user_email = "user@example.com"
channel_config = {"priority": 1}

❌ 错误
def CreateUser(userData):
    pass

def getAvailableChannels():
    pass

UserEmail = "user@example.com"
```

#### **常量**
```python
✅ 正确
MAX_RETRY_COUNT = 3
DEFAULT_PAGE_SIZE = 20
API_VERSION = "v1"
SUPPORTED_PROVIDERS = ["openai", "anthropic", "deepseek"]

❌ 错误
max_retry_count = 3
defaultPageSize = 20
```

### **Go命名规范**

#### **包命名**
```go
✅ 正确
package handlers
package services
package models

❌ 错误
package chatHandlers
package user_services
```

#### **类型命名**
```go
✅ 正确
type User struct {
    ID       string `json:"id"`
    Email    string `json:"email"`
    FullName string `json:"full_name"`
}

type ChatService interface {
    ProcessMessage(ctx context.Context, req *ChatRequest) (*ChatResponse, error)
}

❌ 错误
type user struct {
    id       string
    email    string
    fullName string
}
```

#### **函数命名**
```go
✅ 正确
func NewChatService() *ChatService {
    return &ChatService{}
}

func (s *ChatService) ProcessMessage(ctx context.Context, req *ChatRequest) (*ChatResponse, error) {
    // implementation
}

❌ 错误
func newChatService() *ChatService {
    return &ChatService{}
}

func (s *ChatService) processMessage(ctx context.Context, req *ChatRequest) (*ChatResponse, error) {
    // implementation
}
```

### **TypeScript/React命名规范**

#### **组件命名**
```typescript
✅ 正确
// 组件使用PascalCase
const UserLoginForm: React.FC = () => {
    return <div>Login Form</div>;
};

const ChatMessageBubble: React.FC<ChatMessageProps> = ({ message }) => {
    return <div>{message.content}</div>;
};

❌ 错误
const userLoginForm = () => {
    return <div>Login Form</div>;
};

const chat_message_bubble = () => {
    return <div>Message</div>;
};
```

#### **文件命名**
```typescript
✅ 正确
// 组件文件：PascalCase
UserLoginForm.tsx
ChatMessageBubble.tsx
AdminLayout.tsx

// 非组件文件：camelCase
authService.ts
userStore.ts
apiConstants.ts

❌ 错误
userLoginForm.tsx
chat_message_bubble.tsx
auth-service.ts
```

#### **变量和函数**
```typescript
✅ 正确
const currentUser = useUser();
const conversationHistory = useConversationHistory();

const handleUserLogin = (credentials: LoginCredentials) => {
    // implementation
};

const validateEmailFormat = (email: string): boolean => {
    // implementation
};

❌ 错误
const CurrentUser = useUser();
const conversation_history = useConversationHistory();

const HandleUserLogin = (credentials) => {
    // implementation
};
```

---

## 📁 文件和目录命名规范

### **配置文件**
```bash
✅ 正确
docker-compose.yml
docker-compose.dev.yml
docker-compose.prod.yml
.env.example
.env.development
.env.production

❌ 错误
DockerCompose.yml
docker_compose.yml
env.example
.env_development
```

### **脚本文件**
```bash
✅ 正确
start-dev.sh
health-check.sh
backup-db.sh
migrate-database.py

❌ 错误
startDev.sh
health_check.sh
BackupDB.sh
```

### **文档文件**
```bash
✅ 正确
README.md
CHANGELOG.md
API_REFERENCE.md
user-guide.md
deployment-guide.md

❌ 错误
readme.md
change_log.md
api_reference.md
UserGuide.md
```

---

## 🔍 命名检查清单

### **代码提交前检查**
- [ ] 服务名使用 `lyss-{service-name}` 格式
- [ ] 数据库和表名使用 `snake_case`
- [ ] API路由使用小写字母和连字符
- [ ] 环境变量使用 `{SERVICE}_{CATEGORY}_{NAME}` 格式
- [ ] Python类名使用 `PascalCase`
- [ ] Python函数名使用 `snake_case`
- [ ] Go类型名使用 `PascalCase`
- [ ] Go函数名遵循Go惯例
- [ ] React组件使用 `PascalCase`
- [ ] TypeScript变量使用 `camelCase`

### **工具辅助检查**
```bash
# Python命名检查
pylint --disable=all --enable=invalid-name your_file.py

# Go命名检查
golangci-lint run --enable=golint

# TypeScript命名检查
eslint --rule "@typescript-eslint/naming-convention: error" src/
```