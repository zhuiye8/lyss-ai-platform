# 部署与配置文档

## 1. 部署架构概述

### 1.1 部署策略
- **本地开发环境**: Docker Compose部署，快速启动
- **测试环境**: Kubernetes部署，模拟生产环境
- **生产环境**: Kubernetes + Helm部署，高可用架构
- **CI/CD流水线**: GitLab CI/GitHub Actions自动化部署

### 1.2 服务拓扑
```
┌─────────────────────────────────────────────────┐
│                  Load Balancer                  │
│              (Nginx/ALB/CloudFlare)             │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│                API Gateway                      │
│              (FastAPI + Uvicorn)                │
└─────────┬───────────────────────────┬───────────┘
          │                           │
┌─────────▼─────────┐       ┌─────────▼─────────┐
│   Frontend App    │       │   Backend Services │
│   (React/Nginx)   │       │                   │
│                   │       │ ┌───────────────┐ │
│                   │       │ │ Auth Service  │ │
│                   │       │ └───────────────┘ │
│                   │       │ ┌───────────────┐ │
│                   │       │ │ Chat Service  │ │
│                   │       │ └───────────────┘ │
│                   │       │ ┌───────────────┐ │
│                   │       │ │ EINO Service  │ │
│                   │       │ └───────────────┘ │
│                   │       │ ┌───────────────┐ │
│                   │       │ │Memory Service │ │
│                   │       │ └───────────────┘ │
└───────────────────┘       └─────────┬─────────┘
                                      │
                    ┌─────────────────▼─────────────────┐
                    │           Data Layer              │
                    │                                   │
                    │ ┌─────────────┐ ┌─────────────┐   │
                    │ │ PostgreSQL  │ │    Redis    │   │
                    │ │  (Master)   │ │  (Cluster)  │   │
                    │ └─────────────┘ └─────────────┘   │
                    │ ┌─────────────┐ ┌─────────────┐   │
                    │ │ PostgreSQL  │ │    Redis    │   │
                    │ │  (Replica)  │ │ (Sentinel)  │   │
                    │ └─────────────┘ └─────────────┘   │
                    └───────────────────────────────────┘
```

### 1.3 环境配置
```yaml
# 环境矩阵
environments:
  development:
    domain: localhost:3000
    replicas: 1
    resources:
      cpu: "0.5"
      memory: "1Gi"
    database:
      instance: single
      storage: 10Gi
    cache:
      instance: single
      memory: 512Mi
    
  staging:
    domain: staging.lyss.ai
    replicas: 2
    resources:
      cpu: "1"
      memory: "2Gi"
    database:
      instance: master-replica
      storage: 50Gi
    cache:
      instance: cluster
      memory: 2Gi
    
  production:
    domain: lyss.ai
    replicas: 3
    resources:
      cpu: "2"
      memory: "4Gi"
    database:
      instance: ha-cluster
      storage: 200Gi
    cache:
      instance: ha-cluster
      memory: 8Gi
```

## 2. Docker配置

### 2.1 基础镜像构建
```dockerfile
# docker/base/Dockerfile.python
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 升级pip并安装基础包
RUN pip install --upgrade pip setuptools wheel

# 创建工作目录
WORKDIR /app

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 默认命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.2 前端应用Dockerfile
```dockerfile
# frontend/Dockerfile
# 构建阶段
FROM node:18-alpine AS builder

WORKDIR /app

# 复制package文件
COPY package*.json ./
RUN npm ci --only=production

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# 生产阶段
FROM nginx:alpine

# 复制nginx配置
COPY nginx.conf /etc/nginx/nginx.conf

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

### 2.3 后端服务Dockerfile
```dockerfile
# backend/Dockerfile
FROM lyss/python-base:latest

# 复制应用代码
COPY . .

# 安装应用依赖
RUN pip install --no-cache-dir -r requirements.txt

# 运行安全扫描
RUN bandit -r . -f json -o security-report.json || true

# 暴露端口
EXPOSE 8000

# 启动脚本
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

### 2.4 EINO服务Dockerfile
```dockerfile
# eino-service/Dockerfile
# 构建阶段
FROM golang:1.21-alpine AS builder

