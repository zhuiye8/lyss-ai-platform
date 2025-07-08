#!/bin/bash

# Lyss AI Platform 部署脚本
# 支持不同环境的部署

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 默认配置
ENVIRONMENT="dev"
NAMESPACE="lyss-ai-platform"
REGISTRY="your-registry.com"
TAG="latest"
DEPLOY_MONITORING=false
DRY_RUN=false
SKIP_BUILD=false

# 帮助信息
show_help() {
    cat << EOF
Lyss AI Platform 部署脚本

用法: $0 [选项]

选项:
    -e, --env ENVIRONMENT       部署环境 (dev|staging|prod) [默认: dev]
    -n, --namespace NAMESPACE   Kubernetes 命名空间 [默认: lyss-ai-platform]
    -r, --registry REGISTRY     Docker 镜像仓库地址
    -t, --tag TAG              镜像标签 [默认: latest]
    -m, --monitoring           部署监控组件
    --dry-run                  仅显示将要执行的命令，不实际执行
    --skip-build               跳过镜像构建步骤
    -h, --help                 显示此帮助信息

示例:
    $0 -e dev                  # 部署到开发环境
    $0 -e prod -m              # 部署到生产环境并包含监控
    $0 -e staging --dry-run    # 预演部署到测试环境

EOF
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -t|--tag)
                TAG="$2"
                shift 2
                ;;
            -m|--monitoring)
                DEPLOY_MONITORING=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 验证环境
validate_environment() {
    log_info "验证部署环境..."
    
    # 检查 kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl 未安装或不在 PATH 中"
        exit 1
    fi
    
    # 检查 Docker
    if ! command -v docker &> /dev/null && [ "$SKIP_BUILD" = false ]; then
        log_error "Docker 未安装或不在 PATH 中"
        exit 1
    fi
    
    # 检查 Kubernetes 连接
    if ! kubectl cluster-info &> /dev/null; then
        log_error "无法连接到 Kubernetes 集群"
        exit 1
    fi
    
    # 验证环境参数
    if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
        log_error "无效的环境: $ENVIRONMENT（必须是 dev、staging 或 prod）"
        exit 1
    fi
    
    log_success "环境验证通过"
}

# 执行命令（支持 dry-run）
execute_command() {
    local cmd="$1"
    local description="$2"
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] $description"
        echo "    命令: $cmd"
    else
        log_info "$description"
        if eval "$cmd"; then
            log_success "$description 完成"
        else
            log_error "$description 失败"
            exit 1
        fi
    fi
}

# 构建镜像
build_images() {
    if [ "$SKIP_BUILD" = true ]; then
        log_info "跳过镜像构建"
        return
    fi
    
    log_info "开始构建 Docker 镜像..."
    
    # 构建后端镜像
    execute_command \
        "docker build -t ${REGISTRY}/lyss-api-gateway:${TAG} -f backend/Dockerfile backend/" \
        "构建 API Gateway 镜像"
    
    # 构建 EINO 服务镜像
    execute_command \
        "docker build -t ${REGISTRY}/lyss-eino-service:${TAG} -f eino-service/Dockerfile eino-service/" \
        "构建 EINO 服务镜像"
    
    # 构建记忆服务镜像
    execute_command \
        "docker build -t ${REGISTRY}/lyss-memory-service:${TAG} -f memory-service/Dockerfile memory-service/" \
        "构建记忆服务镜像"
    
    # 构建前端镜像
    execute_command \
        "docker build -t ${REGISTRY}/lyss-frontend:${TAG} -f frontend/Dockerfile frontend/" \
        "构建前端镜像"
    
    log_success "所有镜像构建完成"
}

