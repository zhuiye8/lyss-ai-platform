#!/bin/bash

# 启动本地开发服务脚本
# 在不同终端窗口中启动各个应用服务

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Lyss AI Platform 本地开发服务启动助手${NC}"
echo ""

# 检查基础服务是否运行
echo -e "${YELLOW}🔍 检查基础设施服务状态...${NC}"

# 检查PostgreSQL
if ! nc -z localhost 5432 2>/dev/null; then
    echo -e "${RED}❌ PostgreSQL 未运行在 localhost:5432${NC}"
    echo -e "${YELLOW}💡 请先运行: ./scripts/start-infra.sh${NC}"
    exit 1
fi

# 检查Redis
if ! nc -z localhost 6379 2>/dev/null; then
    echo -e "${RED}❌ Redis 未运行在 localhost:6379${NC}"
    echo -e "${YELLOW}💡 请先运行: ./scripts/start-infra.sh${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 基础设施服务运行正常${NC}"
echo ""

# 检查环境配置
if [ ! -f ".env.local" ]; then
    echo -e "${YELLOW}⚠️  .env.local 文件不存在，创建默认配置...${NC}"
    cp .env.local.example .env.local 2>/dev/null || echo "请手动创建 .env.local 文件"
fi

# 检查Python虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 创建Python虚拟环境...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r backend/requirements.txt
    pip install -r memory-service/requirements.txt
    echo -e "${GREEN}✅ Python虚拟环境创建完成${NC}"
else
    echo -e "${GREEN}✅ Python虚拟环境已存在${NC}"
fi

# 检查前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}📦 安装前端依赖...${NC}"
    cd frontend
    npm install
    cd ..
    echo -e "${GREEN}✅ 前端依赖安装完成${NC}"
else
    echo -e "${GREEN}✅ 前端依赖已安装${NC}"
fi

# 检查Go依赖
echo -e "${YELLOW}📦 检查Go依赖...${NC}"
cd eino-service
go mod download
cd ..
echo -e "${GREEN}✅ Go依赖检查完成${NC}"

echo ""
echo -e "${BLUE}🚀 服务启动说明${NC}"
echo ""
echo -e "${YELLOW}请在不同的终端窗口中运行以下命令：${NC}"
echo ""

echo -e "${BLUE}1. 启动后端API网关 (端口8000):${NC}"
echo "   cd backend"
echo "   source ../venv/bin/activate"
echo "   python -m uvicorn api-gateway.main:app --reload --host 0.0.0.0 --port 8000 --env-file ../.env.local"
echo ""

echo -e "${BLUE}2. 启动EINO服务 (端口8080):${NC}"
echo "   cd eino-service"
echo "   export \$(cat ../.env.local | grep -v ^# | xargs)"
echo "   go run cmd/main.go"
echo ""

echo -e "${BLUE}3. 启动记忆服务 (端口8001):${NC}"
echo "   cd memory-service"
echo "   source ../venv/bin/activate"
echo "   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 --env-file ../.env.local"
echo ""

echo -e "${BLUE}4. 启动前端应用 (端口3000):${NC}"
echo "   cd frontend"
echo "   npm run dev"
echo ""

echo -e "${GREEN}🌐 访问地址：${NC}"
echo "  前端应用: http://localhost:3000"
echo "  API文档: http://localhost:8000/docs"
echo "  PgAdmin: http://localhost:5050 (dev@lyss.ai / devpassword)"
echo "  Redis Commander: http://localhost:8081"
echo ""

echo -e "${GREEN}👤 默认账户：${NC}"
echo "  管理员: admin@lyss.ai / admin123"
echo "  演示用户: demo@example.com / admin123"
echo ""

echo -e "${BLUE}💡 开发提示：${NC}"
echo "  • 所有服务都支持热重载，代码修改后自动重启"
echo "  • 数据库和Redis在Docker中运行，数据持久化保存"
echo "  • 可以使用 docker-compose -f docker-compose.infrastructure.yml logs -f 查看基础服务日志"
echo "  • 停止基础服务: docker-compose -f docker-compose.infrastructure.yml down"
echo ""

# 询问是否要启动终端窗口（如果支持）
if command -v gnome-terminal &> /dev/null; then
    read -p "是否要自动打开终端窗口启动服务？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}🚀 启动服务终端窗口...${NC}"
        
        # 启动API网关
        gnome-terminal --title="API Gateway" -- bash -c "cd backend && source ../venv/bin/activate && python -m uvicorn api-gateway.main:app --reload --host 0.0.0.0 --port 8000 --env-file ../.env.local; read"
        
        sleep 1
        
        # 启动EINO服务
        gnome-terminal --title="EINO Service" -- bash -c "cd eino-service && export \$(cat ../.env.local | grep -v ^# | xargs) && go run cmd/main.go; read"
        
        sleep 1
        
        # 启动记忆服务
        gnome-terminal --title="Memory Service" -- bash -c "cd memory-service && source ../venv/bin/activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 --env-file ../.env.local; read"
        
        sleep 1
        
        # 启动前端
        gnome-terminal --title="Frontend" -- bash -c "cd frontend && npm run dev; read"
        
        echo -e "${GREEN}✅ 服务启动完成！请查看新打开的终端窗口${NC}"
    fi
elif command -v osascript &> /dev/null; then
    # macOS 支持
    read -p "是否要自动打开终端窗口启动服务？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}🚀 启动服务终端窗口...${NC}"
        
        # 使用 macOS Terminal 启动服务
        osascript -e "tell application \"Terminal\" to do script \"cd '$PWD/backend' && source ../venv/bin/activate && python -m uvicorn api-gateway.main:app --reload --host 0.0.0.0 --port 8000 --env-file ../.env.local\""
        osascript -e "tell application \"Terminal\" to do script \"cd '$PWD/eino-service' && export \\\$(cat ../.env.local | grep -v ^# | xargs) && go run cmd/main.go\""
        osascript -e "tell application \"Terminal\" to do script \"cd '$PWD/memory-service' && source ../venv/bin/activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 --env-file ../.env.local\""
        osascript -e "tell application \"Terminal\" to do script \"cd '$PWD/frontend' && npm run dev\""
        
        echo -e "${GREEN}✅ 服务启动完成！请查看新打开的终端窗口${NC}"
    fi
fi