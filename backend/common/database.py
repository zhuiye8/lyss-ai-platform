"""
Database connection and session management
"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import get_settings

settings = get_settings()

# Create async engine
async_engine = create_async_engine(
    settings.database.url,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_timeout=settings.database.pool_timeout,
    echo=settings.debug,
    poolclass=StaticPool if settings.is_development else None
)

# Create sync engine for migrations
sync_engine = create_engine(
    settings.database.sync_url,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_timeout=settings.database.pool_timeout,
    echo=settings.debug
)

# Session makers
AsyncSessionLocal = async_sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)

# Base class for models
Base = declarative_base()


class DatabaseManager:
    """Database connection manager"""
    
    def __init__(self):
        self.async_engine = async_engine
        self.sync_engine = sync_engine
        self._is_connected = False
    
    async def connect(self) -> None:
        """Initialize database connection"""
        if self._is_connected:
            return
        
        try:
            # Test connection
            async with self.async_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            self._is_connected = True
            print("Database connected successfully")
        except Exception as e:
            print(f"Database connection failed: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close database connection"""
        if not self._is_connected:
            return
        
        try:
            await self.async_engine.dispose()
            self._is_connected = False
            print("Database disconnected successfully")
        except Exception as e:
            print(f"Database disconnection failed: {e}")
            raise
    
    async def create_tables(self) -> None:
        """Create all tables"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def drop_tables(self) -> None:
        """Drop all tables"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            async with self.async_engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception:
            return False


# Global database manager instance
db_manager = DatabaseManager()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session():
    """Get sync database session"""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def get_tenant_session(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Get database session for specific tenant"""
    # TODO: Implement tenant-specific database routing
    async with get_async_session() as session:
        # Set tenant context
        await session.execute(text("SET app.current_tenant = :tenant_id"), {"tenant_id": tenant_id})
        yield session


class TenantDatabaseManager:
    """Manages tenant-specific database operations"""
    
    def __init__(self):
        self.tenant_engines = {}
    
    async def get_tenant_engine(self, tenant_id: str):
        """Get or create tenant-specific database engine"""
        if tenant_id not in self.tenant_engines:
            # For now, use the main database with tenant isolation
            # In production, this could route to tenant-specific databases
            self.tenant_engines[tenant_id] = async_engine
        return self.tenant_engines[tenant_id]
    
    async def create_tenant_schema(self, tenant_id: str) -> None:
        """Create tenant-specific schema"""
        schema_name = f"tenant_{tenant_id}"
        async with async_engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
    
    async def drop_tenant_schema(self, tenant_id: str) -> None:
        """Drop tenant-specific schema"""
        schema_name = f"tenant_{tenant_id}"
        async with async_engine.begin() as conn:
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
    
    async def migrate_tenant_data(self, tenant_id: str) -> None:
        """Migrate tenant data to new schema"""
        # TODO: Implement tenant data migration logic
        pass


# Global tenant database manager
tenant_db_manager = TenantDatabaseManager()


# Database lifecycle management
async def init_database() -> None:
    """Initialize database on startup"""
    await db_manager.connect()
    await db_manager.create_tables()


async def close_database() -> None:
    """Close database on shutdown"""
    await db_manager.disconnect()


# Dependency functions for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session"""
    async with get_async_session() as session:
        yield session


async def get_tenant_db(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for tenant-specific database session"""
    async with get_tenant_session(tenant_id) as session:
        yield session