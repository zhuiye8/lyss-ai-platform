#!/usr/bin/env python3
"""
数据库初始化脚本

用于初始化lyss-provider-service的PostgreSQL数据库，
包括创建表结构、初始化数据、运行迁移等。

使用方法:
    python scripts/init_database.py [--env development|production] [--force]

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import asyncio
import sys
import os
from pathlib import Path
import argparse
import logging
from typing import Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, inspect
from app.core.config import get_settings
from app.core.database import engine, Base, db_manager
from app.models.database import *  # 导入所有数据模型

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='初始化Provider Service数据库')
    parser.add_argument(
        '--env', 
        choices=['development', 'production', 'testing'],
        default='development',
        help='环境类型 (default: development)'
    )
    parser.add_argument(
        '--force', 
        action='store_true',
        help='强制重新创建表（会删除现有数据）'
    )
    parser.add_argument(
        '--seed', 
        action='store_true',
        help='创建测试数据'
    )
    parser.add_argument(
        '--migrate', 
        action='store_true',
        help='运行数据库迁移'
    )
    parser.add_argument(
        '--check', 
        action='store_true',
        help='仅检查数据库连接'
    )
    return parser.parse_args()


def check_database_connection() -> bool:
    """检查数据库连接"""
    try:
        with engine.connect() as conn:
            # 执行简单查询测试连接
            result = conn.execute(text("SELECT 1")).scalar()
            if result == 1:
                logger.info("✅ 数据库连接测试成功")
                return True
            else:
                logger.error("❌ 数据库连接测试失败：返回值不正确")
                return False
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        return False


def check_database_exists() -> bool:
    """检查数据库是否存在"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM information_schema.tables WHERE table_name = 'provider_configs' LIMIT 1")
            ).fetchone()
            return result is not None
    except Exception as e:
        logger.error(f"检查数据库表失败: {e}")
        return False


def get_existing_tables() -> list:
    """获取现有表列表"""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"现有表数量: {len(tables)}")
        if tables:
            logger.info(f"现有表: {', '.join(tables)}")
        return tables
    except Exception as e:
        logger.error(f"获取表列表失败: {e}")
        return []


def create_database_tables(force: bool = False) -> bool:
    """创建数据库表"""
    try:
        existing_tables = get_existing_tables()
        
        if existing_tables and not force:
            logger.info("数据库表已存在，使用 --force 参数强制重建")
            return True
        
        if force and existing_tables:
            logger.warning("强制删除现有表...")
            Base.metadata.drop_all(bind=engine)
            logger.warning("现有表已删除")
        
        # 创建所有表
        logger.info("开始创建数据库表...")
        Base.metadata.create_all(bind=engine)
        
        # 验证表是否创建成功
        new_tables = get_existing_tables()
        if new_tables:
            logger.info(f"✅ 成功创建 {len(new_tables)} 个数据表")
            return True
        else:
            logger.error("❌ 未能创建任何数据表")
            return False
            
    except Exception as e:
        logger.error(f"❌ 创建数据库表失败: {e}")
        return False


def insert_default_providers() -> bool:
    """插入默认供应商配置"""
    try:
        with engine.connect() as conn:
            # 检查是否已有数据
            result = conn.execute(
                text("SELECT COUNT(*) FROM provider_configs")
            ).scalar()
            
            if result > 0:
                logger.info(f"供应商配置表已有 {result} 条记录，跳过初始化")
                return True
            
            # 插入默认供应商配置
            providers_sql = """
            INSERT INTO provider_configs (provider_id, name, description, base_url, auth_type, supported_models, default_config) VALUES
            ('openai', 'OpenAI', 'OpenAI GPT系列模型', 'https://api.openai.com/v1', 'api_key', 
             '["gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-4", "gpt-4-32k", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini"]',
             '{"timeout": 30, "max_retries": 3}'),
            ('anthropic', 'Anthropic', 'Anthropic Claude系列模型', 'https://api.anthropic.com', 'api_key',
             '["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229", "claude-3-5-sonnet-20241022"]',
             '{"timeout": 30, "max_retries": 3}'),
            ('google', 'Google AI', 'Google Gemini系列模型', 'https://generativelanguage.googleapis.com/v1beta', 'api_key',
             '["gemini-pro", "gemini-pro-vision", "gemini-ultra"]',
             '{"timeout": 30, "max_retries": 3}'),
            ('deepseek', 'DeepSeek', 'DeepSeek AI系列模型', 'https://api.deepseek.com', 'api_key',
             '["deepseek-chat", "deepseek-coder"]',
             '{"timeout": 30, "max_retries": 3}'),
            ('azure-openai', 'Azure OpenAI', 'Microsoft Azure OpenAI服务', 'https://{resource}.openai.azure.com', 'api_key',
             '["gpt-35-turbo", "gpt-4", "gpt-4-32k"]',
             '{"api_version": "2024-02-15-preview", "timeout": 30}')
            """
            
            conn.execute(text(providers_sql))
            conn.commit()
            
            # 验证插入结果
            count = conn.execute(
                text("SELECT COUNT(*) FROM provider_configs")
            ).scalar()
            
            logger.info(f"✅ 成功初始化 {count} 个默认供应商配置")
            return True
            
    except Exception as e:
        logger.error(f"❌ 插入默认供应商配置失败: {e}")
        return False


