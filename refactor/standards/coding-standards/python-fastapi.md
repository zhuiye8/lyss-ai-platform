# Python编码规范 (FastAPI)

## 📋 文档概述

Python和FastAPI项目的专用编码规范，确保代码质量和一致性。

---

## 🐍 Python编码规范 (FastAPI)

### **文件头注释**
```python
"""
用户服务 - 用户管理相关业务逻辑

该模块负责处理用户的注册、登录、权限管理等核心功能。
包含用户信息的CRUD操作和租户隔离逻辑。

Author: Lyss AI Team
Created: 2025-01-20
Modified: 2025-01-20
"""
```

### **导入顺序规范**
```python
# 1. 标准库导入
import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

# 2. 第三方库导入
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import Column, String, DateTime
from redis import Redis

# 3. 本地导入
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService
```

### **类定义规范**
```python
class UserService:
    """
    用户服务类
    
    负责处理用户相关的业务逻辑，包括用户注册、登录验证、
    权限管理等功能。确保多租户数据隔离。
    """
    
    def __init__(self, db_session, redis_client: Redis):
        """
        初始化用户服务
        
        Args:
            db_session: 数据库会话对象
            redis_client: Redis客户端对象
        """
        self.db = db_session
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
    
    async def create_user(self, user_data: UserCreate, tenant_id: str) -> UserResponse:
        """
        创建新用户
        
        Args:
            user_data: 用户创建数据，包含邮箱、密码等信息
            tenant_id: 租户ID，用于数据隔离
            
        Returns:
            UserResponse: 创建成功的用户信息
            
        Raises:
            HTTPException: 当邮箱已存在或数据验证失败时抛出
        """
        try:
            # 检查邮箱是否已存在（在同一租户内）
            existing_user = await self._get_user_by_email(
                email=user_data.email, 
                tenant_id=tenant_id
            )
            if existing_user:
                self.logger.warning(f"尝试创建已存在的用户: {user_data.email}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="该邮箱已被注册"
                )
            
            # 创建用户逻辑
            user = await self._create_user_in_db(user_data, tenant_id)
            
            # 缓存用户信息
            await self._cache_user_info(user)
            
            self.logger.info(f"成功创建用户: {user.email}")
            return UserResponse.from_orm(user)
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"创建用户失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="用户创建失败"
            )
```

### **API路由规范**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_current_user, get_tenant_context

router = APIRouter(prefix="/api/v1/users", tags=["用户管理"])

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_context),
    user_service: UserService = Depends(get_user_service)
):
    """
    创建新用户
    
    创建一个新的用户账户。只有租户管理员才能执行此操作。
    
    Args:
        user_data: 用户创建信息
        current_user: 当前登录用户（通过JWT获取）
        tenant_id: 租户ID（从JWT中提取）
        user_service: 用户服务实例
        
    Returns:
        UserResponse: 创建的用户信息
        
    Raises:
        HTTPException 403: 权限不足
        HTTPException 409: 邮箱已存在
        HTTPException 422: 数据验证失败
    """
    # 权限检查
    if current_user.role not in ["super_admin", "tenant_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足：只有管理员才能创建用户"
        )
    
    return await user_service.create_user(user_data, tenant_id)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_context),
    user_service: UserService = Depends(get_user_service)
):
    """
    获取用户信息
    
    根据用户ID获取用户详细信息。用户只能查看自己的信息，
    管理员可以查看租户内所有用户信息。
    """
    # 权限检查：用户只能查看自己的信息，管理员可以查看所有
    if (current_user.id != user_id and 
        current_user.role not in ["super_admin", "tenant_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足：只能查看自己的用户信息"
        )
    
    user = await user_service.get_user_by_id(user_id, tenant_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return user
```

### **数据模型规范**
```python
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional
from datetime import datetime
from uuid import UUID

class UserBase(BaseModel):
    """用户基础模型"""
    email: EmailStr = Field(..., description="用户邮箱地址")
    full_name: str = Field(..., min_length=2, max_length=100, description="用户姓名")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名")

class UserCreate(UserBase):
    """用户创建模型"""
    password: str = Field(..., min_length=8, max_length=100, description="用户密码")
    
    @validator('password')
    def validate_password(cls, v):
        """密码强度验证"""
        if not any(c.isupper() for c in v):
            raise ValueError('密码必须包含至少一个大写字母')
        if not any(c.islower() for c in v):
            raise ValueError('密码必须包含至少一个小写字母')
        if not any(c.isdigit() for c in v):
            raise ValueError('密码必须包含至少一个数字')
        return v

class UserResponse(UserBase):
    """用户响应模型"""
    id: UUID = Field(..., description="用户唯一标识")
    tenant_id: UUID = Field(..., description="租户ID")
    status: str = Field(..., description="用户状态")
    role: str = Field(..., description="用户角色")
    email_verified: bool = Field(..., description="邮箱验证状态")
    created_at: datetime = Field(..., description="创建时间")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "full_name": "张三",
                "username": "zhangsan",
                "tenant_id": "123e4567-e89b-12d3-a456-426614174001",
                "status": "active",
                "role": "end_user",
                "email_verified": True,
                "created_at": "2025-01-20T10:30:00Z",
                "last_login_at": "2025-01-20T15:45:00Z"
            }
        }
```

### **异常处理规范**
```python
from app.core.exceptions import (
    UserNotFoundError, 
    DuplicateEmailError, 
    InvalidCredentialsError
)

class UserService:
    async def authenticate_user(self, email: str, password: str, tenant_id: str) -> User:
        """
        用户认证
        
        验证用户邮箱和密码，返回认证成功的用户对象
        """
        try:
            # 查找用户
            user = await self.repository.get_by_email(email, tenant_id)
            if not user:
                self.logger.warning(f"登录失败：用户不存在 {email}")
                raise UserNotFoundError(f"用户 {email} 不存在")
            
            # 验证密码
            if not self.verify_password(password, user.password_hash):
                self.logger.warning(f"登录失败：密码错误 {email}")
                raise InvalidCredentialsError("邮箱或密码错误")
            
            # 检查用户状态
            if user.status != "active":
                self.logger.warning(f"登录失败：用户状态异常 {email}")
                raise InvalidCredentialsError("用户账户已被禁用")
            
            # 更新最后登录时间
            await self.repository.update_last_login(user.id)
            
            self.logger.info(f"用户登录成功: {email}")
            return user
            
        except (UserNotFoundError, InvalidCredentialsError):
            # 重新抛出业务异常
            raise
        except Exception as e:
            # 记录未预期的错误
            self.logger.error(f"用户认证过程中发生未预期错误: {str(e)}")
            raise InvalidCredentialsError("认证服务暂时不可用")
```

---

## 📋 Python特定检查清单

- [ ] 遵循PEP 8规范
- [ ] 使用类型提示
- [ ] 文档字符串完整
- [ ] 异常处理具体化
- [ ] 使用参数化查询