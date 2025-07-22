#!/bin/bash

"""
开发环境启动脚本

启动Lyss Provider Service开发环境，包括数据库初始化和服务启动。

Author: Lyss AI Team
Created: 2025-01-21
"""

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 输出格式化消息
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_step "检查依赖项..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    
    # 检查pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 未安装"
        exit 1
    fi
    
    # 检查PostgreSQL客户端
    if ! command -v psql &> /dev/null; then
        log_warn "psql 未安装，跳过数据库连接测试"
    fi
    
    log_info "依赖项检查完成"
}

# 设置虚拟环境
setup_venv() {
    log_step "设置Python虚拟环境..."
    
    if [ ! -d "venv" ]; then
        log_info "创建虚拟环境..."
        python3 -m venv venv
    fi
    
    log_info "激活虚拟环境..."
    source venv/bin/activate
    
    log_info "升级pip..."
    pip install --upgrade pip
    
    log_info "安装依赖..."
    pip install -r requirements.txt
    
    log_info "虚拟环境设置完成"
}

# 检查环境变量
check_env() {
    log_step "检查环境变量..."
    
    if [ ! -f ".env" ]; then
        log_warn ".env 文件不存在，创建默认配置..."
        cat > .env << EOF
# Provider Service Configuration
ENVIRONMENT=development
PROVIDER_SERVICE_HOST=0.0.0.0
PROVIDER_SERVICE_PORT=8003

# Database Configuration  
PROVIDER_SERVICE_DATABASE_URL=postgresql://lyss:lyss123@localhost:5433/lyss_provider_db

# Redis Configuration
PROVIDER_SERVICE_REDIS_URL=redis://localhost:6380/2
REDIS_HOST=localhost
REDIS_PORT=6380
REDIS_PASSWORD=

# JWT Configuration
PROVIDER_SERVICE_JWT_SECRET=your-super-secret-jwt-key-min-32-chars-here-for-development
JWT_ALGORITHM=HS256

# Security Configuration  
PROVIDER_SERVICE_ENCRYPTION_KEY=your-32-char-encryption-key-here
ENABLE_DOCS=true
ALLOWED_HOSTS=["*"]

# Load Balancer Configuration
LOAD_BALANCER_ALGORITHM=weighted_random

# Logging Configuration
LOG_LEVEL=INFO
ENABLE_REQUEST_LOGGING=true
EOF
        log_info "默认.env文件已创建"
    fi
    
    log_info "环境变量检查完成"
}

# 等待数据库服务
wait_for_db() {
    log_step "等待数据库服务启动..."
    
    local retries=30
    local count=0
    
    while [ $count -lt $retries ]; do
        if psql -h localhost -p 5433 -U lyss -d lyss_provider_db -c "SELECT 1;" &> /dev/null; then
            log_info "数据库连接成功"
            return 0
        fi
        
        count=$((count + 1))
        log_info "等待数据库启动... ($count/$retries)"
        sleep 2
    done
    
    log_error "数据库连接超时"
    return 1
}

# 等待Redis服务
wait_for_redis() {
    log_step "等待Redis服务启动..."
    
    local retries=30
    local count=0
    
    while [ $count -lt $retries ]; do
        if redis-cli -h localhost -p 6380 ping &> /dev/null; then
            log_info "Redis连接成功"
            return 0
        fi
        
        count=$((count + 1))
        log_info "等待Redis启动... ($count/$retries)"
        sleep 2
    done
    
    log_warn "Redis连接失败，服务将在启动时重试"
    return 0
}

# 初始化数据库
init_database() {
    log_step "初始化数据库..."
    
    log_info "运行数据库迁移..."
    python -c "
from app.core.database import create_database_tables
create_database_tables()
print('数据库表创建完成')
"
    
    log_info "数据库初始化完成"
}

# 启动服务
start_service() {
    log_step "启动Provider Service..."
    
    log_info "启动参数："
    log_info "  - 环境: development"
    log_info "  - 主机: 0.0.0.0"
    log_info "  - 端口: 8003"
    log_info "  - 文档: http://localhost:8003/docs"
    log_info "  - 健康检查: http://localhost:8003/health"
    
    echo
    log_info "🚀 启动服务..."
    uvicorn main:app --host 0.0.0.0 --port 8003 --reload --log-level info
}

# 清理函数
cleanup() {
    log_warn "收到中断信号，正在清理..."
    exit 0
}

# 主函数
main() {
    log_info "🚀 Lyss Provider Service 开发环境启动脚本"
    log_info "=============================================="
    
    # 设置中断处理
    trap cleanup SIGINT SIGTERM
    
    # 执行启动流程
    check_dependencies
    setup_venv
    check_env
    wait_for_db
    wait_for_redis
    init_database
    start_service
}

# 运行主函数
main "$@"