WORKDIR /app

# 安装依赖
RUN apk add --no-cache git

# 复制go mod文件
COPY go.mod go.sum ./
RUN go mod download

# 复制源代码
COPY . .

# 构建应用
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o eino-service cmd/server/main.go

# 生产阶段
FROM alpine:latest

# 安装CA证书
RUN apk --no-cache add ca-certificates

WORKDIR /root/

# 复制二进制文件
COPY --from=builder /app/eino-service .

# 复制配置文件
COPY --from=builder /app/config ./config

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# 运行应用
CMD ["./eino-service"]
```

## 3. Docker Compose配置

### 3.1 开发环境配置
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  # 数据库服务
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: lyss_platform
      POSTGRES_USER: lyss_user
      POSTGRES_PASSWORD: lyss_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lyss_user -d lyss_platform"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis缓存
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --requirepass redis_password
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "redis_password", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # API网关
  api-gateway:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://lyss_user:lyss_password@postgres:5432/lyss_platform
      - REDIS_URL=redis://:redis_password@redis:6379/0
      - JWT_SECRET_KEY=dev_secret_key_change_in_production
      - EINO_SERVICE_URL=http://eino-service:8080
      - MEMORY_SERVICE_URL=http://memory-service:8001
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend:/app
      - ./logs:/app/logs
    command: ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

  # EINO工作流服务
  eino-service:
    build:
      context: ./eino-service
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - SERVER_PORT=8080
      - REDIS_URL=redis://:redis_password@redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LOG_LEVEL=debug
    depends_on:
      - redis
    volumes:
      - ./eino-service:/app
      - ./logs:/app/logs

  # 记忆服务
  memory-service:
    build:
      context: ./memory-service
      dockerfile: Dockerfile
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://lyss_user:lyss_password@postgres:5432/lyss_platform
      - REDIS_URL=redis://:redis_password@redis:6379/1
      - MEM0_API_KEY=${MEM0_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./memory-service:/app

  # 前端应用
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
      - VITE_WS_URL=ws://localhost:8000/ws
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: ["npm", "run", "dev"]

  # 监控服务
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  default:
    name: lyss_network
```

### 3.2 生产环境配置
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  # Nginx反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - api-gateway
      - frontend
    restart: unless-stopped

  # 生产数据库 (主从配置)
  postgres-master:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_REPLICATION_USER: ${POSTGRES_REPLICATION_USER}
      POSTGRES_REPLICATION_PASSWORD: ${POSTGRES_REPLICATION_PASSWORD}
    volumes:
      - postgres_master_data:/var/lib/postgresql/data
      - ./sql/production-init.sql:/docker-entrypoint-initdb.d/init.sql
      - ./postgresql/master/postgresql.conf:/etc/postgresql/postgresql.conf
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    restart: unless-stopped

  postgres-replica:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_MASTER_SERVICE: postgres-master
    volumes:
      - postgres_replica_data:/var/lib/postgresql/data
      - ./postgresql/replica/recovery.conf:/var/lib/postgresql/data/recovery.conf
    depends_on:
      - postgres-master
    restart: unless-stopped

  # Redis集群
  redis-master:
    image: redis:7-alpine
    command: redis-server /etc/redis/redis.conf
    volumes:
      - ./redis/master.conf:/etc/redis/redis.conf
      - redis_master_data:/data
    restart: unless-stopped

  redis-replica:
    image: redis:7-alpine
    command: redis-server /etc/redis/redis.conf
    volumes:
      - ./redis/replica.conf:/etc/redis/redis.conf
      - redis_replica_data:/data
    depends_on:
      - redis-master
    restart: unless-stopped

  redis-sentinel:
    image: redis:7-alpine
    command: redis-sentinel /etc/redis/sentinel.conf
    volumes:
      - ./redis/sentinel.conf:/etc/redis/sentinel.conf
    depends_on:
      - redis-master
      - redis-replica
    restart: unless-stopped

  # 应用服务 (多实例)
  api-gateway:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres-master:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis-master:6379/0
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      - postgres-master
      - redis-master
    deploy:
      replicas: 3
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  postgres_master_data:
  postgres_replica_data:
  redis_master_data:
  redis_replica_data:

