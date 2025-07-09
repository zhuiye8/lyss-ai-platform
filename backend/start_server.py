#!/usr/bin/env python3
"""
启动脚本 - 修复模块导入问题
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入 uvicorn 和应用
import uvicorn
from api_gateway.main import app

if __name__ == "__main__":
    uvicorn.run(
        "api_gateway.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )