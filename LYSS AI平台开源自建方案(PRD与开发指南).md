# **LYSS AI 平台：精益与智能的自托管技术栈 (PRD & 开发指南)**

## **第一部分：产品需求文档 (PRD) - 成本意识架构师版**

### **1.0 愿景与核心原则**

*   **愿景：** 创建一个自托管、高效率的 AI 交互平台，旨在最大限度地降低运营成本并最大化对话智能。
*   **核心原则：**
    1.  **成本优先：** 每个架构决策都必须优先考虑减少令牌（Token）消耗。
    2.  **治理为本：** 所有核心 PRD v5.0 需求（多供应商、RBAC、配额）都必须通过健壮的开源工具来满足。
    3.  **简约与可扩展性：** 技术栈必须轻量、易于单个开发者部署和维护，同时为未来的增长提供可扩展性。
    4.  **无外部依赖：** 系统的核心功能运行不应依赖外部服务，如电子邮件服务器。

### **2.0 升级版的四层架构**

我们将从简单的三层模型演进到一个更精密的四层架构。该设计明确地将治理与智能分离开来，从而创建一个更清晰、更强大的系统。

1.  **表现层 (The Face): LobeChat**
    *   **为何改变？** 虽然 Ant Design X 提供了出色的组件，但 LobeChat 是一个完整、设计精美、开源的 AI 聊���*框架*。¹ 它提供了开箱即用的精致用户体验，包括通过认证提供商实现的多用户支持（我们可以通过直接使用令牌来绕过）、插件系统和令人惊叹的用户界面。⁴ 这极大地加速了前端开发。它是可自托管且高度可配置的。⁶
2.  **智能与记忆层 (The Brain): FastAPI + Mem0**
    *   **为何选择此组合？** 这是我们成本节约策略的核心。
    *   FastAPI 因其速度和简洁性，仍然是我们业务逻辑服务的首选。
    *   Mem0 是您要求的专业化、自我改进的记忆层。它能智能地压缩对话历史，在保留关键上下文的同时，极大地减少每次请求发送的令牌数量（可节省高达 80-90%）。¹⁰ 它可以自托管，并与 Python 无缝集成。¹¹ 该层将接收来自前端的请求，用压缩后的记忆来丰富它们，然后将它们传递给治理层。
3.  **治理与路由层 (The Gatekeeper): Portkey AI 网关 (开源)**
    *   **为何改变？** Portkey 的开源网关异常轻量、快速（延迟 <1ms）且功能丰富。¹⁴ 它为超过 200 种模型提供了统一的 API，支持自动重试，以及至关重要的**智能缓存**。¹⁵ 这种缓存为相同或相似的查询提供了第二层令牌削减，完美契合我们的成本优先原则。虽然 one-api 也不错，但 Portkey 对性能和语义缓存等功能的专注，使其成为这个“卓越”架构的更优选择。¹⁵
4.  **数据持久层 (The Foundation): PostgreSQL + Redis**
    *   **为何选择此组合？**
    *   PostgreSQL 仍然是结构化数据（用户、日志等）的坚实选择，并得到我们所选组件的支持。
    *   Redis 被添加为 Portkey 缓存的高性能后端，也可以被 Mem0 用作其记忆存储，确保全局的低延迟操作。¹⁶

### **3.0 功能需求与用户故事**

#### **3.1 管理员 (您)**

*   **用户管理 (无需邮件):** 作为管理员，我可以直接通过 Portkey 管理界面创建用户并为他们生成安全的 API 令牌（虚拟密钥），而无需电子邮件验证。¹⁴
*   **模型与供应商管理:** 作为管理员，我可以通过 Portkey 网关连接到多个 LLM 供应商（OpenAI, Anthropic, Ollama 等）。¹⁴
*   **RBAC 与配额控制:** 作为管理员，我可以创建用户组/工作区，为它们分配特定模型，并设置带有到期日期的硬性令牌/成本限制，以防止预算超支。¹⁹
*   **成本节约:** 作为管理员，我可以在 Portkey 网关上启用和配置缓存以减少冗余的 API 调用。¹⁴ 我还可以依赖 Mem0 层自动减少提示（Prompt）的令牌大小。

#### **3.2 最终用户**

*   **智能对���:** 作为用户，系统能记住我过去对话中的关键偏好（例如，“我是一名 Python 开发者”，“我喜欢简洁的回答”），并利用这些上下文提供更相关和个性化的回应。¹⁰
*   **无缝体验:** 作为用户，我使用管理员提供的 API 密钥登录，并与一个快速、精致的聊天界面 (LobeChat) 互动。¹
*   **动态模型访问:** 作为用户，我的聊天界面中的模型选择器只显示我被授权访问的特定模型。

---

## **第二部分：终极开发者指南**

这份分步指南是您的完整路线图。我们将使用 Docker Compose 来编排所有服务，以实现简单的一键式启动。

### **阶段 0: 项目设置**

1.  **安装工具:** 确保您已安装 Docker 和 Docker Compose。
2.  **项目结构:** 创建一个名为 `lyss-intelligent-stack` 的根目录，结构如下：
    ```
    lyss-intelligent-stack/
    ├── docker-compose.yml
    └── backend/
        ├── Dockerfile
        ├── main.py
        └── requirements.txt
    ```

### **阶段 1: 部署基础与网关 (PostgreSQL, Redis, Portkey)**

这是我们用于数据、缓存和治理的核心基础设施。

1.  创建 `docker-compose.yml`:
    此文件将定义我们的三个核心基础设施服务。
    ```yaml
    version: '3.8'

    services:
      postgres:
        image: postgres:15-alpine
        container_name: lyss_postgres
        environment:
          POSTGRES_USER: lyss_user
          POSTGRES_PASSWORD: your_strong_password_here # 请修改此密码
          POSTGRES_DB: lyss_db
        volumes:
          - ./postgres_data:/var/lib/postgresql/data
        restart: always
        networks:
          - lyss_network

      redis:
        image: redis:7-alpine
        container_name: lyss_redis
        restart: always
        networks:
          - lyss_network

      portkey-gateway:
        image: portkeyai/gateway:latest # 使用官方的轻量级网关
        container_name: lyss_portkey_gateway
        ports:
          - "8787:8787" # 暴露 Portkey 的端口
        environment:
          # 这是一个基础配置。我们稍后将通过 API/UI 管理供应商。
          # 现在，我们先让它指向 Redis 以进行缓存。
          PORTKEY_GATEWAY_CONFIG: |
            cache:
              enabled: true
              redis_url: "redis://redis:6379"
        depends_on:
          - redis
        restart: always
        networks:
          - lyss_network

    networks:
      lyss_network:
        driver: bridge
    ```

2.  启动基础设施:
    在根目录中运行: `docker-compose up -d postgres redis portkey-gateway`。
    您的核心服务现已运行。Portkey 正在 `http://localhost:8787` 上监听。

### **阶段 2: 构建智能层 (FastAPI + Mem0)**

该服务是整个操作的大脑。

1.  **定义 `backend/requirements.txt`:**
    ```plaintext
    fastapi
    uvicorn[standard]
    mem0ai
    openai
    python-dotenv
    requests
    ```

2.  创建 `backend/main.py`:
    这是魔法发生的地方。我们创建一个端点，该端点在调用 Portkey 网关之前使用 Mem0 处理记忆。
    ```python
    import os
    from fastapi import FastAPI, HTTPException, Depends
    from fastapi.security import APIKeyHeader
    from pydantic import BaseModel
    from typing import List
    import requests
    from mem0 import Memory

    # --- 配置 ---
    # 在真实应用中，使用 Pydantic 的 BaseSettings 从 .env 文件加载
    PORTKEY_GATEWAY_URL = "http://portkey-gateway:8787/v1"

    # 初始化 Mem0。默认情况下，它使用内存中的向量存储，
    # 这对于轻量级启动来说非常完美。
    # 如需持久化，您可以配置它使用 Qdrant、Redis 等。
    mem0 = Memory()

    app = FastAPI(title="LYSS 智能层")
    api_key_header = APIKeyHeader(name="Authorization")

    # --- Pydantic 模型 ---
    class ChatMessage(BaseModel):
        role: str
        content: str

    class ChatRequest(BaseModel):
        messages: List[ChatMessage]
        model: str
        user_id: str # 对 Mem0 区分用户至关重要

    # --- API 端点 ---
    @app.post("/chat/memory")
    async def chat_with_memory(req: ChatRequest, token: str = Depends(api_key_header)):
        """
        此端点提供具有持久记忆的聊天接口。
        """
        # 1. 从 Mem0 检索相关记忆
        try:
            relevant_memories = mem0.search(
                query=req.messages[-1].content, # 基于最新消息进行搜索
                user_id=req.user_id,
                limit=5
            )
            memory_context = "\n".join(
                [f"- {entry['memory']}" for entry in relevant_memories.get("results", [])]
            )
        except Exception as e:
            print(f"Mem0 搜索失败: {e}")
            memory_context = ""

        # 2. 将新的对话轮次添加到 Mem0
        try:
            # 我们只添加最后两条消息（用户 + 助手）作为上下文
            mem0.add(
                messages=[msg.dict() for msg in req.messages[-2:]],
                user_id=req.user_id
            )
        except Exception as e:
            print(f"Mem0 添加失败: {e}")

        # 3. 构建带有记忆上下文的新提示
        system_prompt = f"""你是一个乐于助人的 AI 助手。
        以下是与该用户过去对话的一些相关记忆：
        {memory_context}

        现在，请继续对话。
        """

        # 准备发送到 Portkey 网关的消息
        final_messages = [
            {"role": "system", "content": system_prompt}
        ] + [msg.dict() for msg in req.messages]

        # 4. 调用 Portkey 网关以获取最终的 LLM 响应
        headers = {
            "Authorization": token, # 将用户的令牌传递给 Portkey
            "Content-Type": "application/json"
        }
        payload = {
            "model": req.model,
            "messages": final_messages
        }

        try:
            response = requests.post(
                f"{PORTKEY_GATEWAY_URL}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=e.response.status_code if e.response else 500, detail=str(e))
    ```

