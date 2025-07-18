#!/usr/bin/env python3
"""
API Gateway 开发环境启动脚本

用于在开发环境中启动API Gateway服务
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.api_gateway.config import settings
from backend.api_gateway.core.logging import setup_logging, get_logger

# 设置日志
setup_logging()
logger = get_logger(__name__)


def check_environment():
    """检查开发环境"""
    
    print("🔍 检查开发环境...")
    
    # 检查Python版本
    python_version = sys.version_info
    if python_version < (3, 11):
        print(f"❌ Python版本过低: {python_version.major}.{python_version.minor}")
        print("   需要Python 3.11或更高版本")
        sys.exit(1)
    else:
        print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 检查虚拟环境
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  建议在虚拟环境中运行")
    else:
        print("✅ 虚拟环境已激活")
    
    # 检查依赖包
    try:
        import fastapi
        import uvicorn
        import httpx
        import pydantic
        print("✅ 核心依赖包已安装")
    except ImportError as e:
        print(f"❌ 依赖包缺失: {e}")
        print("   请运行: pip install -r requirements.txt")
        sys.exit(1)
    
    # 检查环境变量
    env_file = project_root / "backend" / ".env"
    if not env_file.exists():
        print("⚠️  .env文件不存在，将使用默认配置")
        print("   建议复制.env.example为.env并配置")
    else:
        print("✅ .env文件已存在")
    
    print()


def check_downstream_services():
    """检查下游服务状态"""
    
    print("🔍 检查下游服务状态...")
    
    import asyncio
    import httpx
    
    services = {
        "Auth Service": settings.auth_service_url,
        "Tenant Service": settings.tenant_service_url,
        "EINO Service": settings.eino_service_url,
        "Memory Service": settings.memory_service_url
    }
    
    async def check_service(name: str, url: str):
        """检查单个服务"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    print(f"✅ {name}: {url}")
                    return True
                else:
                    print(f"⚠️  {name}: {url} (状态码: {response.status_code})")
                    return False
        except Exception as e:
            print(f"❌ {name}: {url} (错误: {str(e)})")
            return False
    
    async def check_all_services():
        """检查所有服务"""
        tasks = [check_service(name, url) for name, url in services.items()]
        results = await asyncio.gather(*tasks)
        return sum(results), len(results)
    
    # 运行检查
    healthy_count, total_count = asyncio.run(check_all_services())
    
    print(f"\n📊 服务状态: {healthy_count}/{total_count} 健康")
    
    if healthy_count == 0:
        print("⚠️  所有下游服务都不可用，API Gateway仍可启动但功能受限")
    elif healthy_count < total_count:
        print("⚠️  部分下游服务不可用，某些功能可能受限")
    else:
        print("✅ 所有下游服务正常")
    
    print()


def start_server(host: str = None, port: int = None, reload: bool = True):
    """启动服务器"""
    
    host = host or settings.host
    port = port or settings.port
    
    print(f"🚀 启动API Gateway...")
    print(f"   主机: {host}")
    print(f"   端口: {port}")
    print(f"   热重载: {reload}")
    print(f"   调试模式: {settings.debug}")
    print(f"   环境: {settings.environment}")
    print()
    
    # 构建启动命令
    cmd = [
        sys.executable,
        "-m", "uvicorn",
        "backend.api_gateway.main:app",
        "--host", host,
        "--port", str(port),
        "--log-config", "null",  # 使用我们自己的日志配置
        "--access-log"
    ]
    
    if reload:
        cmd.append("--reload")
    
    if settings.debug:
        cmd.extend(["--log-level", "debug"])
    
    try:
        # 启动服务器
        subprocess.run(cmd, cwd=project_root, check=True)
    except KeyboardInterrupt:
        print("\n👋 API Gateway已停止")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)


def main():
    """主函数"""
    
    parser = argparse.ArgumentParser(description="API Gateway开发环境启动脚本")
    parser.add_argument("--host", default=None, help="监听主机")
    parser.add_argument("--port", type=int, default=None, help="监听端口")
    parser.add_argument("--no-reload", action="store_true", help="禁用热重载")
    parser.add_argument("--skip-checks", action="store_true", help="跳过环境检查")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("🌟 Lyss AI Platform - API Gateway")
    print("=" * 50)
    
    # 检查环境
    if not args.skip_checks:
        check_environment()
        check_downstream_services()
    
    # 启动服务器
    start_server(
        host=args.host,
        port=args.port,
        reload=not args.no_reload
    )


if __name__ == "__main__":
    main()