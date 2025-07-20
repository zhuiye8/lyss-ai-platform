# 部署架构设计

## 📋 文档概述

重新设计的Docker Compose部署架构，按生产环境标准配置，支持健康检查、监控和扩展。

---

## 🐳 Docker Compose 生产配置

### **主配置文件 (docker-compose.yml)**
```yaml
version: '3.8'

services:
  # === 基础设施服务 ===
  postgres:
    image: postgres:15-alpine
    container_name: lyss-postgres
    environment:
      POSTGRES_DB: lyss_main
      POSTGRES_USER: lyss_admin
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_INITDB_ARGS: "--auth-host=scram-sha-256"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/init-databases.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
      - ./sql/migrations:/docker-entrypoint-initdb.d/migrations:ro
    ports:
      - "5432:5432"
    networks:
      - lyss-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lyss_admin -d lyss_main"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'

  redis:
    image: redis:7-alpine
    container_name: lyss-redis
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis_data:/data
      - ./infrastructure/redis/redis.conf:/usr/local/etc/redis/redis.conf:ro
    ports:
      - "6379:6379"
    networks:
      - lyss-network
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 10s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.25'

  qdrant:
    image: qdrant/qdrant:v1.7.4
    container_name: lyss-qdrant
    environment:
      QDRANT__SERVICE__HTTP_PORT: 6333
      QDRANT__SERVICE__GRPC_PORT: 6334
      QDRANT__LOG_LEVEL: INFO
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
      - "6334:6334"
    networks:
      - lyss-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '0.5'

  # === 核心服务 ===
  lyss-api-gateway:
    build: 
      context: ./lyss-api-gateway
      target: production
    container_name: lyss-api-gateway
    environment:
      - DATABASE_URL=postgresql://lyss_admin:${POSTGRES_PASSWORD}@postgres:5432/lyss_main
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - JWT_SECRET=${JWT_SECRET}
      - AUTH_SERVICE_URL=http://lyss-auth-service:8001
      - USER_SERVICE_URL=http://lyss-user-service:8002
      - PROVIDER_SERVICE_URL=http://lyss-provider-service:8003
      - CHAT_SERVICE_URL=http://lyss-chat-service:8004
      - MEMORY_SERVICE_URL=http://lyss-memory-service:8005
    ports:
      - "8000:8000"
    networks:
      - lyss-network
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'

  lyss-auth-service:
    build: 
      context: ./lyss-auth-service
      target: production
    container_name: lyss-auth-service
    environment:
      - DATABASE_URL=postgresql://lyss_admin:${POSTGRES_PASSWORD}@postgres:5432/lyss_user_db
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
      - JWT_SECRET=${JWT_SECRET}
      - USER_SERVICE_URL=http://lyss-user-service:8002
    ports:
      - "8001:8001"
    networks:
      - lyss-network
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.25'

  lyss-user-service:
    build: 
      context: ./lyss-user-service
      target: production
    container_name: lyss-user-service
    environment:
      - DATABASE_URL=postgresql://lyss_admin:${POSTGRES_PASSWORD}@postgres:5432/lyss_user_db
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/2
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    ports:
      - "8002:8002"
    networks:
      - lyss-network
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.25'

  lyss-provider-service:
    build: 
      context: ./lyss-provider-service
      target: production
    container_name: lyss-provider-service
    environment:
      - DATABASE_URL=postgresql://lyss_admin:${POSTGRES_PASSWORD}@postgres:5432/lyss_provider_db
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/3
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - USER_SERVICE_URL=http://lyss-user-service:8002
    ports:
      - "8003:8003"
    networks:
      - lyss-network
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.25'

  lyss-chat-service:
    build: 
      context: ./lyss-chat-service
      target: production
    container_name: lyss-chat-service
    environment:
      - DATABASE_URL=postgresql://lyss_admin:${POSTGRES_PASSWORD}@postgres:5432/lyss_chat_db
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/4
      - PROVIDER_SERVICE_URL=http://lyss-provider-service:8003
      - MEMORY_SERVICE_URL=http://lyss-memory-service:8005
      - USER_SERVICE_URL=http://lyss-user-service:8002
    ports:
      - "8004:8004"
    networks:
      - lyss-network
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      lyss-provider-service:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8004/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 90s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'

  lyss-memory-service:
    build: 
      context: ./lyss-memory-service
      target: production
    container_name: lyss-memory-service
    environment:
      - DATABASE_URL=postgresql://lyss_admin:${POSTGRES_PASSWORD}@postgres:5432/lyss_memory_db
      - QDRANT_URL=http://qdrant:6333
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/5
      - USER_SERVICE_URL=http://lyss-user-service:8002
    ports:
      - "8005:8005"
    networks:
      - lyss-network
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8005/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 90s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'

  # === 前端服务 ===
  lyss-frontend:
    build: 
      context: ./lyss-frontend
      target: production
    container_name: lyss-frontend
    environment:
      - REACT_APP_API_URL=http://localhost:8000
      - REACT_APP_VERSION=${APP_VERSION:-dev}
    ports:
      - "3000:3000"
    networks:
      - lyss-network
    depends_on:
      lyss-api-gateway:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.25'

# === 数据卷 ===
volumes:
  postgres_data:
    driver: local
    name: lyss_postgres_data
  redis_data:
    driver: local  
    name: lyss_redis_data
  qdrant_data:
    driver: local
    name: lyss_qdrant_data

# === 网络配置 ===
networks:
  lyss-network:
    driver: bridge
    name: lyss_network
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

---

## 🔧 开发环境配置

### **开发环境配置 (docker-compose.dev.yml)**
```yaml
version: '3.8'

