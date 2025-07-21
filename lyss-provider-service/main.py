"""
Lyss Provider Service - 多供应商管理服务

统一管理多个AI服务提供商（OpenAI、Anthropic、Google、DeepSeek等），
实现供应商抽象、凭证管理、负载均衡和故障转移。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )