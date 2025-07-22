#!/usr/bin/env python3
"""
Provider Service数据库迁移脚本

用于将Provider Service数据库结构迁移到最新的统一规范，
确保与其他服务的数据库设计保持一致。

使用方法:
    python scripts/migrate_database.py [--dry-run] [--env development|production]

Author: Lyss AI Team
Created: 2025-01-22
Modified: 2025-01-22
"""

import asyncio
import sys
import os
from pathlib import Path
import argparse
import logging
from typing import List, Dict, Any

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, inspect, Column, String, Integer, DateTime, JSON, Float, Boolean, Text, Index
from sqlalchemy.sql import func
from app.core.config import get_settings
from app.core.database import engine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """数据库迁移器"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.migration_history = []
    
    def log_migration(self, operation: str, description: str):
        """记录迁移操作"""
        self.migration_history.append({
            'operation': operation,
            'description': description,
            'executed': not self.dry_run
        })
        
        if self.dry_run:
            logger.info(f"[DRY RUN] {operation}: {description}")
        else:
            logger.info(f"[EXECUTE] {operation}: {description}")
    
    def execute_sql(self, sql: str, description: str):
        """执行SQL语句"""
        self.log_migration("SQL", description)
        
        if not self.dry_run:
            try:
                with engine.connect() as conn:
                    conn.execute(text(sql))
                    conn.commit()
                logger.info("✅ SQL执行成功")
            except Exception as e:
                logger.error(f"❌ SQL执行失败: {e}")
                raise
    
    def check_table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            inspector = inspect(engine)
            return table_name in inspector.get_table_names()
        except Exception as e:
            logger.error(f"检查表 {table_name} 失败: {e}")
            return False
    
    def get_table_columns(self, table_name: str) -> List[Dict]:
        """获取表的列信息"""
        try:
            inspector = inspect(engine)
            return inspector.get_columns(table_name)
        except Exception as e:
            logger.error(f"获取表 {table_name} 列信息失败: {e}")
            return []
    
    def migrate_channel_table(self):
        """迁移Channel表以符合统一规范"""
        logger.info("🔄 开始迁移Provider Channel表...")
        
        # 检查现有表结构
        if not self.check_table_exists('provider_channels'):
            logger.info("provider_channels表不存在，创建新表...")
            
            create_sql = """
            CREATE TABLE provider_channels (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                name VARCHAR(100) NOT NULL,
                type INTEGER NOT NULL REFERENCES provider_types(id),
                
                -- One-API标准字段
                key TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                weight INTEGER DEFAULT 1,
                status INTEGER DEFAULT 1,
                
                -- 配额管理
                quota BIGINT DEFAULT -1,
                used_quota BIGINT DEFAULT 0,
                rate_limit INTEGER DEFAULT 100,
                
                -- 配置范围
                config_scope VARCHAR(20) DEFAULT 'personal',
                owner_id UUID,
                group_id UUID,
                
                -- 模型配置
                models JSONB DEFAULT '[]',
                model_mapping JSONB DEFAULT '{}',
                
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                
                CONSTRAINT uk_provider_channels_tenant_name UNIQUE(tenant_id, name)
            );
            
            -- 创建索引
            CREATE INDEX idx_provider_channels_tenant_scope ON provider_channels(tenant_id, config_scope);
            CREATE INDEX idx_provider_channels_status ON provider_channels(status);
            CREATE INDEX idx_provider_channels_priority ON provider_channels(priority);
            """
            
            self.execute_sql(create_sql, "创建符合统一规范的provider_channels表")
            return
        
        # 检查是否需要添加新字段
        columns = self.get_table_columns('provider_channels')
        column_names = [col['name'] for col in columns]
        
        # 需要添加的字段
        required_fields = {
            'quota': 'BIGINT DEFAULT -1',
            'used_quota': 'BIGINT DEFAULT 0', 
            'rate_limit': 'INTEGER DEFAULT 100',
            'config_scope': 'VARCHAR(20) DEFAULT \'personal\'',
            'owner_id': 'UUID',
            'group_id': 'UUID',
            'model_mapping': 'JSONB DEFAULT \'{}\'',
            'type': 'INTEGER'
        }
        
        # 添加缺失字段
        for field_name, field_definition in required_fields.items():
            if field_name not in column_names:
                alter_sql = f"ALTER TABLE provider_channels ADD COLUMN {field_name} {field_definition}"
                self.execute_sql(alter_sql, f"添加字段 {field_name}")
        
        # 检查并创建缺失的索引
        self.create_missing_indexes('provider_channels', [
            "CREATE INDEX IF NOT EXISTS idx_provider_channels_tenant_scope ON provider_channels(tenant_id, config_scope)",
            "CREATE INDEX IF NOT EXISTS idx_provider_channels_priority ON provider_channels(priority)",
            "CREATE INDEX IF NOT EXISTS idx_provider_channels_quota ON provider_channels(quota)",
        ])
    
    def migrate_token_table(self):
        """迁移Token表以支持One-API兼容"""
        logger.info("🔄 创建用户Token表...")
        
        if not self.check_table_exists('user_tokens'):
            create_sql = """
            CREATE TABLE user_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                user_id UUID NOT NULL,
                name VARCHAR(100) NOT NULL,
                key TEXT UNIQUE NOT NULL,
                
                -- 权限控制
                allowed_channels JSONB DEFAULT '[]',
                allowed_models JSONB DEFAULT '[]',
                
                -- 配额管理
                quota BIGINT DEFAULT -1,
                used_quota BIGINT DEFAULT 0,
                rate_limit INTEGER DEFAULT 60,
                
                -- 状态管理
                status INTEGER DEFAULT 1,
                expires_at TIMESTAMP,
                last_used_at TIMESTAMP,
                
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                
                CONSTRAINT uk_user_tokens_tenant_name UNIQUE(tenant_id, name)
            );
            
            -- 创建索引
            CREATE INDEX idx_user_tokens_tenant_user ON user_tokens(tenant_id, user_id);
            CREATE INDEX idx_user_tokens_key ON user_tokens(key);
            CREATE INDEX idx_user_tokens_status ON user_tokens(status);
            CREATE INDEX idx_user_tokens_expires ON user_tokens(expires_at);
            """
            
            self.execute_sql(create_sql, "创建用户Token表")
    
    def migrate_provider_types_table(self):
        """创建供应商类型定义表"""
        logger.info("🔄 创建供应商类型表...")
        
        if not self.check_table_exists('provider_types'):
            create_sql = """
            CREATE TABLE provider_types (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                display_name VARCHAR(100) NOT NULL,
                base_url TEXT,
                supported_models JSONB DEFAULT '[]',
                api_format VARCHAR(20) DEFAULT 'openai',
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            
            -- 插入预置供应商类型
            INSERT INTO provider_types (name, display_name, base_url, api_format) VALUES
            ('openai', 'OpenAI', 'https://api.openai.com', 'openai'),
            ('anthropic', 'Anthropic', 'https://api.anthropic.com', 'anthropic'),
            ('deepseek', 'DeepSeek', 'https://api.deepseek.com', 'openai'),
            ('azure-openai', 'Azure OpenAI', NULL, 'openai'),
            ('zhipu', '智谱AI', 'https://open.bigmodel.cn', 'openai'),
            ('google', 'Google AI', 'https://generativelanguage.googleapis.com', 'google');
            """
            
            self.execute_sql(create_sql, "创建供应商类型表并插入预置数据")
    
    def migrate_usage_logs_table(self):
        """优化请求日志表结构"""
        logger.info("🔄 优化请求日志表...")
        
        # 检查表是否存在
        if self.check_table_exists('provider_request_logs'):
            # 添加分区支持（按月分区）
            partition_sql = """
            -- 为大数据量表添加分区支持
            -- 按月分区provider_request_logs表
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_class WHERE relname = 'provider_request_logs_y2025m01'
                ) THEN
                    -- 注意：这里只是示例，实际分区需要重建表
                    -- 在生产环境中需要更谨慎的分区策略
                    RAISE NOTICE '需要手动创建分区表，请参考文档';
                END IF;
            END $$;
            """
            
            self.execute_sql(partition_sql, "准备请求日志表分区")
    
    def create_missing_indexes(self, table_name: str, indexes: List[str]):
        """创建缺失的索引"""
        logger.info(f"检查表 {table_name} 的索引...")
        
        for index_sql in indexes:
            try:
                self.execute_sql(index_sql, f"为 {table_name} 创建索引")
            except Exception as e:
                if "already exists" in str(e):
                    logger.info(f"索引已存在，跳过")
                else:
                    raise
    
    def optimize_existing_tables(self):
        """优化现有表结构"""
        logger.info("🔄 优化现有表结构...")
        
        # 为现有表添加注释
        comments_sql = [
            "COMMENT ON TABLE provider_configs IS '供应商配置表'",
            "COMMENT ON TABLE provider_channels IS 'Provider Channel配置表（多租户隔离）'",
            "COMMENT ON TABLE provider_request_logs IS '请求日志表'",
            "COMMENT ON TABLE provider_channel_metrics IS 'Provider Channel指标统计表'",
            "COMMENT ON COLUMN provider_channels.tenant_id IS '租户UUID'",
            "COMMENT ON COLUMN provider_channels.credentials IS 'pgcrypto加密后的凭证信息'",
        ]
        
        for comment_sql in comments_sql:
            try:
                self.execute_sql(comment_sql, "添加表注释")
            except Exception as e:
                logger.warning(f"添加注释失败: {e}")
    
    def update_statistics(self):
        """更新数据库统计信息"""
        if not self.dry_run:
            logger.info("🔄 更新数据库统计信息...")
            
            analyze_sql = """
            ANALYZE provider_configs;
            ANALYZE provider_channels;
            ANALYZE provider_request_logs;
            ANALYZE provider_channel_metrics;
            """
            
            self.execute_sql(analyze_sql, "更新表统计信息")
    
    def run_migration(self):
        """执行完整迁移"""
        logger.info("🚀 开始Provider Service数据库迁移...")
        
        try:
            # 1. 创建供应商类型表
            self.migrate_provider_types_table()
            
            # 2. 迁移Channel表
            self.migrate_channel_table()
            
            # 3. 创建Token表
            self.migrate_token_table()
            
            # 4. 优化请求日志表
            self.migrate_usage_logs_table()
            
            # 5. 优化现有表
            self.optimize_existing_tables()
            
            # 6. 更新统计信息
            self.update_statistics()
            
            # 显示迁移摘要
            self.show_migration_summary()
            
            logger.info("🎉 Provider Service数据库迁移完成！")
            
        except Exception as e:
            logger.error(f"❌ 迁移过程中发生错误: {e}")
            raise
    
    def show_migration_summary(self):
        """显示迁移摘要"""
        logger.info("\n📊 迁移操作摘要:")
        logger.info("=" * 60)
        
        for item in self.migration_history:
            status = "✅ 已执行" if item['executed'] else "🔍 预览"
            logger.info(f"{status} {item['operation']}: {item['description']}")
        
        logger.info("=" * 60)
        logger.info(f"总操作数: {len(self.migration_history)}")


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='Provider Service数据库迁移')
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='预览迁移操作，不实际执行'
    )
    parser.add_argument(
        '--env', 
        choices=['development', 'production', 'testing'],
        default='development',
        help='环境类型 (default: development)'
    )
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()
    
    # 设置环境变量
    if args.env:
        os.environ['ENVIRONMENT'] = args.env
    
    if args.dry_run:
        logger.info("🔍 预览模式 - 不会实际修改数据库")
    
    logger.info(f"🚀 Provider Service数据库迁移 - 环境: {args.env}")
    
    # 检查数据库连接
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1")).scalar()
        logger.info("✅ 数据库连接正常")
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        sys.exit(1)
    
    # 执行迁移
    migrator = DatabaseMigrator(dry_run=args.dry_run)
    
    try:
        migrator.run_migration()
        
        if args.dry_run:
            logger.info("🔍 预览完成！要实际执行迁移，请移除 --dry-run 参数")
        else:
            logger.info("🎉 迁移成功完成！")
            
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()