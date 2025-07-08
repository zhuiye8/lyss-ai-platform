#!/bin/bash

# Lyss AI Platform 开发环境设置脚本
# 此脚本用于快速设置本地开发环境

set -e

echo "🚀 开始设置 Lyss AI Platform 开发环境..."

# 检查必要工具
check_requirements() {
    echo "📋 检查系统要求..."
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    # 检查 Node.js
    if ! command -v node &> /dev/null; then
        echo "❌ Node.js 未安装，请先安装 Node.js (版本 >= 18)"
        exit 1
    fi
    
    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 未安装，请先安装 Python 3.11+"
        exit 1
    fi
    
    # 检查 Go
    if ! command -v go &> /dev/null; then
        echo "❌ Go 未安装，请先安装 Go 1.21+"
        exit 1
    fi
    
    echo "✅ 系统要求检查通过"
}

# 创建环境配置文件
setup_env_files() {
    echo "📝 设置环境配置文件..."
    
    if [ ! -f .env ]; then
        cp .env.dev .env
        echo "✅ 已创建 .env 文件（基于开发环境配置）"
    else
        echo "⚠️  .env 文件已存在，跳过创建"
    fi
    
    # 为各个服务创建 .env 文件
    if [ ! -f backend/.env ]; then
        cp .env.dev backend/.env
        echo "✅ 已创建 backend/.env 文件"
    fi
    
    if [ ! -f memory-service/.env ]; then
        cp .env.dev memory-service/.env
        echo "✅ 已创建 memory-service/.env 文件"
    fi
    
    if [ ! -f frontend/.env.local ]; then
        cat > frontend/.env.local << EOF
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
NODE_ENV=development
EOF
        echo "✅ 已创建 frontend/.env.local 文件"
    fi
}

# 安装依赖
install_dependencies() {
    echo "📦 安装项目依赖..."
    
    # 安装前端依赖
    echo "📦 安装前端依赖..."
    cd frontend
    npm install
    cd ..
    echo "✅ 前端依赖安装完成"
    
    # 安装 Python 依赖
    echo "📦 安装 Python 依赖..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r backend/requirements.txt
    pip install -r memory-service/requirements.txt
    deactivate
    echo "✅ Python 依赖安装完成"
    
    # 安装 Go 依赖
    echo "📦 安装 Go 依赖..."
    cd eino-service
    go mod download
    cd ..
    echo "✅ Go 依赖安装完成"
}

# 启动基础服务
start_infrastructure() {
    echo "🗄️ 启动基础设施服务..."
    
    # 启动数据库和 Redis
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres redis
    
    # 等待服务启动
    echo "⏳ 等待数据库和 Redis 启动..."
    sleep 10
    
    # 检查服务状态
    if docker-compose ps | grep -q "postgres.*Up"; then
        echo "✅ PostgreSQL 已启动"
    else
        echo "❌ PostgreSQL 启动失败"
        exit 1
    fi
    
    if docker-compose ps | grep -q "redis.*Up"; then
        echo "✅ Redis 已启动"
    else
        echo "❌ Redis 启动失败"
        exit 1
    fi
}

# 初始化数据库
init_database() {
    echo "🗄️ 初始化数据库..."
    
    # 等待数据库完全启动
    echo "⏳ 等待数据库完全启动..."
    sleep 5
    
    # 运行数据库迁移
    source venv/bin/activate
    cd backend
    
    # 这里可以添加数据库迁移命令
    # python -m alembic upgrade head
    
    cd ..
    deactivate
    
    echo "✅ 数据库初始化完成"
}

# 创建开发用户
create_dev_users() {
    echo "👤 创建开发用户..."
    
    # 这里可以添加创建开发用户的脚本
    echo "ℹ️  默认用户已通过种子数据创建"
    echo "   - 管理员: admin@lyss.ai / admin123"
    echo "   - 演示用户: demo@example.com / admin123"
    echo "   - 普通用户: user@example.com / admin123"
}

# 启动开发服务
start_dev_services() {
    echo "🚀 启动开发服务..."
    
    echo "ℹ️  请在不同的终端窗口中运行以下命令启动各个服务："
    echo ""
    echo "1. 启动后端 API 网关:"
    echo "   cd backend && source ../venv/bin/activate && python -m uvicorn api-gateway.main:app --host 0.0.0.0 --port 8000 --reload"
    echo ""
    echo "2. 启动 EINO 服务:"
    echo "   cd eino-service && go run cmd/main.go"
    echo ""
    echo "3. 启动记忆服务:"
    echo "   cd memory-service && source ../venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"
    echo ""
    echo "4. 启动前端:"
    echo "   cd frontend && npm run dev"
    echo ""
    echo "🌐 访问地址:"
    echo "   - 前端应用: http://localhost:3000"
    echo "   - API 文档: http://localhost:8000/docs"
    echo "   - PgAdmin: http://localhost:5050"
    echo "   - Redis Commander: http://localhost:8081"
    echo "   - Prometheus: http://localhost:9090"
    echo "   - Grafana: http://localhost:3001"
}

# 主函数
main() {
    echo "🎯 Lyss AI Platform 开发环境设置"
    echo "=================================="
    
    check_requirements
    setup_env_files
    install_dependencies
    start_infrastructure
    init_database
    create_dev_users
    start_dev_services
    
    echo ""
    echo "🎉 开发环境设置完成！"
    echo ""
    echo "📚 更多信息请查看 README.md 文件"
    echo "🐛 如有问题，请查看 docs/ 目录下的文档"
}

# 处理命令行参数
case "${1:-}" in
    --help|-h)
        echo "Lyss AI Platform 开发环境设置脚本"
        echo ""
        echo "用法: $0 [选项]"
        echo ""
        echo "选项:"
        echo "  --help, -h     显示此帮助信息"
        echo "  --only-deps    仅安装依赖"
        echo "  --only-infra   仅启动基础设施"
        echo ""
        exit 0
        ;;
    --only-deps)
        check_requirements
        setup_env_files
        install_dependencies
        echo "✅ 依赖安装完成"
        ;;
    --only-infra)
        start_infrastructure
        echo "✅ 基础设施启动完成"
        ;;
    *)
        main
        ;;
esac