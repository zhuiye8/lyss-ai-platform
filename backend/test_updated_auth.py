#!/usr/bin/env python3
"""
更新后的认证模块测试脚本
测试修正后的数据库模型和API响应格式
"""
import asyncio
import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from common.database import init_database, AsyncSessionLocal
from common.security import get_security_manager, Role, Permission
from common.models import (
    User, Tenant, UserStatus, TenantStatus, 
    Role as RoleModel, UserRole,
    TenantConfigSchema
)
from common.response import ResponseHelper, ErrorDetail, ErrorCode
from common.config import get_settings
from common.redis_client import init_redis
import uuid

async def test_response_format():
    """测试响应格式"""
    print("🔧 测试统一响应格式...")
    
    # 测试成功响应
    success_resp = ResponseHelper.success(
        data={"test": "data"},
        message="测试成功"
    )
    print(f"✓ 成功响应格式: {json.dumps(success_resp, ensure_ascii=False, indent=2)}")
    
    # 测试错误响应
    error_resp = ResponseHelper.error(
        message="测试错误",
        errors=[
            ErrorDetail(
                code=ErrorCode.VALIDATION_ERROR,
                message="验证失败",
                field="email"
            )
        ]
    )
    print(f"✓ 错误响应格式: {json.dumps(error_resp, ensure_ascii=False, indent=2)}")
    
    return True

async def test_user_role_system():
    """测试用户角色系统"""
    print("👥 测试用户角色系统...")
    
    async with AsyncSessionLocal() as session:
        # 创建测试租户
        test_tenant = Tenant(
            tenant_name="测试企业2",
            tenant_slug="test-company-2",
            contact_email="admin@test2.com",
            contact_name="管理员",
            company_name="测试公司2",
            status=TenantStatus.ACTIVE,
            config={
                "max_users": 100,
                "max_conversations_per_user": 1000,
                "max_api_calls_per_month": 100000
            }
        )
        
        session.add(test_tenant)
        await session.commit()
        await session.refresh(test_tenant)
        
        # 创建或获取角色
        end_user_role = await session.scalar(
            select(RoleModel).where(RoleModel.role_name == Role.END_USER.value)
        )
        
        if not end_user_role:
            security_manager = get_security_manager()
            end_user_role = RoleModel(
                role_name=Role.END_USER.value,
                role_description="普通用户角色",
                permissions=security_manager.ROLE_PERMISSIONS[Role.END_USER],
                is_system_role=True
            )
            session.add(end_user_role)
            await session.commit()
            await session.refresh(end_user_role)
        
        print(f"✓ 创建/获取角色: {end_user_role.role_name}")
        
        # 创建测试用户
        security_manager = get_security_manager()
        password_hash = security_manager.hash_password("Test123!@#")
        
        test_user = User(
            tenant_id=test_tenant.tenant_id,
            email="test2@example.com",
            password_hash=password_hash,
            first_name="测试",
            last_name="用户2",
            status=UserStatus.ACTIVE,
            email_verified=False
        )
        
        session.add(test_user)
        await session.commit()
        await session.refresh(test_user)
        
        print(f"✓ 创建用户: {test_user.email}")
        
        # 分配角色给用户
        user_role = UserRole(
            user_id=test_user.user_id,
            role_id=end_user_role.role_id,
            assigned_at=datetime.utcnow()
        )
        session.add(user_role)
        await session.commit()
        
        print(f"✓ 分配角色: {test_user.email} -> {end_user_role.role_name}")
        
        # 查询用户角色
        user_roles = await session.scalars(
            select(UserRole).join(RoleModel).where(
                UserRole.user_id == test_user.user_id
            )
        )
        
        role_names = []
        for ur in user_roles:
            role = await session.scalar(
                select(RoleModel).where(RoleModel.role_id == ur.role_id)
            )
            if role:
                role_names.append(role.role_name)
        
        print(f"✓ 查询用户角色: {role_names}")
        
        # 清理测试数据
        await session.delete(user_role)
        await session.delete(test_user)
        await session.commit()
        
        print("✓ 清理测试数据完成")
        
        return True

