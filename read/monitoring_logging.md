# 监控与日志系统设计文档

## 1. 监控架构概述

### 1.1 监控策略
- **四个黄金信号**：延迟、流量、错误率、饱和度
- **多层监控**：基础设施、应用、业务、用户体验
- **实时告警**：基于阈值和机器学习的智能告警
- **可观测性**：Metrics、Logs、Traces三位一体

### 1.2 监控技术栈
```
┌─────────────────────────────────────────────────┐
│                数据展示层                        │
│            Grafana Dashboard                    │
├─────────────────────────────────────────────────┤
│                告警处理层                        │
│        AlertManager + PagerDuty               │
├─────────────────────────────────────────────────┤
│                数据存储层                        │
│    Prometheus + InfluxDB + Elasticsearch      │
├─────────────────────────────────────────────────┤
│                数据采集层                        │
│   Node Exporter + cAdvisor + Jaeger           │
├─────────────────────────────────────────────────┤
│                应用层                           │
│        Lyss Platform Services                 │
└─────────────────────────────────────────────────┘
```

### 1.3 关键指标体系
```python
# 系统关键指标定义
SYSTEM_METRICS = {
    "availability": {
        "target": 99.95,  # 99.95%可用性目标
        "measurement": "uptime_ratio",
        "window": "monthly"
    },
    "performance": {
        "api_latency_p95": 200,  # 95%请求延迟<200ms
        "api_latency_p99": 500,  # 99%请求延迟<500ms
        "throughput": 5000       # 支持5000并发用户
    },
    "reliability": {
        "error_rate": 0.1,       # 错误率<0.1%
        "mttr": 15,              # 平均恢复时间<15分钟
        "mtbf": 720              # 平均故障间隔>720小时
    }
}
```

## 2. 指标收集系统

### 2.1 应用指标
```python
# metrics/application.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time
from functools import wraps

# 定义核心指标
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status', 'tenant_id']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint', 'tenant_id'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)

ACTIVE_CONNECTIONS = Gauge(
    'active_connections',
    'Active database connections',
    ['database', 'tenant_id']
)

AI_MODEL_REQUESTS = Counter(
    'ai_model_requests_total',
    'Total AI model requests',
    ['provider', 'model', 'tenant_id', 'status']
)

AI_MODEL_LATENCY = Histogram(
    'ai_model_latency_seconds',
    'AI model response latency',
    ['provider', 'model', 'tenant_id'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

TOKEN_USAGE = Counter(
    'ai_tokens_consumed_total',
    'Total AI tokens consumed',
    ['provider', 'model', 'tenant_id', 'token_type']
)

# 装饰器用于自动收集指标
def monitor_api(endpoint_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tenant_id = kwargs.get('tenant_id', 'unknown')
            method = kwargs.get('method', 'unknown')
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                REQUEST_COUNT.labels(
                    method=method,
                    endpoint=endpoint_name,
                    status='success',
                    tenant_id=tenant_id
                ).inc()
                return result
            except Exception as e:
                REQUEST_COUNT.labels(
                    method=method,
                    endpoint=endpoint_name,
                    status='error',
                    tenant_id=tenant_id
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                REQUEST_DURATION.labels(
                    method=method,
                    endpoint=endpoint_name,
                    tenant_id=tenant_id
                ).observe(duration)
        
        return wrapper
    return decorator

# 业务指标收集器
class BusinessMetrics:
    def __init__(self):
        self.user_sessions = Gauge(
            'active_user_sessions',
            'Active user sessions',
            ['tenant_id']
        )
        
        self.conversation_count = Counter(
            'conversations_created_total',
            'Total conversations created',
            ['tenant_id']
        )
        
        self.message_count = Counter(
            'messages_sent_total',
            'Total messages sent',
            ['tenant_id', 'message_type']
        )
        
        self.revenue_metrics = Counter(
            'revenue_generated_total',
            'Total revenue generated',
            ['tenant_id', 'plan_type']
        )
    
    def track_user_login(self, tenant_id: str):
        self.user_sessions.labels(tenant_id=tenant_id).inc()
    
    def track_user_logout(self, tenant_id: str):
        self.user_sessions.labels(tenant_id=tenant_id).dec()
    
    def track_conversation_created(self, tenant_id: str):
        self.conversation_count.labels(tenant_id=tenant_id).inc()
    
    def track_message_sent(self, tenant_id: str, message_type: str):
        self.message_count.labels(
            tenant_id=tenant_id,
            message_type=message_type
        ).inc()
    
    def track_ai_request(self, tenant_id: str, provider: str, 
                        model: str, tokens: int, success: bool):
        status = 'success' if success else 'error'
        AI_MODEL_REQUESTS.labels(
            provider=provider,
            model=model,
            tenant_id=tenant_id,
            status=status
        ).inc()
        
        if success:
            TOKEN_USAGE.labels(
                provider=provider,
                model=model,
                tenant_id=tenant_id,
                token_type='total'
            ).inc(tokens)

business_metrics = BusinessMetrics()
```

