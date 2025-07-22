# -*- coding: utf-8 -*-
"""
数据库引擎配置模块

基于OpenWebUI最佳实践的SQLAlchemy数据库连接池优化配置，
支持高并发用户管理操作和实时响应需求。

参考 OpenWebUI 的优化策略：
- QueuePool 连接池配置
- 连接健康检查
- 适配PostgreSQL生产环境
"""

import logging
import time
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Dict, Any
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncEngine, 
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.pool import QueuePool, StaticPool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from sqlalchemy.orm import declarative_base, sessionmaker
import psutil

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# SQLAlchemy 基类
Base = declarative_base()

class DatabaseEngineManager:
    """
    数据库引擎管理器
    
    基于OpenWebUI优化方案，提供高性能数据库连接管理：
    - 连接池优化配置
    - 健康检查机制
    - 异步支持
    - 自动重连策略
    """
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.async_session_maker: Optional[async_sessionmaker] = None
        self.connection_pools_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'checked_in_connections': 0,
            'checked_out_connections': 0,
            'overflow_connections': 0,
            'invalid_connections': 0
        }
        
    def create_engine(self, database_url: str) -> AsyncEngine:
        """
        创建优化的异步数据库引擎
        
        Args:
            database_url: 数据库连接URL
            
        Returns:
            AsyncEngine: 配置好的异步引擎
        """
        try:
            # 解析URL以确定是否是SQLite（开发环境）或PostgreSQL（生产环境）
            is_sqlite = database_url.startswith("sqlite")
            is_async_url = "asyncpg" in database_url or "aiomysql" in database_url
            
            # 如果不是异步URL，转换为异步版本
            if not is_async_url and not is_sqlite:
                # PostgreSQL: postgresql+asyncpg://
                if database_url.startswith("postgresql://"):
                    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
                elif database_url.startswith("mysql://"):
                    database_url = database_url.replace("mysql://", "mysql+aiomysql://")
            elif is_sqlite and not database_url.startswith("sqlite+aiosqlite://"):
                database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://")
            
            # 引擎配置参数
            engine_kwargs = {
                "echo": settings.database_echo,  # 生产环境应为False
                "future": True,  # 使用SQLAlchemy 2.0风格
            }
            
            # SQLite配置（开发/测试环境）
            if is_sqlite:
                engine_kwargs.update({
                    "poolclass": StaticPool,
                    "connect_args": {
                        "check_same_thread": False,
                        "timeout": 30,
                    }
                })
            else:
                # PostgreSQL/MySQL配置（生产环境）
                # 借鉴OpenWebUI的连接池优化参数
                engine_kwargs.update({
                    "poolclass": QueuePool,
                    "pool_size": settings.database_pool_size,        # 30 (基础连接池大小)
                    "max_overflow": settings.database_max_overflow,  # 50 (额外连接数)
                    "pool_pre_ping": True,                          # 连接前健康检查
                    "pool_recycle": settings.database_pool_recycle, # 3600秒回收连接
                    "pool_timeout": 30,                             # 获取连接超时
                    "connect_args": {
                        "connect_timeout": 10,
                        "application_name": f"lyss-user-service-{settings.environment}",
                        "options": "-c statement_timeout=30000",  # 30秒语句超时
                    }
                })
            
            # 创建异步引擎
            engine = create_async_engine(database_url, **engine_kwargs)
            
            # 注册事件监听器
            self._setup_engine_events(engine.sync_engine)
            
            logger.info(f"数据库引擎创建成功: {database_url.split('@')[0]}@***")
            return engine
            
        except Exception as e:
            logger.error(f"数据库引擎创建失败: {e}")
            raise
    
    def _setup_engine_events(self, engine: Engine):
        """设置引擎事件监听器"""
        
        @event.listens_for(engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """连接建立事件"""
            logger.debug("数据库连接已建立")
            self.connection_pools_stats['total_connections'] += 1
        
        @event.listens_for(engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """连接签出事件"""
            self.connection_pools_stats['checked_out_connections'] += 1
            self.connection_pools_stats['active_connections'] += 1
        
        @event.listens_for(engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """连接签入事件"""
            self.connection_pools_stats['checked_in_connections'] += 1
            self.connection_pools_stats['active_connections'] = max(0, 
                self.connection_pools_stats['active_connections'] - 1)
        
        @event.listens_for(engine, "invalidate")
        def on_invalidate(dbapi_connection, connection_record, exception):
            """连接失效事件"""
            logger.warning(f"数据库连接失效: {exception}")
            self.connection_pools_stats['invalid_connections'] += 1
    
    async def initialize(self, database_url: str = None):
        """
        初始化数据库连接
        
        Args:
            database_url: 数据库连接URL，如果为None则使用配置中的URL
        """
        if database_url is None:
            database_url = settings.database_url
        
        try:
            # 创建引擎
            self.engine = self.create_engine(database_url)
            
            # 创建会话工厂
            self.async_session_maker = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,  # 提交后不过期对象
                autoflush=False,         # 手动刷新
                autocommit=False,        # 手动提交
            )
            
            # 测试连接
            await self.health_check()
            
            logger.info("数据库初始化成功")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        获取异步数据库会话
        
        Yields:
            AsyncSession: 异步数据库会话
        """
        if not self.async_session_maker:
            raise RuntimeError("数据库未初始化，请先调用 initialize()")
        
        session = self.async_session_maker()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库会话异常: {e}")
            raise
        finally:
            await session.close()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        数据库健康检查
        
        Returns:
            Dict[str, Any]: 健康检查结果
        """
        if not self.engine:
            return {
                'status': 'error',
                'message': '数据库引擎未初始化',
                'timestamp': time.time()
            }
        
        start_time = time.time()
        
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute("SELECT 1 as health_check")
                health_result = result.fetchone()
                
            response_time = time.time() - start_time
            
            # 获取连接池状态
            pool_status = self.get_pool_status()
            
            return {
                'status': 'healthy',
                'response_time_ms': round(response_time * 1000, 2),
                'database_responsive': health_result[0] == 1,
                'pool_status': pool_status,
                'timestamp': time.time()
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"数据库健康检查失败: {e}")
            
            return {
                'status': 'error',
                'response_time_ms': round(response_time * 1000, 2),
                'error': str(e),
                'timestamp': time.time()
            }
    
    def get_pool_status(self) -> Dict[str, Any]:
        """
        获取连接池状态信息
        
        Returns:
            Dict[str, Any]: 连接池状态
        """
        if not self.engine or not hasattr(self.engine.sync_engine, 'pool'):
            return {'status': '连接池不可用'}
        
        pool = self.engine.sync_engine.pool
        
        try:
            return {
                'pool_size': pool.size(),
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'invalid': pool.invalid(),
                'total_stats': self.connection_pools_stats.copy()
            }
        except Exception as e:
            logger.error(f"获取连接池状态失败: {e}")
            return {'error': str(e)}
    
    async def execute_raw_sql(self, sql: str, params: Dict[str, Any] = None) -> Any:
        """
        执行原生SQL查询
        
        Args:
            sql: SQL语句
            params: 参数字典
            
        Returns:
            查询结果
        """
        async with self.get_session() as session:
            try:
                result = await session.execute(sql, params or {})
                return result.fetchall()
            except Exception as e:
                logger.error(f"执行SQL失败 [{sql}]: {e}")
                raise
    
    async def close(self):
        """关闭数据库连接"""
        if self.engine:
            await self.engine.dispose()
            logger.info("数据库连接已关闭")

class ResourceMonitor:
    """
    资源监控器
    
    监控数据库连接和系统资源使用情况，
    基于OpenWebUI的资源管理策略
    """
    
    def __init__(self, db_manager: DatabaseEngineManager):
        self.db_manager = db_manager
        self.monitoring = False
        self.memory_threshold = 0.85  # 85%内存使用率阈值
        self.connection_threshold = 0.9  # 90%连接池使用率阈值
    
    async def start_monitoring(self, interval: int = 60):
        """
        启动资源监控
        
        Args:
            interval: 监控间隔（秒）
        """
        self.monitoring = True
        logger.info(f"资源监控已启动，监控间隔: {interval}秒")
        
        while self.monitoring:
            try:
                await self.check_resources()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"资源监控异常: {e}")
                await asyncio.sleep(interval)
    
    def stop_monitoring(self):
        """停止资源监控"""
        self.monitoring = False
        logger.info("资源监控已停止")
    
    async def check_resources(self):
        """检查系统资源"""
        # 检查内存使用率
        memory_percent = psutil.virtual_memory().percent / 100
        
        if memory_percent > self.memory_threshold:
            logger.warning(f"内存使用率过高: {memory_percent:.1%}")
            await self.trigger_cleanup()
        
        # 检查数据库连接池
        pool_status = self.db_manager.get_pool_status()
        if 'pool_size' in pool_status:
            pool_usage = pool_status['checked_out'] / max(pool_status['pool_size'], 1)
            
            if pool_usage > self.connection_threshold:
                logger.warning(f"数据库连接池使用率过高: {pool_usage:.1%}")
    
    async def trigger_cleanup(self):
        """触发资源清理"""
        logger.info("触发资源清理")
        
        # Python垃圾回收
        import gc
        gc.collect()
        
        # 可以添加更多清理逻辑，如缓存清理等

# 全局数据库管理器实例
db_manager = DatabaseEngineManager()

# 依赖注入函数
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI依赖注入函数，获取数据库会话
    
    Yields:
        AsyncSession: 异步数据库会话
    """
    async with db_manager.get_session() as session:
        yield session

# 数据库健康检查函数
async def check_database_health() -> Dict[str, Any]:
    """
    数据库健康检查函数，供健康检查端点使用
    
    Returns:
        Dict[str, Any]: 健康检查结果
    """
    return await db_manager.health_check()

# 初始化函数
async def init_database(database_url: str = None):
    """
    初始化数据库连接
    
    Args:
        database_url: 数据库连接URL
    """
    await db_manager.initialize(database_url)

# 关闭函数
async def close_database():
    """关闭数据库连接"""
    await db_manager.close()