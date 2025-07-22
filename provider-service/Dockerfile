# ================================================================
# Lyss Provider Service - 多阶段Docker镜像
# 
# 支持开发、测试、生产多种环境的优化镜像构建
# 使用Alpine Linux作为基础镜像，减小镜像体积
#
# 构建命令:
#   docker build -t lyss/provider-service:latest .
#   docker build --target development -t lyss/provider-service:dev .
#   docker build --target production -t lyss/provider-service:prod .
#
# Author: Lyss AI Team
# Created: 2025-01-22
# Modified: 2025-01-22
# ================================================================

# ================================================================
# 阶段1: 基础环境
# ================================================================
FROM python:3.11-slim as base

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    # 基础工具
    curl \
    wget \
    git \
    # 编译工具（某些Python包需要）
    gcc \
    g++ \
    make \
    # PostgreSQL客户端
    libpq-dev \
    # 清理缓存
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 创建应用用户（安全性）
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# ================================================================
# 阶段2: 依赖安装
# ================================================================
FROM base as dependencies

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ================================================================
# 阶段3: 开发环境
# ================================================================
FROM dependencies as development

# 安装开发工具
RUN pip install \
    pytest \
    pytest-cov \
    pytest-asyncio \
    black \
    isort \
    flake8 \
    mypy

# 复制源代码
COPY . .

# 创建必要的目录
RUN mkdir -p logs config/provider_schemas

# 设置权限
RUN chown -R appuser:appgroup /app

# 切换到应用用户
USER appuser

# 暴露端口
EXPOSE 8003 9090

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# 默认启动命令（开发模式）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003", "--reload"]

# ================================================================
# 阶段4: 测试环境
# ================================================================
FROM development as testing

# 设置测试环境变量
ENV ENVIRONMENT=testing

# 复制测试配置
COPY tests/ ./tests/
COPY pytest.ini .

# 运行测试
RUN python -m pytest tests/ --cov=app --cov-report=xml --cov-report=term

# ================================================================
# 阶段5: 生产环境构建
# ================================================================
FROM base as production-build

# 安装生产依赖
COPY requirements.txt .
RUN pip install --no-dev -r requirements.txt

# 复制应用代码
COPY app/ ./app/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY sql/ ./sql/

# 清理不必要的文件
RUN find . -type f -name "*.pyc" -delete && \
    find . -type d -name "__pycache__" -delete && \
    find . -type d -name "*.egg-info" -exec rm -rf {} +

# ================================================================
# 阶段6: 生产环境最终镜像
# ================================================================
FROM python:3.11-slim as production

# 设置生产环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    curl \
    libpq5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 创建应用用户
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# 设置工作目录
WORKDIR /app

# 从构建阶段复制文件
COPY --from=production-build --chown=appuser:appgroup /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=production-build --chown=appuser:appgroup /usr/local/bin /usr/local/bin
COPY --from=production-build --chown=appuser:appgroup /app /app

# 创建必要的目录
RUN mkdir -p logs config/provider_schemas && \
    chown -R appuser:appgroup /app

# 切换到应用用户
USER appuser

# 暴露端口
EXPOSE 8003

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# 生产环境启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "4"]

# ================================================================
# 镜像元数据
# ================================================================
LABEL maintainer="Lyss AI Team" \
      service="lyss-provider-service" \
      version="1.0.0" \
      description="Lyss AI Platform Provider Service" \
      build-date="2025-01-22" \
      vendor="Lyss AI Platform"

# ================================================================
# 构建参数和环境变量
# ================================================================

# 构建时参数
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

# 运行时环境变量（可被覆盖）
ENV SERVICE_NAME=lyss-provider-service \
    SERVICE_VERSION=${VERSION} \
    HOST=0.0.0.0 \
    PORT=8003

# ================================================================
# 使用示例和说明
# ================================================================

# 构建开发镜像:
# docker build --target development -t lyss/provider-service:dev .

# 构建生产镜像:
# docker build --target production -t lyss/provider-service:prod .

# 运行开发容器:
# docker run -d -p 8003:8003 --name provider-dev lyss/provider-service:dev

# 运行生产容器:
# docker run -d -p 8003:8003 --name provider-prod \
#   -e DATABASE_URL=postgresql://user:pass@host:5432/db \
#   -e REDIS_URL=redis://redis-host:6379/0 \
#   lyss/provider-service:prod

# 查看容器日志:
# docker logs -f provider-dev

# 进入容器调试:
# docker exec -it provider-dev /bin/bash