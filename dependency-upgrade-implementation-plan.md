# Python依赖升级实施方案

## 实施概述

本文档提供了Lyss AI平台Python依赖升级的详细技术实施方案，包括具体的升级步骤、测试策略、风险缓解措施和回滚计划。

## 阶段1: 紧急安全修复 (1-2周)

### 1.1 FastAPI升级 (0.104.1 → 0.116.0+)

#### 破坏性变更分析
- **Starlette依赖**: 可能需要同时升级Starlette
- **中间件变更**: 中间件API可能有微调
- **异步处理**: 异步上下文管理可能有变化

#### 升级步骤
```bash
# 1. 备份当前环境
cp backend/requirements.txt backend/requirements.txt.backup

# 2. 升级FastAPI
pip install 'fastapi>=0.116.0'

# 3. 检查依赖冲突
pip check

# 4. 运行测试
pytest backend/tests/ -v
```

#### 兼容性检查点
- [ ] API路由正常工作
- [ ] 中间件链完整
- [ ] 异步端点响应正常
- [ ] 错误处理机制正常
- [ ] 文档生成正常

### 1.2 python-jose升级 (3.3.0 → 3.3.1+)

#### 升级步骤
```bash
# 1. 升级python-jose
pip install 'python-jose[cryptography]>=3.3.1'

# 2. 验证加密后端
python -c "from jose import jwt; print(jwt.get_unverified_header('dummy'))"

# 3. 测试JWT功能
pytest backend/tests/test_auth.py -v
```

#### 测试重点
- [ ] JWT令牌生成和验证
- [ ] 密钥轮换功能
- [ ] 算法验证严格性
- [ ] 错误处理机制

### 1.3 transformers升级 (4.36.2 → 4.52.4+)

#### 升级步骤
```bash
# 1. 升级transformers
pip install 'transformers>=4.52.4'

# 2. 检查模型兼容性
python -c "from transformers import AutoModel; print('OK')"

# 3. 测试memory-service
pytest memory-service/tests/ -v
```

#### 兼容性检查点
- [ ] 模型加载正常
- [ ] 文本处理管道正常
- [ ] 向量化功能正常
- [ ] 内存使用在预期范围内

## 阶段2: 高优先级升级 (2-4周)

### 2.1 Redis客户端升级 (5.0.1 → 6.2.0+)

#### API变更分析
```python
# 旧版本 (5.0.1)
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# 新版本 (6.2.0+) - 基本兼容，但建议使用连接池
redis_client = redis.Redis(
    host='localhost', 
    port=6379, 
    db=0,
    connection_pool=redis.ConnectionPool(max_connections=20)
)
```

#### 升级步骤
```bash
# 1. 升级redis
pip install 'redis>=6.2.0'

# 2. 更新配置
# 检查redis配置是否需要调整

# 3. 测试连接
python -c "import redis; r=redis.Redis(); r.ping()"

# 4. 运行完整测试
pytest backend/tests/test_redis.py -v
```

### 2.2 OpenAI客户端升级 (1.3.7 → 1.93.1+)

#### 重大API变更
```python
# 旧版本 (1.3.7)
import openai
openai.api_key = "sk-..."
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello"}]
)

# 新版本 (1.93.1+)
from openai import OpenAI
client = OpenAI(api_key="sk-...")
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello"}]
)
```

#### 代码迁移清单
- [ ] 更新导入语句
- [ ] 修改客户端初始化
- [ ] 更新API调用语法
- [ ] 调整错误处理
- [ ] 更新异步调用

### 2.3 mem0ai升级 (0.1.0 → 0.1.114)

#### 升级步骤
```bash
# 1. 升级mem0ai
pip install 'mem0ai>=0.1.114'

# 2. 检查配置文件
# 验证mem0ai配置兼容性

# 3. 测试基本功能
python -c "from mem0 import Memory; m = Memory(); print('OK')"

# 4. 运行memory-service测试
pytest memory-service/tests/test_memory.py -v
```

## 阶段3: 中等优先级升级 (1-3个月)

### 3.1 批量升级策略

#### 升级批次
```bash
# 批次1: 数据库相关
pip install 'sqlalchemy>=2.0.41' 'asyncpg>=0.30.0' 'psycopg2-binary>=2.9.10'

# 批次2: 验证和配置
pip install 'pydantic>=2.11.0' 'uvicorn[standard]>=0.35.0'

# 批次3: 其他依赖
pip install 'gunicorn>=21.2.0' 'alembic>=1.13.1'
```

