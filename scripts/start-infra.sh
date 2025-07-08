#!/bin/bash

# 启动基础设施服务脚本
# 仅启动数据库、Redis等基础服务，应用服务在本地运行

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 启动 Lyss AI Platform 基础设施服务...${NC}"

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker 未运行，请先启动 Docker${NC}"
    exit 1
fi

# 检查 Docker Compose 是否可用
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose 未安装${NC}"
    exit 1
fi

# 启动基础服务
echo -e "${YELLOW}📦 启动基础设施服务...${NC}"
docker-compose -f docker-compose.infrastructure.yml up -d

# 等待服务启动
echo -e "${YELLOW}⏳ 等待服务启动...${NC}"
sleep 5

# 检查服务状态
echo -e "${YELLOW}🔍 检查服务状态...${NC}"

# 检查 PostgreSQL
if docker-compose -f docker-compose.infrastructure.yml ps postgres | grep -q "Up"; then
    echo -e "${GREEN}✅ PostgreSQL 启动成功${NC}"
else
    echo -e "${RED}❌ PostgreSQL 启动失败${NC}"
fi

# 检查 Redis
if docker-compose -f docker-compose.infrastructure.yml ps redis | grep -q "Up"; then
    echo -e "${GREEN}✅ Redis 启动成功${NC}"
else
    echo -e "${RED}❌ Redis 启动失败${NC}"
fi

# 等待数据库完全就绪
echo -e "${YELLOW}⏳ 等待数据库完全就绪...${NC}"
timeout=60
while [ $timeout -gt 0 ]; do
    if docker-compose -f docker-compose.infrastructure.yml exec -T postgres pg_isready -U lyss_dev_user -d lyss_platform_dev > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 数据库已就绪${NC}"
        break
    fi
    echo -n "."
    sleep 2
    timeout=$((timeout-2))
done

if [ $timeout -le 0 ]; then
    echo -e "${RED}❌ 数据库启动超时${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 基础设施服务启动完成！${NC}"
echo ""
echo -e "${BLUE}📋 服务信息：${NC}"
echo "  🗄️  PostgreSQL: localhost:5432"
echo "      - 数据库: lyss_platform_dev"
echo "      - 用户名: lyss_dev_user"
echo "      - 密码: lyss_dev_password"
echo ""
echo "  📦 Redis: localhost:6379"
echo "      - 密码: lyss_redis_dev_password"
echo ""
echo -e "${BLUE}🌐 管理工具：${NC}"
echo "  📊 PgAdmin: http://localhost:5050"
echo "      - 邮箱: dev@lyss.ai"
echo "      - 密码: devpassword"
echo ""
echo "  🔧 Redis Commander: http://localhost:8081"
echo ""
echo -e "${BLUE}📝 环境变量设置：${NC}"
echo "export DB_HOST=localhost"
echo "export DB_PORT=5432"
echo "export DB_USERNAME=lyss_dev_user"
echo "export DB_PASSWORD=lyss_dev_password"
echo "export DB_DATABASE=lyss_platform_dev"
echo "export REDIS_HOST=localhost"
echo "export REDIS_PORT=6379"
echo "export REDIS_PASSWORD=lyss_redis_dev_password"
echo ""
echo -e "${BLUE}🚀 下一步：${NC}"
echo "现在可以在本地启动应用服务了："
echo ""
echo "1. 后端 API 网关："
echo "   cd backend && python -m uvicorn api-gateway.main:app --reload --port 8000"
echo ""
echo "2. EINO 服务："
echo "   cd eino-service && go run cmd/main.go"
echo ""
echo "3. 记忆服务："
echo "   cd memory-service && python -m uvicorn app.main:app --reload --port 8001"
echo ""
echo "4. 前端应用："
echo "   cd frontend && npm run dev"
echo ""
echo -e "${BLUE}🛠️  管理命令：${NC}"
echo "  查看日志: docker-compose -f docker-compose.infrastructure.yml logs -f"
echo "  停止服务: docker-compose -f docker-compose.infrastructure.yml down"
echo "  重置数据: docker-compose -f docker-compose.infrastructure.yml down -v"
echo ""

# 可选：启动监控服务
if [ "$1" = "--with-monitoring" ]; then
    echo -e "${YELLOW}📊 启动监控服务...${NC}"
    docker-compose -f docker-compose.infrastructure.yml --profile monitoring up -d
    echo -e "${GREEN}✅ 监控服务已启动${NC}"
    echo "  📈 Prometheus: http://localhost:9090"
    echo "  📊 Grafana: http://localhost:3001 (admin/admin)"
fi