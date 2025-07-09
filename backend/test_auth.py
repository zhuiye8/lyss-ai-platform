#!/usr/bin/env python3
"""
认证模块测试脚本
测试JWT认证、用户登录、权限验证等功能
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from common.database import init_database, async_session_maker
from common.security import get_security_manager, Role, Permission
from common.models import User, Tenant, TenantStatus, UserStatus
from common.config import get_settings
from common.redis_client import init_redis
import uuid

async def test_security_manager():
    """测试SecurityManager功能"""
    print("🔒 测试SecurityManager功能...")
    
    security_manager = get_security_manager()
    
    # 测试密码哈希
    password = "Test123!@#"
    hashed = security_manager.hash_password(password)
    print(f"✓ 密码哈希: {hashed[:50]}...")
    
    # 测试密码验证
    is_valid = security_manager.verify_password(password, hashed)
    print(f"✓ 密码验证: {is_valid}")
    
    # 测试JWT令牌
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    email = "test@example.com"
    roles = [Role.END_USER.value]
    
    # 创建访问令牌
    access_token = security_manager.create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        email=email,
        roles=roles
    )
    print(f"✓ 访问令牌: {access_token[:50]}...")
    
    # 验证令牌
    token_data = security_manager.verify_token(access_token)
    if token_data:
        print(f"✓ 令牌验证成功: {token_data.email}")
        print(f"  用户ID: {token_data.user_id}")
        print(f"  租户ID: {token_data.tenant_id}")
        print(f"  角色: {token_data.roles}")
        print(f"  权限: {token_data.permissions[:3]}...")
    else:
        print("✗ 令牌验证失败")
    
    # 测试权限检查
    has_permission = security_manager.check_permission(
        roles, 
        Permission.CONVERSATION_CREATE.value
    )
    print(f"✓ 权限检查 (创建对话): {has_permission}")
    
    # 测试刷新令牌
    refresh_token = security_manager.create_refresh_token(
        user_id=user_id,
        tenant_id=tenant_id
    )
    print(f"✓ 刷新令牌: {refresh_token[:50]}...")
    
    return True

async def setup_test_data():
    """设置测试数据"""
    print("🗄️ 设置测试数据...")
    
    async with async_session_maker() as session:
        # 创建测试租户
        test_tenant = Tenant(
            tenant_name="测试企业",
            tenant_slug="test-company",
            contact_email="admin@test.com",
            contact_name="管理员",
            company_name="测试公司",
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
        
        # 创建测试用户
        security_manager = get_security_manager()
        password_hash = security_manager.hash_password("Test123!@#")
        
        test_user = User(
            tenant_id=test_tenant.tenant_id,
            email="test@example.com",
            password_hash=password_hash,
            first_name="测试",
            last_name="用户",
            status=UserStatus.ACTIVE,
            roles=[Role.END_USER.value],
            password_changed_at=datetime.utcnow()
        )
        
        session.add(test_user)
        await session.commit()
        await session.refresh(test_user)
        
        print(f"✓ 创建测试租户: {test_tenant.tenant_name} ({test_tenant.tenant_id})")
        print(f"✓ 创建测试用户: {test_user.email} ({test_user.user_id})")
        
        return test_tenant, test_user

async def test_database_operations():
    """测试数据库操作"""
    print("🗃️ 测试数据库操作...")
    
    async with async_session_maker() as session:
        # 查询租户
        stmt = select(Tenant).where(Tenant.tenant_slug == "test-company")
        result = await session.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        if tenant:
            print(f"✓ 查询租户成功: {tenant.tenant_name}")
            
            # 查询用户
            user_stmt = select(User).where(
                and_(
                    User.tenant_id == tenant.tenant_id,
                    User.email == "test@example.com"
                )
            )
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            if user:
                print(f"✓ 查询用户成功: {user.email}")
                print(f"  用户角色: {user.roles}")
                print(f"  用户状态: {user.status}")
                return user
            else:
                print("✗ 查询用户失败")
        else:
            print("✗ 查询租户失败")
    
    return None

async def test_auth_flow():
    """测试完整的认证流程"""
    print("🔄 测试完整认证流程...")
    
    # 模拟登录流程
    async with async_session_maker() as session:
        # 1. 查找用户
        stmt = select(User).join(Tenant).where(
            and_(
                User.email == "test@example.com",
                User.status == UserStatus.ACTIVE,
                Tenant.status == TenantStatus.ACTIVE
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            print("✗ 用户不存在")
            return False
        
        # 2. 验证密码
        security_manager = get_security_manager()
        password_valid = security_manager.verify_password("Test123!@#", user.password_hash)
        
        if not password_valid:
            print("✗ 密码验证失败")
            return False
        
        print("✓ 密码验证成功")
        
        # 3. 生成令牌
        access_token = security_manager.create_access_token(
            user_id=str(user.user_id),
            tenant_id=str(user.tenant_id),
            email=user.email,
            roles=user.roles
        )
        
        refresh_token = security_manager.create_refresh_token(
            user_id=str(user.user_id),
            tenant_id=str(user.tenant_id)
        )
        
        print("✓ 令牌生成成功")
        
        # 4. 验证令牌
        token_data = security_manager.verify_token(access_token)
        if token_data:
            print("✓ 令牌验证成功")
            print(f"  用户: {token_data.email}")
            print(f"  权限数量: {len(token_data.permissions)}")
            return True
        else:
            print("✗ 令牌验证失败")
            return False

async def cleanup_test_data():
    """清理测试数据"""
    print("🧹 清理测试数据...")
    
    async with async_session_maker() as session:
        # 删除测试用户
        user_stmt = select(User).where(User.email == "test@example.com")
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if user:
            await session.delete(user)
            print("✓ 删除测试用户")
        
        # 删除测试租户
        tenant_stmt = select(Tenant).where(Tenant.tenant_slug == "test-company")
        tenant_result = await session.execute(tenant_stmt)
        tenant = tenant_result.scalar_one_or_none()
        
        if tenant:
            await session.delete(tenant)
            print("✓ 删除测试租户")
        
        await session.commit()

async def main():
    """主测试函数"""
    print("🚀 开始认证模块测试")
    print("=" * 50)
    
    try:
        # 初始化数据库
        await init_database()
        print("✓ 数据库初始化成功")
        
        # 初始化Redis
        await init_redis()
        print("✓ Redis初始化成功")
        
        # 测试SecurityManager
        await test_security_manager()
        print()
        
        # 设置测试数据
        test_tenant, test_user = await setup_test_data()
        print()
        
        # 测试数据库操作
        db_user = await test_database_operations()
        print()
        
        # 测试认证流程
        if db_user:
            auth_success = await test_auth_flow()
            if auth_success:
                print("✓ 认证流程测试成功")
            else:
                print("✗ 认证流程测试失败")
        print()
        
        # 清理测试数据
        await cleanup_test_data()
        
        print("=" * 50)
        print("🎉 认证模块测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)