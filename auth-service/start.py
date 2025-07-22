#!/usr/bin/env python3
"""
lyss-auth-service 启动脚本

快速启动认证服务用于开发和测试
"""

import asyncio
import sys
import uvicorn
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from auth_service.config import settings
from auth_service.utils.logging import get_logger

logger = get_logger(__name__)


async def check_dependencies():
    """检查服务依赖"""
    logger.info("正在检查服务依赖...")
    
    try:
        # 检查Redis连接
        from auth_service.utils.redis_client import redis_client
        await redis_client.connect()
        logger.info("✅ Redis连接正常")
        await redis_client.disconnect()
        
    except Exception as e:
        logger.error(f"❌ 依赖检查失败: {str(e)}")
        logger.error("请确保以下服务正在运行:")
        logger.error("  - Redis服务 (localhost:6379)")
        logger.error("  - PostgreSQL服务 (localhost:5433)")
        return False
    
    logger.info("✅ 所有依赖检查通过")
    return True


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("🚀 启动 Lyss Auth Service")
    logger.info("=" * 60)
    
    # 打印配置信息
    logger.info(f"环境: {settings.environment}")
    logger.info(f"调试模式: {settings.debug}")
    logger.info(f"服务地址: http://{settings.auth_service_host}:{settings.auth_service_port}")
    logger.info(f"API文档: http://{settings.auth_service_host}:{settings.auth_service_port}/docs")
    
    # 检查生产环境配置
    if settings.is_production():
        config_issues = settings.validate_production_config()
        if config_issues:
            logger.warning("⚠️ 生产环境配置问题:")
            for issue in config_issues:
                logger.warning(f"  - {issue}")
    
    # 运行依赖检查
    logger.info("🔍 开始依赖检查...")
    try:
        deps_ok = asyncio.run(check_dependencies())
        if not deps_ok:
            logger.error("❌ 依赖检查失败，服务无法启动")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("👋 用户中断启动")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ 启动检查异常: {str(e)}")
        sys.exit(1)
    
    logger.info("🎯 准备启动服务...")
    
    try:
        # 启动服务
        uvicorn.run(
            "auth_service.main:app",
            host=settings.auth_service_host,
            port=settings.auth_service_port,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
            access_log=False,  # 使用自定义日志中间件
            workers=1,  # 开发环境单进程
        )
    except KeyboardInterrupt:
        logger.info("👋 服务已停止")
    except Exception as e:
        logger.error(f"❌ 服务启动失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()