## 测试策略

### 单元测试
```bash
# Backend服务测试
cd backend
pytest tests/ --cov=. --cov-report=html

# Memory服务测试
cd memory-service
pytest tests/ --cov=. --cov-report=html
```

### 集成测试
```bash
# 启动测试环境
docker-compose -f docker-compose.test.yml up -d

# 运行端到端测试
python scripts/run_integration_tests.py

# API测试
curl -X POST http://localhost:8000/api/v1/health
```

### 性能测试
```bash
# 使用wrk进行负载测试
wrk -t12 -c400 -d30s http://localhost:8000/api/v1/health

# 内存使用监控
python scripts/monitor_memory_usage.py
```

## 风险缓解措施

### 1. 自动化测试
```yaml
# .github/workflows/dependency-upgrade.yml
name: Dependency Upgrade Test
on:
  pull_request:
    paths:
      - '**/requirements.txt'
      - '**/pyproject.toml'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install -r memory-service/requirements.txt
      - name: Run tests
        run: |
          pytest backend/tests/
          pytest memory-service/tests/
```

### 2. 渐进式部署
```bash
# 1. 在staging环境验证
docker-compose -f docker-compose.staging.yml up -d

# 2. 运行健康检查
./scripts/health_check.sh

# 3. 蓝绿部署到生产环境
./scripts/blue_green_deploy.sh
```

### 3. 监控和告警
```python
# scripts/monitor_dependencies.py
import subprocess
import requests

def check_vulnerabilities():
    """检查已知漏洞"""
    result = subprocess.run(['safety', 'check'], capture_output=True, text=True)
    if result.returncode != 0:
        send_alert(f"发现安全漏洞: {result.stdout}")

def check_outdated_packages():
    """检查过期包"""
    result = subprocess.run(['pip', 'list', '--outdated'], capture_output=True, text=True)
    if result.stdout:
        send_alert(f"发现过期包: {result.stdout}")

def send_alert(message):
    """发送告警"""
    # 实现告警逻辑
    pass
```

## 回滚计划

### 1. 快速回滚
```bash
# 1. 恢复requirements.txt
git checkout HEAD~1 -- backend/requirements.txt memory-service/requirements.txt

# 2. 重新安装依赖
pip install -r backend/requirements.txt
pip install -r memory-service/requirements.txt

# 3. 重启服务
docker-compose restart backend memory-service
```

### 2. 数据库回滚
```bash
# 如果涉及数据库迁移
alembic downgrade -1

# 恢复数据库备份
pg_restore -d lyss_platform backup_before_upgrade.sql
```

### 3. 容器回滚
```bash
# 回滚到上一个稳定版本
docker-compose down
docker-compose up -d --scale backend=0
docker-compose up -d --scale backend=1
```

## 验证清单

### 功能验证
- [ ] 用户认证和授权正常
- [ ] API端点响应正常
- [ ] 数据库操作正常
- [ ] 缓存功能正常
- [ ] AI模型推理正常
- [ ] 记忆服务正常

### 性能验证
- [ ] 响应时间在预期范围内
- [ ] 内存使用正常
- [ ] CPU使用率正常
- [ ] 数据库连接池正常
- [ ] 并发处理能力正常

### 安全验证
- [ ] 漏洞扫描通过
- [ ] 身份验证机制正常
- [ ] 数据加密正常
- [ ] 访问控制正常
- [ ] 审计日志正常

## 文档更新

### 1. 更新部署文档
```markdown
# 更新docker-compose文件
version: '3.8'
services:
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - FASTAPI_VERSION=0.116.0+
```

### 2. 更新API文档
```bash
# 重新生成API文档
cd backend
python -c "from main import app; import json; print(json.dumps(app.openapi(), indent=2))" > api_schema.json
```

### 3. 更新依赖文档
```bash
# 生成依赖树
pip install pipdeptree
pipdeptree --json > dependency_tree.json
```

## 后续维护

### 1. 定期安全扫描
```bash
# 设置cron job
0 9 * * 1 cd /path/to/project && safety check --json > security_report.json
```

### 2. 依赖更新策略
- 每月第一个周一检查依赖更新
- 安全更新立即应用
- 功能更新经测试后应用
- 重大版本更新需要评估影响

### 3. 监控和告警
- 集成Snyk进行持续监控
- 配置Slack/钉钉告警
- 定期生成依赖报告

---

*实施方案制定日期: 2025年7月8日*  
*预计完成时间: 2025年9月30日*  
*风险等级: 中等*