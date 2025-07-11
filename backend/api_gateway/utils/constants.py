"""
常量定义模块

定义API Gateway使用的常量
"""

# HTTP状态码
HTTP_STATUS_OK = 200
HTTP_STATUS_CREATED = 201
HTTP_STATUS_NO_CONTENT = 204
HTTP_STATUS_BAD_REQUEST = 400
HTTP_STATUS_UNAUTHORIZED = 401
HTTP_STATUS_FORBIDDEN = 403
HTTP_STATUS_NOT_FOUND = 404
HTTP_STATUS_METHOD_NOT_ALLOWED = 405
HTTP_STATUS_TOO_MANY_REQUESTS = 429
HTTP_STATUS_INTERNAL_SERVER_ERROR = 500
HTTP_STATUS_SERVICE_UNAVAILABLE = 503
HTTP_STATUS_GATEWAY_TIMEOUT = 504

# 错误代码
ERROR_CODES = {
    "INVALID_INPUT": "1001",
    "MISSING_REQUIRED_FIELD": "1002",
    "INVALID_FORMAT": "1003",
    "REQUEST_TOO_LARGE": "1004",
    "RATE_LIMIT_EXCEEDED": "1005",
    "UNAUTHORIZED": "2001",
    "TOKEN_EXPIRED": "2002",
    "TOKEN_INVALID": "2003",
    "INSUFFICIENT_PERMISSIONS": "2004",
    "SERVICE_UNAVAILABLE": "5004",
    "REQUEST_TIMEOUT": "4003",
    "INTERNAL_SERVER_ERROR": "5003"
}

# 用户角色
USER_ROLES = {
    "END_USER": "end_user",
    "TENANT_ADMIN": "tenant_admin",
    "SUPER_ADMIN": "super_admin"
}

# 服务名称
SERVICE_NAMES = {
    "AUTH": "auth_service",
    "TENANT": "tenant_service",
    "EINO": "eino_service",
    "MEMORY": "memory_service",
    "GATEWAY": "api_gateway"
}

# 路由前缀
ROUTE_PREFIXES = {
    "AUTH": "/api/v1/auth",
    "ADMIN": "/api/v1/admin",
    "CHAT": "/api/v1/chat",
    "MEMORY": "/api/v1/memory",
    "HEALTH": "/health"
}

# 安全头部
SECURITY_HEADERS = {
    "X_CONTENT_TYPE_OPTIONS": "X-Content-Type-Options",
    "X_FRAME_OPTIONS": "X-Frame-Options",
    "X_XSS_PROTECTION": "X-XSS-Protection",
    "STRICT_TRANSPORT_SECURITY": "Strict-Transport-Security",
    "CONTENT_SECURITY_POLICY": "Content-Security-Policy",
    "REFERRER_POLICY": "Referrer-Policy"
}

# 自定义头部
CUSTOM_HEADERS = {
    "X_REQUEST_ID": "X-Request-ID",
    "X_USER_ID": "X-User-ID",
    "X_TENANT_ID": "X-Tenant-ID",
    "X_USER_ROLE": "X-User-Role",
    "X_USER_EMAIL": "X-User-Email",
    "X_FORWARDED_FOR": "X-Forwarded-For",
    "X_REAL_IP": "X-Real-IP",
    "X_CLIENT_IP": "X-Client-IP"
}

# 请求方法
HTTP_METHODS = {
    "GET": "GET",
    "POST": "POST",
    "PUT": "PUT",
    "PATCH": "PATCH",
    "DELETE": "DELETE",
    "OPTIONS": "OPTIONS",
    "HEAD": "HEAD"
}

# 内容类型
CONTENT_TYPES = {
    "JSON": "application/json",
    "FORM": "application/x-www-form-urlencoded",
    "MULTIPART": "multipart/form-data",
    "TEXT": "text/plain",
    "HTML": "text/html",
    "XML": "application/xml",
    "STREAM": "text/event-stream"
}

# 日志级别
LOG_LEVELS = {
    "DEBUG": "DEBUG",
    "INFO": "INFO",
    "WARNING": "WARNING",
    "ERROR": "ERROR",
    "CRITICAL": "CRITICAL"
}

# 操作类型
OPERATION_TYPES = {
    "API_REQUEST": "api_request",
    "SERVICE_CALL": "service_call",
    "AUTH_EVENT": "auth_event",
    "HEALTH_CHECK": "health_check",
    "PROXY_REQUEST": "proxy_request"
}

# 认证事件类型
AUTH_EVENT_TYPES = {
    "JWT_VALIDATION": "jwt_validation",
    "TOKEN_EXTRACTION": "token_extraction",
    "USER_AUTHENTICATION": "user_authentication",
    "PERMISSION_CHECK": "permission_check",
    "ACCESS_DENIED": "access_denied"
}

# 超时配置
TIMEOUT_CONFIG = {
    "DEFAULT_REQUEST_TIMEOUT": 30,
    "HEALTH_CHECK_TIMEOUT": 5,
    "SERVICE_CALL_TIMEOUT": 30,
    "JWT_VALIDATION_TIMEOUT": 5
}

# 缓存配置
CACHE_CONFIG = {
    "JWT_CACHE_TTL": 300,  # 5分钟
    "HEALTH_CHECK_CACHE_TTL": 30,  # 30秒
    "SERVICE_REGISTRY_CACHE_TTL": 60  # 1分钟
}

# 限流配置
RATE_LIMIT_CONFIG = {
    "DEFAULT_REQUESTS_PER_MINUTE": 100,
    "DEFAULT_BURST_SIZE": 10,
    "AUTH_REQUESTS_PER_MINUTE": 10,
    "HEALTH_CHECK_REQUESTS_PER_MINUTE": 1000
}

# 默认响应消息
DEFAULT_MESSAGES = {
    "SUCCESS": "操作成功",
    "CREATED": "创建成功",
    "UPDATED": "更新成功",
    "DELETED": "删除成功",
    "NOT_FOUND": "资源不存在",
    "INVALID_INPUT": "输入参数无效",
    "UNAUTHORIZED": "认证失败",
    "FORBIDDEN": "权限不足",
    "INTERNAL_ERROR": "内部服务器错误",
    "SERVICE_UNAVAILABLE": "服务不可用",
    "REQUEST_TIMEOUT": "请求超时"
}

# 敏感信息关键词
SENSITIVE_KEYWORDS = {
    "password", "secret", "key", "token", "credential",
    "api_key", "secret_key", "access_token", "refresh_token",
    "authorization", "auth", "private_key", "public_key",
    "certificate", "cert", "signature", "hash"
}

# 健康检查状态
HEALTH_STATUS = {
    "HEALTHY": "healthy",
    "UNHEALTHY": "unhealthy",
    "DEGRADED": "degraded",
    "UNKNOWN": "unknown"
}