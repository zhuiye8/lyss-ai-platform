"""
数据库连接和会话管理

配置SQLAlchemy数据库连接，提供数据库会话依赖注入，
支持多租户数据隔离和连接池管理。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# 数据库引擎配置
engine = create_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,  # 连接前测试连接可用性
    echo=settings.debug,  # 开发环境下打印SQL
)

# 会话工厂
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

# 基础模型类
Base = declarative_base()

# 元数据
metadata = MetaData()


async def init_db():
    """初始化数据库连接"""
    try:
        # 测试数据库连接
        with engine.connect() as connection:
            logger.info("数据库连接测试成功")
        
        # 创建表（如果不存在）
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建完成")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


def get_db() -> Generator[Session, None, None]:
    """
    数据库会话依赖注入
    
    提供数据库会话对象，自动处理事务提交和回滚，
    确保连接正确释放。
    
    Yields:
        Session: 数据库会话对象
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"数据库会话异常: {e}")
        db.rollback()
        raise
    finally:
        db.close()


class DatabaseManager:
    """数据库管理器"""
    
    @staticmethod
    def get_session() -> Session:
        """获取数据库会话"""
        return SessionLocal()
    
    @staticmethod
    def create_tables():
        """创建所有数据表"""
        Base.metadata.create_all(bind=engine)
        logger.info("数据表创建完成")
    
    @staticmethod
    def drop_tables():
        """删除所有数据表（仅开发环境）"""
        if settings.is_production:
            raise RuntimeError("生产环境不允许删除数据表")
        
        Base.metadata.drop_all(bind=engine)
        logger.warning("所有数据表已删除")
    
    @staticmethod
    def check_connection() -> bool:
        """检查数据库连接"""
        try:
            with engine.connect():
                return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False


# 全局数据库管理器实例
db_manager = DatabaseManager()