3.  **创建 `backend/Dockerfile`:**
    ```dockerfile
    FROM python:3.11-slim
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    COPY . .
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
    ```

4.  **将后端服务添加到 `docker-compose.yml`:**
    ```yaml
    #... (postgres, redis, portkey-gateway 服务)

      backend:
        build: ./backend
        container_name: lyss_backend
        ports:
          - "8000:8000"
        depends_on:
          - portkey-gateway
        restart: always
        networks:
          - lyss_network

    #... (networks 定义)
    ```

### **阶段 3: 部署前端 (LobeChat)**

我们将 LobeChat 作为另一个 Docker 容器进行部署。它是预构建的，并且可以通过环境变量高度配置。

1.  **将 LobeChat 添加到 `docker-compose.yml`:**
    ```yaml
    #... (postgres, redis, portkey-gateway, backend 服务)

      lobe-chat:
        image: lobehub/lobe-chat
        container_name: lyss_lobe_chat
        ports:
          - "3210:3210" # LobeChat 的默认端口
        environment:
          # --- 核心配置 ---
          # 将 LobeChat 指向我们的 FastAPI 后端作为 OpenAI 端点
          OPENAI_PROXY_URL: "http://backend:8000"
          # 禁用多用户认证，因为我们使用 API 密钥
          ACCESS_CODE: "your_super_secret_access_code" # 请修改此访问码
        depends_on:
          - backend
        restart: always
        networks:
          - lyss_network

    #... (networks 定义)
    ```

### **阶段 4: 最终启动与配置**

1.  **启动所有服务:**
    在您的根目录中，运行 `docker-compose up -d --build`。这将构建您的 FastAPI 服务并启动所有容器。
2.  **配置 Portkey 并获取 API 密钥:**
    *   虽然 Portkey 可以通过 API 进行配置，但对于单人开发者来说，最简单的方法是使用他们免费的托管仪表板来管理您的自托管网关。
    *   在 portkey.ai 注册一个免费账户。¹⁴
    *   在 Portkey 仪表板中，连接到您的自托管网关（它会引导您完成）。
    *   **创建虚拟密钥:** 转到“Virtual Keys”部分。在这里，您将添加来自 OpenAI、Anthropic 等的实际 API 密钥。Portkey 会安全地存储它们。
    *   **生成用户令牌:** 为您平台的每个“用户”创建一个新的虚拟密钥。此密钥充当其唯一的 API 令牌。您可以为其附加策略，例如它可以访问哪些模型以及其支出限制是多少。这就是您的 RBAC 和配额系统。¹⁹
    *   **启用缓存:** 在 Portkey 仪表板的网关设置中，确保缓存已启用并指向您的 Redis 实例。
3.  **使用您的平台:**
    *   在浏览器中打开 `http://localhost:3210`。
    *   输入您在 `docker-compose.yml` 文件中设置的 `ACCESS_CODE`。
    *   在 LobeChat 的设置中，转到“语言模型”部分。
    *   对于 OpenAI API 密钥，粘贴您从 Portkey 生成的**虚拟密钥**之一。
    *   开始聊天！您的请求现在将流经 LobeChat -> FastAPI (获取记忆) -> Portkey (获取缓存、路由和治理) -> 最终的 LLM。

### **总结与后续步骤**

您现在已经构建了一个异常强大、轻量且成本优化的 AI 平台。此架构之所以优越，是因为它智能地分离了关注点，为每项工作使用了同类最佳的开源工具，并采用双管齐下的方法直接解决了您降低令牌消耗的核心需求：**智能记忆 (Mem0)** 和 **智能缓存 (Portkey + Redis)**。

**您的后续步骤:**

*   **探索高级缓存:** 研究 Portkey 的“语义缓存”，以实现更智能的成本节约。
*   **持久化记忆:** 配置 Mem0 使用持久化的向量数据库（如 Qdrant 或 Redis），而不是其内存中的默认设置，以实现跨重启的长期记忆。
*   **自定义仪表板:** 使用 FastAPI 后端创建新的端点，查询 Portkey 和 Mem0 的日志，以构建自定义的分析仪表板。

#### **引用的著作**