### 2.2 基础设施指标
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  # 应用指标
  - job_name: 'lyss-api-gateway'
    static_configs:
      - targets: ['api-gateway:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
    
  - job_name: 'lyss-eino-service'
    static_configs:
      - targets: ['eino-service:8080']
    metrics_path: '/metrics'
    scrape_interval: 10s
    
  # 基础设施指标
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
    
  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']
    
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']
    
  # 容器指标
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
    
  # Kubernetes指标
  - job_name: 'kubernetes-apiservers'
    kubernetes_sd_configs:
      - role: endpoints
    relabel_configs:
      - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
        action: keep
        regex: default;kubernetes;https
```

## 3. 日志系统

### 3.1 日志架构
```
应用日志 → Filebeat → Logstash → Elasticsearch → Kibana
         ↓
      Fluentd → InfluxDB → Grafana
```

### 3.2 结构化日志
```python
# logging/structured_logger.py
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import traceback

class StructuredLogger:
    def __init__(self, service_name: str, version: str):
        self.service_name = service_name
        self.version = version
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        logger = logging.getLogger(self.service_name)
        logger.setLevel(logging.INFO)
        
        # JSON格式化器
        formatter = StructuredFormatter(self.service_name, self.version)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 文件处理器
        file_handler = logging.FileHandler(f'/logs/{self.service_name}.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def info(self, message: str, **kwargs):
        self._log('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log('WARNING', message, **kwargs)
    
    def error(self, message: str, error: Exception = None, **kwargs):
        if error:
            kwargs['error'] = {
                'type': type(error).__name__,
                'message': str(error),
                'traceback': traceback.format_exc()
            }
        self._log('ERROR', message, **kwargs)
    
    def audit(self, event_type: str, tenant_id: str, user_id: str, 
              action: str, resource: str, result: str, **kwargs):
        self._log('AUDIT', f"Audit event: {event_type}", 
                  event_type=event_type,
                  tenant_id=tenant_id,
                  user_id=user_id,
                  action=action,
                  resource=resource,
                  result=result,
                  **kwargs)
    
    def security(self, event_type: str, severity: str, description: str, **kwargs):
        self._log('SECURITY', f"Security event: {event_type}",
                  event_type=event_type,
                  severity=severity,
                  description=description,
                  **kwargs)
    
    def _log(self, level: str, message: str, **kwargs):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'service': self.service_name,
            'version': self.version,
            'level': level,
            'message': message,
            **kwargs
        }
        
        # 根据级别选择日志方法
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(json.dumps(log_data, ensure_ascii=False))

class StructuredFormatter(logging.Formatter):
    def __init__(self, service_name: str, version: str):
        self.service_name = service_name
        self.version = version
        super().__init__()
    
    def format(self, record):
        # 如果record.msg已经是JSON，直接返回
        if hasattr(record, 'msg') and record.msg.startswith('{'):
            return record.msg
        
        # 否则构建结构化日志
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'service': self.service_name,
            'version': self.version,
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)

# 全局日志实例
app_logger = StructuredLogger('lyss-platform', '1.0.0')
```

### 3.3 日志中间件
```python
# middleware/logging_middleware.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid

class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger):
        super().__init__(app)
        self.logger = logger
    
    async def dispatch(self, request: Request, call_next):
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 请求开始日志
        start_time = time.time()
        
        self.logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            tenant_id=getattr(request.state, 'tenant_id', None)
        )
        
        try:
            response = await call_next(request)
            
            # 请求完成日志
            duration = time.time() - start_time
            self.logger.info(
                "Request completed",
                request_id=request_id,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
                response_size=response.headers.get("content-length")
            )
            
            # 添加请求ID到响应头
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # 请求失败日志
            duration = time.time() - start_time
            self.logger.error(
                "Request failed",
                error=e,
                request_id=request_id,
                duration_ms=round(duration * 1000, 2)
            )
            raise