networks:
  default:
    name: lyss_prod_network
    driver: bridge
```

## 4. Kubernetes配置

### 4.1 命名空间和资源配额
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: lyss-platform
  labels:
    name: lyss-platform
    environment: production

---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: lyss-quota
  namespace: lyss-platform
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    persistentvolumeclaims: "10"
    services: "20"
    secrets: "20"
    configmaps: "20"

---
apiVersion: v1
kind: LimitRange
metadata:
  name: lyss-limits
  namespace: lyss-platform
spec:
  limits:
  - default:
      cpu: "1"
      memory: "2Gi"
    defaultRequest:
      cpu: "100m"
      memory: "128Mi"
    type: Container
```

### 4.2 ConfigMap配置
```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: lyss-config
  namespace: lyss-platform
data:
  # 数据库配置
  POSTGRES_HOST: "postgres-service"
  POSTGRES_PORT: "5432"
  POSTGRES_DB: "lyss_platform"
  
  # Redis配置
  REDIS_HOST: "redis-service"
  REDIS_PORT: "6379"
  
  # 应用配置
  LOG_LEVEL: "info"
  API_PREFIX: "/api/v1"
  CORS_ORIGINS: "https://lyss.ai,https://app.lyss.ai"
  
  # EINO服务配置
  EINO_SERVICE_URL: "http://eino-service:8080"
  MEMORY_SERVICE_URL: "http://memory-service:8001"

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-config
  namespace: lyss-platform
data:
  nginx.conf: |
    upstream api_backend {
        server api-gateway-service:8000;
    }
    
    upstream frontend_backend {
        server frontend-service:80;
    }
    
    server {
        listen 80;
        server_name lyss.ai www.lyss.ai;
        
        # API代理
        location /api/ {
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # WebSocket代理
        location /ws/ {
            proxy_pass http://api_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }
        
        # 前端应用
        location / {
            proxy_pass http://frontend_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
```

### 4.3 Secret配置
```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: lyss-secrets
  namespace: lyss-platform
type: Opaque
data:
  # 数据库密码 (base64编码)
  POSTGRES_PASSWORD: <base64-encoded-password>
  POSTGRES_REPLICATION_PASSWORD: <base64-encoded-password>
  
  # Redis密码
  REDIS_PASSWORD: <base64-encoded-password>
  
  # JWT密钥
  JWT_SECRET_KEY: <base64-encoded-key>
  
  # 加密密钥
  ENCRYPTION_KEY: <base64-encoded-key>
  
  # AI服务API密钥
  OPENAI_API_KEY: <base64-encoded-key>
  ANTHROPIC_API_KEY: <base64-encoded-key>
  
  # 第三方服务密钥
  MEM0_API_KEY: <base64-encoded-key>
  WEB_SEARCH_API_KEY: <base64-encoded-key>

---
apiVersion: v1
kind: Secret
metadata:
  name: tls-secret
  namespace: lyss-platform
type: kubernetes.io/tls
data:
  tls.crt: <base64-encoded-certificate>
  tls.key: <base64-encoded-private-key>
```

### 4.4 数据库部署
```yaml
# k8s/postgres.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: lyss-platform
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
  storageClassName: fast-ssd

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: lyss-platform
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          valueFrom:
            configMapKeyRef:
              name: lyss-config
              key: POSTGRES_DB
        - name: POSTGRES_USER
          value: "lyss_user"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: lyss-secrets
              key: POSTGRES_PASSWORD
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2
            memory: 4Gi
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - lyss_user
            - -d
            - lyss_platform
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - lyss_user
            - -d
            - lyss_platform
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: lyss-platform
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  type: ClusterIP
```