1.  Groups API | Permit.io Documentation, 访问时间为 七月 7, 2025， [https://docs.permit.io/api/rebac/groups/](https://docs.permit.io/api/rebac/groups/)
2.  Permissions - Django REST framework, 访问时间为 七月 7, 2025， [https://www.django-rest-framework.org/api-guide/permissions/](https://www.django-rest-framework.org/api-guide/permissions/)
3.  Permissions - The REST API basics | Akeneo APIs, 访问时间为 七月 7, 2025， [https://api.akeneo.com/documentation/permissions.html](https://api.akeneo.com/documentation/permissions.html)
4.  Support Multi-User Management - Iden... - LobeHub, 访问时间为 七月 7, 2025， [https://lobehub.com/docs/usage/features/auth](https://lobehub.com/docs/usage/features/auth)
5.  LobeChat Supports Multi-User Management with Clerk and Next-Auth - LobeHub, 访问时间为 七月 7, 2025， [https://lobehub.com/changelog/2024-02-08-sso-oauth](https://lobehub.com/changelog/2024-02-08-sso-oauth)
6.  Build Your Own LobeChat - Choose Your Deployment Platform - LobeHub, 访问时间为 七月 7, 2025， [https://lobehub.com/docs/self-hosting/start](https://lobehub.com/docs/self-hosting/start)
7.  Customize LobeChat Deployment with Environment Variables - LobeHub, 访问时间为 七月 7, 2025， [https://lobehub.com/docs/self-hosting/environment-variables/basic](https://lobehub.com/docs/self-hosting/environment-variables/basic)
8.  Added Lobe Chat to BigBearCasaOS - Big Bear Community, 访问时间为 七月 7, 2025， [https://community.bigbeartechworld.com/t/added-lobe-chat-to-bigbearcasaos/2453](https://community.bigbeartechworld.com/t/added-lobe-chat-to-bigbearcasaos/2453)
9.  LobeChat: Free Open Source LLM Platform - YouTube, 访问时间为 七月 7, 2025， [https://www.youtube.com/watch?v=2bjkx3QFOQo](https://www.youtube.com/watch?v=2bjkx3QFOQo)
10. Mem0 - The Memory Layer for your AI Apps, 访问时间为 七月 7, 2025， [https://mem0.ai/](https://mem0.ai/)
11. GitHub - mem0ai/mem0: Memory for AI Agents; Announcing OpenMemory MCP, 访问时间为 七月 7, 2025， [https://github.com/mem0ai/mem0](https://github.com/mem0ai/mem0)
12. Quickstart - Mem0, 访问时间为 七月 7, 2025， [https://docs.mem0.ai/quickstart](https://docs.mem0.ai/quickstart)
13. into-the-night/mem0-feat-gemini: The Memory layer for your AI apps (now with Gemini!), 访问时间为 七月 7, 2025， [https://github.com/into-the-night/mem0-feat-gemini](https://github.com/into-the-night/mem0-feat-gemini)
14. Portkey-AI/gateway: A blazing fast AI Gateway with integrated guardrails. Route to 200+ LLMs, 50+ AI Guardrails with 1 fast & friendly API. - GitHub, 访问时间为 七月 7, 2025， [https://github.com/Portkey-AI/gateway](https://github.com/Portkey-AI/gateway)
15. In-Depth Analysis of AI Gateway: The New Generation of Intelligent Traffic Control Hub, 访问时间为 七月 7, 2025， [https://jimmysong.io/en/blog/ai-gateway-in-depth/](https://jimmysong.io/en/blog/ai-gateway-in-depth/)
16. Smarter memory management for AI agents with Mem0 and Redis, 访问时间为 七月 7, 2025， [https://redis.io/blog/smarter-memory-management-for-ai-agents-with-mem0-and-redis/](https://redis.io/blog/smarter-memory-management-for-ai-agents-with-mem0-and-redis/)
17. Helicone/ai-gateway: The fastest, lightest, and easiest-to-integrate AI gateway on the market. Fully open-sourced. - GitHub, 访问时间为 七月 7, 2025， [https://github.com/Helicone/ai-gateway](https://github.com/Helicone/ai-gateway)
18. Portkey-AI/portkey-python-sdk: Build reliable, secure, and production-ready AI apps easily., 访问时间为 七月 7, 2025， [https://github.com/Portkey-AI/portkey-python-sdk](https://github.com/Portkey-AI/portkey-python-sdk)
19. Role-based access control (RBAC) for LLM applications - Portkey, 访问时间为 七月 7, 2025， [https://portkey.ai/blog/rbac-for-llm-applications](https://portkey.ai/blog/rbac-for-llm-applications)
20. Role-based access control - Portkey, 访问时间为 七月 7, 2025， [https://portkey.ai/for/rbac](https://portkey.ai/for/rbac)