```

## 4. 分布式追踪

### 4.1 Jaeger配置
```python
# tracing/jaeger_config.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

def setup_tracing(service_name: str, jaeger_endpoint: str):
    # 设置tracer provider
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    
    # Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger-agent",
        agent_port=6831,
        collector_endpoint=jaeger_endpoint,
    )
    
    # Span processor
    span_processor = BatchSpanProcessor(jaeger_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    
    # 自动instrumentation
    FastAPIInstrumentor.instrument()
    RequestsInstrumentor.instrument()
    SQLAlchemyInstrumentor.instrument()
    
    return tracer

# 自定义追踪装饰器
def trace_function(operation_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(operation_name) as span:
                # 添加span属性
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("function.result", "success")
                    return result
                except Exception as e:
                    span.set_attribute("function.result", "error")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    raise
        return wrapper
    return decorator
```

## 5. 告警系统

### 5.1 告警规则
```yaml
# monitoring/alert_rules.yml
groups:
- name: lyss_platform_alerts
  rules:
  # 服务可用性告警
  - alert: ServiceDown
    expr: up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Service {{ $labels.job }} is down"
      description: "Service {{ $labels.job }} has been down for more than 1 minute"
  
  # API延迟告警
  - alert: HighAPILatency
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High API latency detected"
      description: "95th percentile latency is {{ $value }}s for {{ $labels.endpoint }}"
  
  # 错误率告警
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.01
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value | humanizePercentage }} for {{ $labels.endpoint }}"
  
  # 数据库连接告警
  - alert: DatabaseConnectionHigh
    expr: active_connections > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High database connection count"
      description: "Database {{ $labels.database }} has {{ $value }} active connections"
  
  # 内存使用率告警
  - alert: HighMemoryUsage
    expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High memory usage"
      description: "Memory usage is {{ $value | humanizePercentage }} on {{ $labels.instance }}"
  
  # AI模型调用失败告警
  - alert: AIModelFailures
    expr: rate(ai_model_requests_total{status="error"}[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "AI model failures detected"
      description: "{{ $labels.provider }}/{{ $labels.model }} failure rate is {{ $value }}/s"
  
  # 租户配额告警
  - alert: TenantQuotaExceeded
    expr: rate(http_requests_total{status="429"}[5m]) > 0
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "Tenant quota exceeded"
      description: "Tenant {{ $labels.tenant_id }} is hitting rate limits"
```

### 5.2 告警管理器配置
```yaml
# monitoring/alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@lyss.ai'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'default-receiver'
  routes:
  - match:
      severity: critical
    receiver: 'critical-alerts'
  - match:
      severity: warning
    receiver: 'warning-alerts'

receivers:
- name: 'default-receiver'
  slack_configs:
  - api_url: 'YOUR_SLACK_WEBHOOK_URL'
    channel: '#alerts'
    title: 'Lyss Platform Alert'
    text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

- name: 'critical-alerts'
  slack_configs:
  - api_url: 'YOUR_SLACK_WEBHOOK_URL'
    channel: '#critical-alerts'
    title: '🚨 CRITICAL: Lyss Platform Alert'
    text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}{{ end }}'
  pagerduty_configs:
  - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
    description: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

- name: 'warning-alerts'
  slack_configs:
  - api_url: 'YOUR_SLACK_WEBHOOK_URL'
    channel: '#warnings'
    title: '⚠️ WARNING: Lyss Platform Alert'
    text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

inhibit_rules:
- source_match:
    severity: 'critical'
  target_match:
    severity: 'warning'
  equal: ['alertname', 'cluster', 'service']
```

## 6. 仪表盘配置

### 6.1 Grafana仪表盘
```json
{
  "dashboard": {
    "title": "Lyss Platform Overview",
    "panels": [
      {
        "title": "API Request Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total[5m]))",
            "legendFormat": "Requests/sec"
          }
        ]
      },
      {
        "title": "API Latency Percentiles",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          },
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "99th percentile"
          }
        ]
      },
      {
        "title": "Error Rate by Endpoint",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) by (endpoint) / sum(rate(http_requests_total[5m])) by (endpoint)",
            "legendFormat": "{{ endpoint }}"
          }
        ]
      },
      {
        "title": "Active Users by Tenant",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(active_user_sessions) by (tenant_id)",
            "legendFormat": "{{ tenant_id }}"
          }
        ]
      },
      {
        "title": "AI Model Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(ai_model_requests_total[5m])) by (provider, model)",
            "legendFormat": "{{ provider }}/{{ model }}"
          }
        ]
      },
      {
        "title": "Token Consumption",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(ai_tokens_consumed_total[5m])) by (provider)",
            "legendFormat": "{{ provider }}"
          }
        ]
      }
    ]
  }
}
```

## 7. 日志分析查询

### 7.1 常用ELK查询
```json
{
  "kibana_queries": {
    "error_analysis": {
      "query": {
        "bool": {
          "must": [
            {"match": {"level": "ERROR"}},
            {"range": {"timestamp": {"gte": "now-1h"}}}
          ]
        }
      },
      "aggs": {
        "error_by_service": {
          "terms": {"field": "service.keyword"}
        }
      }
    },
    "security_events": {
      "query": {
        "bool": {
          "must": [
            {"match": {"level": "SECURITY"}},
            {"match": {"severity": "high"}}
          ]
        }
      }
    },
    "slow_queries": {
      "query": {
        "bool": {
          "must": [
            {"match": {"message": "slow query"}},
            {"range": {"duration_ms": {"gte": 1000}}}
          ]
        }
      }
    },
    "tenant_activity": {
      "query": {
        "bool": {
          "must": [
            {"term": {"tenant_id": "TENANT_ID_HERE"}},
            {"range": {"timestamp": {"gte": "now-24h"}}}
          ]
        }
      },
      "aggs": {
        "activity_by_hour": {
          "date_histogram": {
            "field": "timestamp",
            "interval": "1h"
          }
        }
      }
    }
  }
}
```

## 8. 监控自动化

### 8.1 健康检查脚本
```python
# scripts/health_check.py
import asyncio
import aiohttp
import sys
from datetime import datetime

