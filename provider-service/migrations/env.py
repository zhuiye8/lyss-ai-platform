"""
Alembic环境配置

配置Alembic迁移环境，支持数据库版本管理。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# 添加项目路径到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入数据模型
from app.models.database import Base

# Alembic Config对象，提供访问.ini文件中值的方法
config = context.config

# 解释配置文件的日志记录
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 添加你的模型的MetaData对象在这里
# 用于'autogenerate'支持
target_metadata = Base.metadata


def get_database_url():
    """
    从环境变量获取数据库连接URL
    
    Returns:
        str: 数据库连接URL
    """
    # 尝试从环境变量获取
    db_url = os.getenv('PROVIDER_SERVICE_DATABASE_URL')
    
    if not db_url:
        # 使用默认配置
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5433')
        db_user = os.getenv('DB_USER', 'lyss')
        db_password = os.getenv('DB_PASSWORD', 'lyss123')
        db_name = os.getenv('DB_NAME', 'lyss_provider_db')
        
        db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    return db_url


def run_migrations_offline() -> None:
    """
    在'离线'模式下运行迁移
    
    这将配置上下文，只需要一个URL
    而不是一个Engine，尽管Engine也是可以接受的。
    通过跳过Engine创建，我们甚至不需要可用的数据库。
    
    调用context.execute()输出SQL到STDOUT。
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    在'在线'模式下运行迁移
    
    在这种情况下，我们需要创建一个Engine
    并将连接与上下文关联。
    """
    # 获取数据库URL并更新配置
    db_url = get_database_url()
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = db_url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# 根据上下文选择运行模式
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()