### 4.5 应用服务部署
```yaml
# k8s/api-gateway.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: lyss-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: lyss/api-gateway:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          value: "postgresql://lyss_user:$(POSTGRES_PASSWORD)@postgres-service:5432/lyss_platform"
        - name: REDIS_URL
          value: "redis://:$(REDIS_PASSWORD)@redis-service:6379/0"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: lyss-secrets
              key: POSTGRES_PASSWORD
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: lyss-secrets
              key: REDIS_PASSWORD
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: lyss-secrets
              key: JWT_SECRET_KEY
        envFrom:
        - configMapRef:
            name: lyss-config
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 1
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true

---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway-service
  namespace: lyss-platform
spec:
  selector:
    app: api-gateway
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
  namespace: lyss-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## 5. Helm Charts

### 5.1 Chart结构
```
helm/lyss-platform/
├── Chart.yaml
├── values.yaml
├── values-production.yaml
├── values-staging.yaml
├── templates/
│   ├── _helpers.tpl
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── postgres/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── pvc.yaml
│   ├── redis/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── api-gateway/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── hpa.yaml
│   ├── frontend/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── eino-service/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── memory-service/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── nginx/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── ingress.yaml
│   └── monitoring/
│       ├── prometheus.yaml
│       └── grafana.yaml
└── charts/
```

### 5.2 Chart.yaml
```yaml
# helm/lyss-platform/Chart.yaml
apiVersion: v2
name: lyss-platform
description: Enterprise AI Service Aggregation Platform
type: application
version: 1.0.0
appVersion: "1.0.0"
keywords:
  - ai
  - platform
  - microservices
  - chat
home: https://lyss.ai
sources:
  - https://github.com/lyss-ai/platform
maintainers:
  - name: Lyss Team
    email: team@lyss.ai
dependencies:
  - name: postgresql
    version: 12.1.2
    repository: https://charts.bitnami.com/bitnami
    condition: postgresql.enabled
  - name: redis
    version: 17.4.3
    repository: https://charts.bitnami.com/bitnami
    condition: redis.enabled
  - name: prometheus
    version: 19.6.1
    repository: https://prometheus-community.github.io/helm-charts
    condition: monitoring.prometheus.enabled
  - name: grafana
    version: 6.50.7
    repository: https://grafana.github.io/helm-charts
    condition: monitoring.grafana.enabled
```

### 5.3 values.yaml
```yaml
# helm/lyss-platform/values.yaml
global:
  imageRegistry: ""
  imagePullSecrets: []
  storageClass: ""

# 应用配置
app:
  name: lyss-platform
  environment: production
  domain: lyss.ai
  
# 镜像配置
images:
  apiGateway:
    repository: lyss/api-gateway
    tag: latest
    pullPolicy: IfNotPresent
  frontend:
    repository: lyss/frontend
    tag: latest
    pullPolicy: IfNotPresent
  einoService:
    repository: lyss/eino-service
    tag: latest
    pullPolicy: IfNotPresent
  memoryService:
    repository: lyss/memory-service
    tag: latest
    pullPolicy: IfNotPresent

# 副本配置
replicaCount:
  apiGateway: 3
  frontend: 2
  einoService: 2
  memoryService: 2

# 资源配置
resources:
  apiGateway:
    requests:
      cpu: 200m
      memory: 512Mi
    limits:
      cpu: 1
      memory: 2Gi
  frontend:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi
  einoService:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2
      memory: 4Gi
  memoryService:
    requests:
      cpu: 200m
      memory: 512Mi
    limits:
      cpu: 1
      memory: 2Gi

# 自动伸缩配置
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

# 数据库配置
postgresql:
  enabled: true
  auth:
    username: lyss_user
    database: lyss_platform
  primary:
    persistence:
      enabled: true
      size: 100Gi
  readReplicas:
    replicaCount: 1

# Redis配置
redis:
  enabled: true
  auth:
    enabled: true
  master:
    persistence:
      enabled: true
      size: 8Gi
  replica:
    replicaCount: 2

