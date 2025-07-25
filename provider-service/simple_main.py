"""
简化的Provider Service主程序，用于测试
"""
from fastapi import FastAPI
from app.core.config import get_settings
from app.api.v1.proxy import router as proxy_router

# 获取配置
settings = get_settings()

# 创建FastAPI应用
app = FastAPI(
    title="Lyss Provider Service",
    description="AI供应商管理和透明代理服务",
    version="1.0.0"
)

# 添加路由
app.include_router(proxy_router, prefix="/api")

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "provider-service",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)