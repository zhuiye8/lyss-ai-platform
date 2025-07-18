#!/usr/bin/env python3
"""
API Gateway 健康检查脚本

用于检查API Gateway和下游服务的健康状态
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Dict, Any
import httpx

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.api_gateway.config import settings


class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.timeout = 10.0
        self.client = httpx.AsyncClient(timeout=self.timeout)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def check_api_gateway(self) -> Dict[str, Any]:
        """检查API Gateway健康状态"""
        
        gateway_url = f"http://{settings.host}:{settings.port}"
        
        try:
            response = await self.client.get(f"{gateway_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "service": "API Gateway",
                    "status": "healthy",
                    "url": gateway_url,
                    "response_time_ms": int(response.elapsed.total_seconds() * 1000),
                    "data": data
                }
            else:
                return {
                    "service": "API Gateway",
                    "status": "unhealthy",
                    "url": gateway_url,
                    "status_code": response.status_code,
                    "error": response.text
                }
                
        except Exception as e:
            return {
                "service": "API Gateway",
                "status": "unhealthy",
                "url": gateway_url,
                "error": str(e)
            }
    
    async def check_downstream_services(self) -> Dict[str, Any]:
        """检查下游服务健康状态"""
        
        services = {
            "Auth Service": settings.auth_service_url,
            "Tenant Service": settings.tenant_service_url,
            "EINO Service": settings.eino_service_url,
            "Memory Service": settings.memory_service_url
        }
        
        results = {}
        
        for service_name, service_url in services.items():
            try:
                response = await self.client.get(f"{service_url}/health")
                
                if response.status_code == 200:
                    results[service_name] = {
                        "status": "healthy",
                        "url": service_url,
                        "response_time_ms": int(response.elapsed.total_seconds() * 1000),
                        "data": response.json() if response.content else {}
                    }
                else:
                    results[service_name] = {
                        "status": "unhealthy",
                        "url": service_url,
                        "status_code": response.status_code,
                        "error": response.text
                    }
                    
            except Exception as e:
                results[service_name] = {
                    "status": "unhealthy",
                    "url": service_url,
                    "error": str(e)
                }
        
        return results
    
    async def check_all(self) -> Dict[str, Any]:
        """检查所有服务"""
        
        print("🔍 检查API Gateway和下游服务健康状态...")
        print()
        
        # 并发检查
        gateway_task = self.check_api_gateway()
        services_task = self.check_downstream_services()
        
        gateway_result, services_results = await asyncio.gather(
            gateway_task, services_task
        )
        
        # 计算总体状态
        all_services = {"API Gateway": gateway_result, **services_results}
        
        healthy_count = sum(1 for service in all_services.values() 
                          if service["status"] == "healthy")
        total_count = len(all_services)
        
        overall_status = "healthy" if healthy_count == total_count else \
                        "degraded" if healthy_count > 0 else "unhealthy"
        
        return {
            "overall_status": overall_status,
            "healthy_count": healthy_count,
            "total_count": total_count,
            "services": all_services
        }


def format_output(results: Dict[str, Any], format_type: str = "table"):
    """格式化输出结果"""
    
    if format_type == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return
    
    # 表格格式
    overall_status = results["overall_status"]
    healthy_count = results["healthy_count"]
    total_count = results["total_count"]
    services = results["services"]
    
    # 状态图标
    status_icons = {
        "healthy": "✅",
        "unhealthy": "❌",
        "degraded": "⚠️"
    }
    
    print(f"{status_icons.get(overall_status, '❓')} 总体状态: {overall_status.upper()}")
    print(f"📊 健康服务: {healthy_count}/{total_count}")
    print()
    
    # 服务详情
    print("服务详情:")
    print("-" * 80)
    print(f"{'服务名称':<20} {'状态':<10} {'响应时间':<10} {'URL':<30}")
    print("-" * 80)
    
    for service_name, service_info in services.items():
        status = service_info["status"]
        status_icon = status_icons.get(status, "❓")
        
        response_time = service_info.get("response_time_ms", "-")
        response_time_str = f"{response_time}ms" if response_time != "-" else "-"
        
        url = service_info.get("url", "")
        if len(url) > 30:
            url = url[:27] + "..."
        
        print(f"{service_name:<20} {status_icon} {status:<8} {response_time_str:<10} {url}")
        
        # 如果有错误，显示错误信息
        if status == "unhealthy" and "error" in service_info:
            error_msg = service_info["error"]
            if len(error_msg) > 60:
                error_msg = error_msg[:57] + "..."
            print(f"{'':>20} 错误: {error_msg}")
    
    print()
    
    # 建议
    if overall_status == "unhealthy":
        print("💡 建议:")
        print("   - 检查服务是否正在运行")
        print("   - 检查网络连接")
        print("   - 查看服务日志")
    elif overall_status == "degraded":
        print("💡 建议:")
        print("   - 检查失败的服务")
        print("   - 某些功能可能受限")


async def main():
    """主函数"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="API Gateway健康检查脚本")
    parser.add_argument("--format", choices=["table", "json"], default="table",
                       help="输出格式")
    parser.add_argument("--gateway-only", action="store_true",
                       help="只检查API Gateway")
    parser.add_argument("--services-only", action="store_true",
                       help="只检查下游服务")
    
    args = parser.parse_args()
    
    async with HealthChecker() as checker:
        if args.gateway_only:
            result = await checker.check_api_gateway()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif args.services_only:
            results = await checker.check_downstream_services()
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            results = await checker.check_all()
            format_output(results, args.format)
            
            # 设置退出码
            if results["overall_status"] == "unhealthy":
                sys.exit(1)
            elif results["overall_status"] == "degraded":
                sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())