# 服务配置
service:
  type: ClusterIP
  ports:
    apiGateway: 8000
    frontend: 80
    einoService: 8080
    memoryService: 8001

# Ingress配置
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
  hosts:
    - host: lyss.ai
      paths:
        - path: /
          pathType: Prefix
          service: frontend
        - path: /api
          pathType: Prefix
          service: api-gateway
  tls:
    - secretName: lyss-tls
      hosts:
        - lyss.ai

# 监控配置
monitoring:
  enabled: true
  prometheus:
    enabled: true
    retention: 15d
    storageSize: 50Gi
  grafana:
    enabled: true
    adminPassword: changeme

# 安全配置
security:
  podSecurityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
  securityContext:
    allowPrivilegeEscalation: false
    capabilities:
      drop:
        - ALL
    readOnlyRootFilesystem: true
    runAsNonRoot: true
    runAsUser: 1000

# 网络策略
networkPolicy:
  enabled: true
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
  egress:
    - to: []
```

## 6. CI/CD配置

### 6.1 GitLab CI配置
```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - security
  - deploy

variables:
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: "/certs"
  REGISTRY: registry.gitlab.com/lyss-ai/platform

# 测试阶段
test:backend:
  stage: test
  image: python:3.11
  services:
    - postgres:15-alpine
    - redis:7-alpine
  variables:
    POSTGRES_DB: test_db
    POSTGRES_USER: test_user
    POSTGRES_PASSWORD: test_password
    REDIS_URL: redis://redis:6379/0
  before_script:
    - cd backend
    - pip install -r requirements.txt
    - pip install -r requirements-test.txt
  script:
    - pytest tests/ --cov=. --cov-report=xml --cov-report=term
    - python -m bandit -r . -f json -o bandit-report.json
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: backend/coverage.xml
      sast: backend/bandit-report.json
    expire_in: 1 week
  only:
    - merge_requests
    - main

test:frontend:
  stage: test
  image: node:18-alpine
  before_script:
    - cd frontend
    - npm ci
  script:
    - npm run test:unit
    - npm run test:e2e
    - npm run lint
    - npm audit --audit-level=moderate
  artifacts:
    reports:
      junit: frontend/test-results.xml
    expire_in: 1 week
  only:
    - merge_requests
    - main

# 构建阶段
build:
  stage: build
  image: docker:20.10.16
  services:
    - docker:20.10.16-dind
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    # 构建后端镜像
    - docker build -t $REGISTRY/api-gateway:$CI_COMMIT_SHA backend/
    - docker push $REGISTRY/api-gateway:$CI_COMMIT_SHA
    
    # 构建前端镜像
    - docker build -t $REGISTRY/frontend:$CI_COMMIT_SHA frontend/
    - docker push $REGISTRY/frontend:$CI_COMMIT_SHA
    
    # 构建EINO服务镜像
    - docker build -t $REGISTRY/eino-service:$CI_COMMIT_SHA eino-service/
    - docker push $REGISTRY/eino-service:$CI_COMMIT_SHA
    
    # 标记latest
    - |
      if [ "$CI_COMMIT_BRANCH" == "main" ]; then
        docker tag $REGISTRY/api-gateway:$CI_COMMIT_SHA $REGISTRY/api-gateway:latest
        docker push $REGISTRY/api-gateway:latest
        
        docker tag $REGISTRY/frontend:$CI_COMMIT_SHA $REGISTRY/frontend:latest
        docker push $REGISTRY/frontend:latest
        
        docker tag $REGISTRY/eino-service:$CI_COMMIT_SHA $REGISTRY/eino-service:latest
        docker push $REGISTRY/eino-service:latest
      fi
  only:
    - main
    - develop

# 安全扫描
security:container-scan:
  stage: security
  image: 
    name: aquasec/trivy:latest
    entrypoint: [""]
  script:
    - trivy image --format template --template "@contrib/gitlab.tpl" 
      --output container-security-report.json $REGISTRY/api-gateway:$CI_COMMIT_SHA
  artifacts:
    reports:
      container_scanning: container-security-report.json
  only:
    - main