def create_test_data() -> bool:
    """创建测试数据"""
    try:
        logger.info("开始创建测试数据...")
        
        # 读取并执行测试数据SQL
        sql_file = Path(__file__).parent.parent.parent / "sql" / "seeds" / "provider_service_test_data.sql"
        
        if not sql_file.exists():
            logger.warning(f"测试数据文件不存在: {sql_file}")
            return False
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割SQL语句并执行（跳过注释和空行）
        with engine.connect() as conn:
            # 简单的SQL分割（实际项目中应该使用更严格的SQL解析器）
            statements = []
            current_statement = []
            
            for line in sql_content.split('\n'):
                line = line.strip()
                if not line or line.startswith('--'):
                    continue
                
                current_statement.append(line)
                
                if line.endswith(';'):
                    statement = ' '.join(current_statement)
                    if statement and not statement.startswith('\\'):
                        statements.append(statement)
                    current_statement = []
            
            # 执行SQL语句
            for statement in statements:
                try:
                    conn.execute(text(statement))
                except Exception as e:
                    logger.warning(f"跳过SQL语句执行失败: {str(e)[:100]}...")
                    continue
            
            conn.commit()
            logger.info("✅ 测试数据创建完成")
            return True
            
    except Exception as e:
        logger.error(f"❌ 创建测试数据失败: {e}")
        return False


def show_database_summary():
    """显示数据库概览"""
    try:
        with engine.connect() as conn:
            tables_info = {
                'provider_configs': '供应商配置',
                'provider_channels': 'Channel配置',
                'channel_metrics': 'Channel指标',
                'tenant_quotas': '租户配额',
                'proxy_request_logs': '请求日志'
            }
            
            logger.info("\n📊 数据库概览:")
            logger.info("=" * 50)
            
            for table, desc in tables_info.items():
                try:
                    count = conn.execute(
                        text(f"SELECT COUNT(*) FROM {table}")
                    ).scalar()
                    logger.info(f"{desc} ({table}): {count} 条记录")
                except Exception:
                    logger.info(f"{desc} ({table}): 表不存在或无法访问")
            
            logger.info("=" * 50)
            
    except Exception as e:
        logger.error(f"获取数据库概览失败: {e}")


def main():
    """主函数"""
    args = parse_arguments()
    settings = get_settings()
    
    # 设置环境变量
    if args.env:
        os.environ['ENVIRONMENT'] = args.env
    
    logger.info(f"🚀 初始化Provider Service数据库 - 环境: {args.env}")
    logger.info(f"数据库URL: {settings.database_url}")
    
    # 检查数据库连接
    if not check_database_connection():
        logger.error("数据库连接失败，请检查配置")
        sys.exit(1)
    
    if args.check:
        logger.info("✅ 数据库连接正常")
        sys.exit(0)
    
    # 创建数据库表
    success = True
    if not args.migrate:  # 如果不是迁移模式，创建表
        success = create_database_tables(force=args.force)
        if success:
            success = insert_default_providers()
    
    # 创建测试数据
    if success and args.seed:
        if args.env == 'production':
            logger.warning("⚠️  生产环境不建议创建测试数据")
            response = input("确定要在生产环境创建测试数据吗？(y/N): ")
            if response.lower() != 'y':
                logger.info("跳过测试数据创建")
            else:
                create_test_data()
        else:
            create_test_data()
    
    # 运行迁移
    if args.migrate:
        logger.info("数据库迁移功能需要安装Alembic")
        logger.info("运行: pip install alembic")
        logger.info("然后: alembic upgrade head")
    
    # 显示概览
    if success:
        show_database_summary()
        logger.info("🎉 Provider Service数据库初始化完成！")
    else:
        logger.error("❌ 数据库初始化失败")
        sys.exit(1)


if __name__ == "__main__":
    main()