# 继承主配置
x-common-variables: &common-variables
  POSTGRES_PASSWORD: dev_password
  REDIS_PASSWORD: dev_redis_password
  JWT_SECRET: dev_jwt_secret_key_32_chars_minimum
  ENCRYPTION_KEY: dev_encryption_key_32_chars_minimum

services:
  postgres:
    extends:
      file: docker-compose.yml
      service: postgres
    environment:
      <<: *common-variables
      POSTGRES_DB: lyss_dev
      POSTGRES_USER: lyss_dev
    ports:
      - "5433:5432"  # 避免与本地postgres冲突
    command: |
      postgres 
      -c log_statement=all 
      -c log_destination=stderr 
      -c logging_collector=on
      -c max_connections=200
      -c shared_buffers=256MB

  redis:
    extends:
      file: docker-compose.yml
      service: redis
    environment:
      <<: *common-variables
    ports:
      - "6380:6379"  # 避免与本地redis冲突

  # 开发环境只启动基础设施，服务在本地运行
  # 可以根据需要添加服务的开发版本
```

---

## 📊 监控和日志配置

### **日志收集配置**
```yaml
# 在主配置中添加日志配置
x-logging: &default-logging
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
    labels: "service"

services:
  lyss-api-gateway:
    # ... 其他配置
    logging: *default-logging
    labels:
      - "service=api-gateway"
      - "environment=${ENVIRONMENT:-production}"
```

### **健康检查端点标准**
所有服务必须实现以下健康检查端点：

```
GET /health
{
  "status": "healthy",
  "timestamp": "2025-01-20T10:30:00Z",
  "version": "1.0.0",
  "dependencies": {
    "database": "healthy",
    "redis": "healthy",
    "external_services": "healthy"
  }
}
```

---

## 🚀 部署脚本

### **启动脚本 (scripts/start-prod.sh)**
```bash
#!/bin/bash
set -e

echo "🚀 启动 Lyss AI Platform 生产环境..."

# 检查环境变量
if [ ! -f .env ]; then
    echo "❌ 错误: .env 文件不存在"
    echo "请复制 .env.production.example 到 .env 并配置相应的值"
    exit 1
fi

# 加载环境变量
source .env

# 检查必需的环境变量
required_vars=("POSTGRES_PASSWORD" "REDIS_PASSWORD" "JWT_SECRET" "ENCRYPTION_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ 错误: 环境变量 $var 未设置"
        exit 1
    fi
done

# 创建网络（如果不存在）
docker network create lyss_network 2>/dev/null || true

# 启动基础设施服务
echo "📊 启动基础设施服务..."
docker-compose up -d postgres redis qdrant

# 等待基础设施服务就绪
echo "⏳ 等待基础设施服务启动..."
sleep 30

# 检查基础设施服务健康状态
echo "🔍 检查基础设施服务状态..."
docker-compose ps postgres redis qdrant

# 启动应用服务
echo "🏗️ 启动应用服务..."
docker-compose up -d lyss-auth-service lyss-user-service lyss-provider-service
sleep 20

docker-compose up -d lyss-chat-service lyss-memory-service
sleep 20

docker-compose up -d lyss-api-gateway lyss-frontend

# 等待所有服务就绪
echo "⏳ 等待所有服务启动..."
sleep 60

# 健康检查
echo "🔍 执行健康检查..."
bash scripts/health-check.sh

echo "✅ Lyss AI Platform 启动完成!"
echo "🌐 前端地址: http://localhost:3000"
echo "🔌 API地址: http://localhost:8000"
```

### **健康检查脚本 (scripts/health-check.sh)**
```bash
#!/bin/bash

services=(
    "http://localhost:8000/health:API Gateway"
    "http://localhost:8001/health:Auth Service" 
    "http://localhost:8002/health:User Service"
    "http://localhost:8003/health:Provider Service"
    "http://localhost:8004/health:Chat Service"
    "http://localhost:8005/health:Memory Service"
    "http://localhost:3000:Frontend"
)

echo "🔍 检查所有服务健康状态..."
echo "=================================="

all_healthy=true

for service in "${services[@]}"; do
    url=$(echo $service | cut -d: -f1-2)
    name=$(echo $service | cut -d: -f3)
    
    printf "%-20s: " "$name"
    
    if curl -f -s "$url" > /dev/null 2>&1; then
        echo "✅ 健康"
    else
        echo "❌ 异常"
        all_healthy=false
    fi
done

echo "=================================="

if [ "$all_healthy" = true ]; then
    echo "✅ 所有服务运行正常!"
    exit 0
else
    echo "❌ 部分服务异常，请检查日志"
    exit 1
fi
```

---

## 🔐 环境变量配置

### **.env.production.example**
```bash
# === 数据库配置 ===
POSTGRES_PASSWORD=your_secure_postgres_password_here
POSTGRES_USER=lyss_admin
POSTGRES_DB=lyss_main

# === 缓存配置 ===
REDIS_PASSWORD=your_secure_redis_password_here

# === 安全配置 ===
JWT_SECRET=your_jwt_secret_key_minimum_32_characters_long
ENCRYPTION_KEY=your_encryption_key_minimum_32_characters_long

# === 应用配置 ===
ENVIRONMENT=production
APP_VERSION=1.0.0
DEBUG=false

# === 外部服务 ===
# 邮件服务配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# 监控配置
ENABLE_METRICS=true
METRICS_PORT=9090
```

---

## 📈 扩展和监控

### **水平扩展配置**
```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  lyss-chat-service:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

  lyss-memory-service:
    deploy:
      replicas: 2
      # ... 类似配置
```

### **监控集成（可选）**
```yaml
# 添加到主配置
  prometheus:
    image: prom/prometheus:latest
    container_name: lyss-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - lyss-network

  grafana:
    image: grafana/grafana:latest
    container_name: lyss-grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - lyss-network
```