# 部署阶段
deploy:staging:
  stage: deploy
  image: alpine/helm:latest
  before_script:
    - kubectl config use-context staging
  script:
    - helm upgrade --install lyss-staging ./helm/lyss-platform 
      --namespace lyss-staging 
      --create-namespace
      --values ./helm/lyss-platform/values-staging.yaml
      --set images.apiGateway.tag=$CI_COMMIT_SHA
      --set images.frontend.tag=$CI_COMMIT_SHA
      --set images.einoService.tag=$CI_COMMIT_SHA
      --wait --timeout=10m
  environment:
    name: staging
    url: https://staging.lyss.ai
  only:
    - develop

deploy:production:
  stage: deploy
  image: alpine/helm:latest
  before_script:
    - kubectl config use-context production
  script:
    - helm upgrade --install lyss-production ./helm/lyss-platform 
      --namespace lyss-production 
      --create-namespace
      --values ./helm/lyss-platform/values-production.yaml
      --set images.apiGateway.tag=$CI_COMMIT_SHA
      --set images.frontend.tag=$CI_COMMIT_SHA
      --set images.einoService.tag=$CI_COMMIT_SHA
      --wait --timeout=15m
  environment:
    name: production
    url: https://lyss.ai
  when: manual
  only:
    - main
```

### 6.2 部署脚本
```bash
#!/bin/bash
# scripts/deploy.sh

set -e

# 配置变量
NAMESPACE=${NAMESPACE:-lyss-platform}
ENVIRONMENT=${ENVIRONMENT:-production}
CHART_PATH="./helm/lyss-platform"
VALUES_FILE="./helm/lyss-platform/values-${ENVIRONMENT}.yaml"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# 检查依赖
check_dependencies() {
    log "检查部署依赖..."
    
    if ! command -v kubectl &> /dev/null; then
        error "kubectl 未安装"
    fi
    
    if ! command -v helm &> /dev/null; then
        error "helm 未安装"
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        error "无法连接到Kubernetes集群"
    fi
    
    log "依赖检查通过"
}

# 备份当前部署
backup_deployment() {
    log "备份当前部署配置..."
    
    if helm list -n $NAMESPACE | grep -q lyss-platform; then
        helm get values lyss-platform -n $NAMESPACE > backup-values-$(date +%Y%m%d-%H%M%S).yaml
        log "备份完成"
    else
        warn "没有找到现有部署，跳过备份"
    fi
}

# 部署应用
deploy_application() {
    log "开始部署应用到 $ENVIRONMENT 环境..."
    
    # 创建命名空间
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # 添加Helm仓库
    helm repo add bitnami https://charts.bitnami.com/bitnami
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update
    
    # 部署应用
    helm upgrade --install lyss-platform $CHART_PATH \
        --namespace $NAMESPACE \
        --values $VALUES_FILE \
        --wait \
        --timeout=15m \
        --atomic
    
    log "部署完成"
}

# 验证部署
verify_deployment() {
    log "验证部署状态..."
    
    # 检查Pod状态
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=lyss-platform -n $NAMESPACE --timeout=300s
    
    # 检查服务状态
    kubectl get services -n $NAMESPACE
    
    # 运行健康检查
    log "运行健康检查..."
    if kubectl run health-check --image=curlimages/curl --rm -it --restart=Never -n $NAMESPACE -- \
        curl -f http://api-gateway-service:8000/health; then
        log "健康检查通过"
    else
        error "健康检查失败"
    fi
}

# 主函数
main() {
    log "开始部署 Lyss Platform 到 $ENVIRONMENT 环境"
    
    check_dependencies
    backup_deployment
    deploy_application
    verify_deployment
    
    log "部署成功完成！"
    log "访问地址: https://$(kubectl get ingress -n $NAMESPACE -o jsonpath='{.items[0].spec.rules[0].host}')"
}

# 运行部署
main "$@"
```

这个部署与配置文档提供了完整的部署方案，包括Docker、Kubernetes、Helm等多种部署方式的详细配置。