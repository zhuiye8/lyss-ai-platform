"""
数据库初始化脚本

创建数据库表结构并插入初始化数据。
包括供应商配置和示例Channel配置。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import asyncio
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.database import (
    Base, 
    ProviderConfigTable, 
    ChannelTable, 
    RequestLogTable,
    ChannelMetricsTable,
    TenantQuotaTable
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tables():
    """创建所有数据库表"""
    try:
        # 使用异步引擎创建表
        engine = create_async_engine(settings.database_url, echo=True)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("数据库表创建成功")
        
    except Exception as e:
        logger.error(f"创建数据库表失败: {e}")
        raise


async def insert_initial_data():
    """插入初始化数据"""
    try:
        engine = create_async_engine(settings.database_url)
        async_session = sessionmaker(engine, class_=AsyncSession)
        
        async with async_session() as session:
            # 插入默认供应商配置
            providers = [
                ProviderConfigTable(
                    provider_id="openai",
                    name="OpenAI",
                    description="OpenAI GPT系列模型",
                    base_url="https://api.openai.com",
                    auth_type="bearer",
                    supported_models=[
                        "gpt-4", "gpt-4-turbo", "gpt-4-turbo-preview",
                        "gpt-3.5-turbo", "gpt-3.5-turbo-16k"
                    ],
                    default_config={
                        "temperature": 0.7,
                        "max_tokens": 4000,
                        "top_p": 1.0,
                        "frequency_penalty": 0.0,
                        "presence_penalty": 0.0
                    },
                    status="active"
                ),
                ProviderConfigTable(
                    provider_id="anthropic",
                    name="Anthropic",
                    description="Anthropic Claude系列模型",
                    base_url="https://api.anthropic.com",
                    auth_type="api_key",
                    supported_models=[
                        "claude-3-opus-20240229",
                        "claude-3-sonnet-20240229", 
                        "claude-3-haiku-20240307",
                        "claude-2.1", "claude-2.0"
                    ],
                    default_config={
                        "temperature": 0.7,
                        "max_tokens": 4000,
                        "top_p": 1.0
                    },
                    status="active"
                ),
                ProviderConfigTable(
                    provider_id="azure_openai",
                    name="Azure OpenAI",
                    description="微软Azure OpenAI服务",
                    base_url="https://your-resource.openai.azure.com",
                    auth_type="api_key",
                    supported_models=[
                        "gpt-4", "gpt-4-32k", "gpt-35-turbo", "gpt-35-turbo-16k"
                    ],
                    default_config={
                        "temperature": 0.7,
                        "max_tokens": 4000,
                        "api_version": "2023-12-01-preview"
                    },
                    status="active"
                ),
                ProviderConfigTable(
                    provider_id="google_gemini",
                    name="Google Gemini",
                    description="Google Gemini系列模型",
                    base_url="https://generativelanguage.googleapis.com",
                    auth_type="api_key", 
                    supported_models=[
                        "gemini-pro", "gemini-pro-vision"
                    ],
                    default_config={
                        "temperature": 0.7,
                        "max_output_tokens": 4000,
                        "top_p": 1.0
                    },
                    status="active"
                )
            ]
            
            # 检查是否已存在数据
            existing = await session.execute(
                session.query(ProviderConfigTable).filter(
                    ProviderConfigTable.provider_id.in_([p.provider_id for p in providers])
                )
            )
            
            if not existing.scalars().first():
                session.add_all(providers)
                logger.info(f"插入了 {len(providers)} 个默认供应商配置")
            else:
                logger.info("默认供应商配置已存在，跳过插入")
            
            await session.commit()
            
        logger.info("初始化数据插入完成")
        
    except Exception as e:
        logger.error(f"插入初始化数据失败: {e}")
        raise


async def init_database():
    """完整数据库初始化流程"""
    logger.info("开始初始化数据库...")
    
    try:
        # 1. 创建表结构
        await create_tables()
        
        # 2. 插入初始化数据
        await insert_initial_data()
        
        logger.info("数据库初始化完成！")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


if __name__ == "__main__":
    # 运行数据库初始化
    asyncio.run(init_database())