class HealthChecker:
    def __init__(self):
        self.services = {
            'api-gateway': 'http://api-gateway:8000/health',
            'eino-service': 'http://eino-service:8080/health',
            'memory-service': 'http://memory-service:8001/health'
        }
        self.dependencies = {
            'postgres': 'postgresql://user:pass@postgres:5432/db',
            'redis': 'redis://redis:6379'
        }
    
    async def check_service_health(self, name: str, url: str):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'service': name,
                            'status': 'healthy',
                            'response_time': data.get('response_time', 0),
                            'timestamp': datetime.utcnow().isoformat()
                        }
                    else:
                        return {
                            'service': name,
                            'status': 'unhealthy',
                            'error': f'HTTP {response.status}',
                            'timestamp': datetime.utcnow().isoformat()
                        }
        except Exception as e:
            return {
                'service': name,
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def run_health_checks(self):
        tasks = []
        for name, url in self.services.items():
            tasks.append(self.check_service_health(name, url))
        
        results = await asyncio.gather(*tasks)
        
        # 检查整体健康状态
        all_healthy = all(result['status'] == 'healthy' for result in results)
        
        health_report = {
            'overall_status': 'healthy' if all_healthy else 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': results
        }
        
        print(json.dumps(health_report, indent=2))
        
        # 如果有服务不健康，返回非零退出码
        if not all_healthy:
            sys.exit(1)

if __name__ == '__main__':
    checker = HealthChecker()
    asyncio.run(checker.run_health_checks())
```

这个监控与日志系统设计文档提供了完整的可观测性解决方案，包括指标收集、日志管理、分布式追踪、告警机制和可视化展示等核心组件。