# 推送镜像
push_images() {
    if [ "$SKIP_BUILD" = true ]; then
        log_info "跳过镜像推送"
        return
    fi
    
    log_info "推送镜像到镜像仓库..."
    
    local images=(
        "${REGISTRY}/lyss-api-gateway:${TAG}"
        "${REGISTRY}/lyss-eino-service:${TAG}"
        "${REGISTRY}/lyss-memory-service:${TAG}"
        "${REGISTRY}/lyss-frontend:${TAG}"
    )
    
    for image in "${images[@]}"; do
        execute_command \
            "docker push $image" \
            "推送镜像 $image"
    done
    
    log_success "所有镜像推送完成"
}

# 创建命名空间
create_namespace() {
    log_info "创建命名空间..."
    
    execute_command \
        "kubectl apply -f k8s/base/namespace.yaml" \
        "创建命名空间"
}

# 部署 Secrets
deploy_secrets() {
    log_info "部署 Secrets..."
    
    # 检查 secrets 文件是否存在
    local secrets_file="k8s/${ENVIRONMENT}/secrets.yaml"
    if [ -f "$secrets_file" ]; then
        execute_command \
            "kubectl apply -f $secrets_file" \
            "部署 Secrets"
    else
        log_warning "Secrets 文件不存在: $secrets_file"
        log_warning "请确保已创建必要的 Secrets"
    fi
}

# 部署 ConfigMaps
deploy_configmaps() {
    log_info "部署 ConfigMaps..."
    
    execute_command \
        "kubectl apply -f k8s/base/configmap.yaml" \
        "部署基础 ConfigMaps"
    
    # 部署环境特定的 ConfigMaps
    local env_configmap="k8s/${ENVIRONMENT}/configmap.yaml"
    if [ -f "$env_configmap" ]; then
        execute_command \
            "kubectl apply -f $env_configmap" \
            "部署环境特定 ConfigMaps"
    fi
}

# 部署数据库
deploy_database() {
    log_info "部署数据库..."
    
    execute_command \
        "kubectl apply -f k8s/base/postgres-deployment.yaml" \
        "部署 PostgreSQL"
    
    # 等待数据库就绪
    execute_command \
        "kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgres -n $NAMESPACE --timeout=300s" \
        "等待数据库就绪"
}

# 部署 Redis
deploy_redis() {
    log_info "部署 Redis..."
    
    local redis_file="k8s/base/redis-deployment.yaml"
    if [ -f "$redis_file" ]; then
        execute_command \
            "kubectl apply -f $redis_file" \
            "部署 Redis"
        
        # 等待 Redis 就绪
        execute_command \
            "kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=redis -n $NAMESPACE --timeout=300s" \
            "等待 Redis 就绪"
    fi
}

# 部署应用服务
deploy_services() {
    log_info "部署应用服务..."
    
    # 更新镜像标签
    if [ "$DRY_RUN" = false ]; then
        # 使用 sed 更新镜像标签（这里需要根据实际 YAML 文件调整）
        log_info "更新镜像标签为 $TAG"
    fi
    
    # 部署 API Gateway
    execute_command \
        "kubectl apply -f k8s/base/api-gateway-deployment.yaml" \
        "部署 API Gateway"
    
    # 部署 EINO 服务
    local eino_file="k8s/base/eino-deployment.yaml"
    if [ -f "$eino_file" ]; then
        execute_command \
            "kubectl apply -f $eino_file" \
            "部署 EINO 服务"
    fi
    
    # 部署记忆服务
    local memory_file="k8s/base/memory-deployment.yaml"
    if [ -f "$memory_file" ]; then
        execute_command \
            "kubectl apply -f $memory_file" \
            "部署记忆服务"
    fi
    
    # 部署前端
    local frontend_file="k8s/base/frontend-deployment.yaml"
    if [ -f "$frontend_file" ]; then
        execute_command \
            "kubectl apply -f $frontend_file" \
            "部署前端"
    fi
}

# 部署 Ingress
deploy_ingress() {
    log_info "部署 Ingress..."
    
    execute_command \
        "kubectl apply -f k8s/base/ingress.yaml" \
        "部署 Ingress"
}