async def test_security_permissions():
    """测试安全权限系统"""
    print("🔐 测试安全权限系统...")
    
    security_manager = get_security_manager()
    
    # 测试角色权限
    end_user_permissions = security_manager.ROLE_PERMISSIONS[Role.END_USER]
    admin_permissions = security_manager.ROLE_PERMISSIONS[Role.TENANT_ADMIN]
    
    print(f"✓ 普通用户权限数量: {len(end_user_permissions)}")
    print(f"✓ 管理员权限数量: {len(admin_permissions)}")
    
    # 测试权限检查
    has_create_conv = security_manager.check_permission(
        [Role.END_USER.value], 
        Permission.CONVERSATION_CREATE.value
    )
    print(f"✓ 普通用户可创建对话: {has_create_conv}")
    
    has_user_delete = security_manager.check_permission(
        [Role.END_USER.value], 
        Permission.USER_DELETE.value
    )
    print(f"✓ 普通用户可删除用户: {has_user_delete}")
    
    has_admin_delete = security_manager.check_permission(
        [Role.TENANT_ADMIN.value], 
        Permission.USER_DELETE.value
    )
    print(f"✓ 管理员可删除用户: {has_admin_delete}")
    
    # 测试JWT令牌
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    
    access_token = security_manager.create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        email="test@example.com",
        roles=[Role.END_USER.value]
    )
    
    token_data = security_manager.verify_token(access_token)
    if token_data:
        print(f"✓ JWT令牌验证成功: {token_data.email}")
        print(f"  权限数量: {len(token_data.permissions)}")
    else:
        print("✗ JWT令牌验证失败")
    
    return True

async def test_database_models():
    """测试数据库模型"""
    print("🗄️ 测试数据库模型...")
    
    async with AsyncSessionLocal() as session:
        # 测试查询租户
        tenant = await session.scalar(
            select(Tenant).where(Tenant.tenant_slug == "test-company")
        )
        
        if tenant:
            print(f"✓ 查询租户成功: {tenant.tenant_name}")
            
            # 测试租户配置
            config = tenant.config
            print(f"✓ 租户配置: {config}")
            
            # 测试软删除字段
            print(f"✓ 软删除字段: {tenant.deleted_at}")
            
        else:
            print("✗ 查询租户失败")
        
        # 测试用户模型
        user = await session.scalar(
            select(User).where(User.email == "test@example.com")
        )
        
        if user:
            print(f"✓ 查询用户成功: {user.email}")
            print(f"  邮箱验证状态: {user.email_verified}")
            print(f"  登录次数: {user.login_count}")
            print(f"  头像URL: {user.avatar_url}")
        else:
            print("✗ 查询用户失败")
    
    return True

async def test_tenant_config_schema():
    """测试租户配置模式"""
    print("⚙️ 测试租户配置模式...")
    
    # 测试默认配置
    config = TenantConfigSchema()
    print(f"✓ 默认配置: {config.dict()}")
    
    # 测试自定义配置
    custom_config = TenantConfigSchema(
        max_users=50,
        max_conversations_per_user=200,
        enabled_models=["gpt-4", "gpt-3.5-turbo"],
        features={
            "conversation_memory": True,
            "file_upload": False,
            "api_access": True
        }
    )
    print(f"✓ 自定义配置: {custom_config.dict()}")
    
    return True

async def main():
    """主测试函数"""
    print("🚀 开始更新后的认证模块测试")
    print("=" * 60)
    
    try:
        # 初始化数据库
        await init_database()
        print("✓ 数据库初始化成功")
        
        # 初始化Redis
        await init_redis()
        print("✓ Redis初始化成功")
        
        # 测试响应格式
        await test_response_format()
        print()
        
        # 测试安全权限系统
        await test_security_permissions()
        print()
        
        # 测试用户角色系统
        await test_user_role_system()
        print()
        
        # 测试数据库模型
        await test_database_models()
        print()
        
        # 测试租户配置模式
        await test_tenant_config_schema()
        print()
        
        print("=" * 60)
        print("🎉 更新后的认证模块测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)