# 部署监控组件
deploy_monitoring() {
    if [ "$DEPLOY_MONITORING" = false ]; then
        log_info "跳过监控组件部署"
        return
    fi
    
    log_info "部署监控组件..."
    
    # 部署 Prometheus
    local prometheus_file="k8s/base/prometheus-deployment.yaml"
    if [ -f "$prometheus_file" ]; then
        execute_command \
            "kubectl apply -f $prometheus_file" \
            "部署 Prometheus"
    fi
    
    # 部署 Grafana
    local grafana_file="k8s/base/grafana-deployment.yaml"
    if [ -f "$grafana_file" ]; then
        execute_command \
            "kubectl apply -f $grafana_file" \
            "部署 Grafana"
    fi
    
    # 部署 Jaeger
    local jaeger_file="k8s/base/jaeger-deployment.yaml"
    if [ -f "$jaeger_file" ]; then
        execute_command \
            "kubectl apply -f $jaeger_file" \
            "部署 Jaeger"
    fi
}

# 等待部署完成
wait_for_deployment() {
    log_info "等待部署完成..."
    
    local deployments=(
        "api-gateway-deployment"
    )
    
    # 根据实际部署的组件添加到列表
    if [ -f "k8s/base/eino-deployment.yaml" ]; then
        deployments+=("eino-deployment")
    fi
    
    if [ -f "k8s/base/memory-deployment.yaml" ]; then
        deployments+=("memory-deployment")
    fi
    
    if [ -f "k8s/base/frontend-deployment.yaml" ]; then
        deployments+=("frontend-deployment")
    fi
    
    for deployment in "${deployments[@]}"; do
        execute_command \
            "kubectl rollout status deployment/$deployment -n $NAMESPACE --timeout=600s" \
            "等待 $deployment 部署完成"
    done
}

# 验证部署
verify_deployment() {
    log_info "验证部署状态..."
    
    execute_command \
        "kubectl get pods -n $NAMESPACE" \
        "查看 Pod 状态"
    
    execute_command \
        "kubectl get services -n $NAMESPACE" \
        "查看 Service 状态"
    
    execute_command \
        "kubectl get ingress -n $NAMESPACE" \
        "查看 Ingress 状态"
    
    # 检查应用健康状态
    log_info "检查应用健康状态..."
    sleep 10  # 等待应用启动
    
    if [ "$DRY_RUN" = false ]; then
        # 这里可以添加具体的健康检查逻辑
        log_info "应用健康检查（实现中...）"
    fi
}

# 显示部署信息
show_deployment_info() {
    log_success "部署完成！"
    echo ""
    echo "部署信息:"
    echo "  环境: $ENVIRONMENT"
    echo "  命名空间: $NAMESPACE"
    echo "  镜像标签: $TAG"
    echo ""
    
    if [ "$DRY_RUN" = false ]; then
        echo "访问地址:"
        echo "  应用: https://app.lyss.ai (生产环境)"
        echo "  API: https://api.lyss.ai (生产环境)"
        echo ""
        echo "管理命令:"
        echo "  查看 Pods: kubectl get pods -n $NAMESPACE"
        echo "  查看日志: kubectl logs -f deployment/api-gateway-deployment -n $NAMESPACE"
        echo "  扩缩容: kubectl scale deployment api-gateway-deployment --replicas=5 -n $NAMESPACE"
    fi
}

# 主函数
main() {
    echo "🚀 Lyss AI Platform 部署脚本"
    echo "================================"
    
    parse_args "$@"
    validate_environment
    
    log_info "开始部署 - 环境: $ENVIRONMENT, 命名空间: $NAMESPACE"
    
    # 部署步骤
    build_images
    push_images
    create_namespace
    deploy_secrets
    deploy_configmaps
    deploy_database
    deploy_redis
    deploy_services
    deploy_ingress
    deploy_monitoring
    wait_for_deployment
    verify_deployment
    show_deployment_info
    
    log_success "部署流程完成！"
}

# 错误处理
trap 'log_error "部署过程中发生错误，退出码: $?"' ERR

# 执行主函数
main "$@"