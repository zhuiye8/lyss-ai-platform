# 技术文档知识库

## 📋 目录概述

本知识库汇总了所有通过Context7调研获得的最新技术文档和最佳实践，确保开发过程中使用的都是最新、最权威的技术方案。

---

## 🏗️ 知识库结构

### **核心技术框架**

#### **[EINO框架集成](./eino-framework)** - Go语言AI工作流编排
- **版本**: v0.3.52 (最新稳定版)
- **核心能力**: 多供应商模型编排、流式响应、工具调用
- **集成方案**: compose.NewChain + compose.NewGraph API

#### **[Mem0AI智能记忆](./mem0ai-integration)** - Python智能记忆框架  
- **版本**: 最新版本 (支持Qdrant集成)
- **核心能力**: 对话记忆、语义检索、用户画像生成
- **集成方案**: FastAPI + Qdrant向量数据库

#### **[Ant Design X](./antd-x-components)** - React聊天组件库
- **版本**: 最新版本
- **核心能力**: useXChat、useXAgent、Bubble.List、Sender组件
- **集成方案**: React 18 + TypeScript现代化聊天界面

### **参考项目架构分析**

#### **[Dify架构分析](./reference-projects/dify-analysis.md)**
- **供应商管理模式**: Provider + Model抽象层设计
- **凭证验证机制**: validate_provider_credentials模式
- **多租户架构**: 基于credential schema的数据隔离

#### **[One-API架构分析](./reference-projects/one-api-analysis.md)**  
- **Channel管理**: 统一多供应商API接入点设计
- **Token管理**: API Key配额控制和负载均衡
- **高可用架构**: 主从节点和故障转移机制

#### **[OpenWebUI架构分析](./reference-projects/openwebui-analysis.md)**
- **数据库架构**: SQLAlchemy并发优化方案
- **实时通信**: WebSocket + Socket.io最佳实践  
- **插件系统**: Pipelines框架Python扩展支持

### **版本锁定和兼容性**

#### **[版本锁定文档](./version-locks)**
- **技术栈版本**: 所有调研技术的确切版本号
- **兼容性矩阵**: 不同组件间的兼容性要求
- **升级路径**: 未来版本升级的安全路径

---

## 📅 文档更新记录

- **2025-01-20**: 初始建立，固化Context7调研成果
- **EINO**: v0.3.52 API用法和Go集成方案
- **Mem0AI**: FastAPI集成和Qdrant配置方案
- **Ant Design X**: 现代化聊天组件最新用法
- **参考项目**: Dify、One-API、OpenWebUI架构精华总结

---

## 🎯 使用指南

### **开发阶段对应文档**
1. **Provider Service开发**: 重点参考 [One-API架构分析](./reference-projects/one-api-analysis.md)
2. **Chat Service开发**: 重点参考 [EINO框架集成](./eino-framework/)
3. **Memory Service开发**: 重点参考 [Mem0AI智能记忆](./mem0ai-integration/)
4. **Frontend开发**: 重点参考 [Ant Design X组件](./antd-x-components/)

### **技术栈选择原则**
- **所有版本号以本知识库为准** - 避免开发周期中的版本漂移问题
- **优先使用调研确认的API** - 减少试错成本和兼容性问题
- **参考架构模式而非具体实现** - 适配我们的业务场景

---

## ⚠️ 重要提醒

1. **版本一致性**: 开发过程中严格按照本知识库的版本要求
2. **API稳定性**: 使用经过Context7验证的稳定API接口
3. **架构模式**: 参考成功项目的设计模式，避免重复踩坑
4. **持续更新**: 定期使用Context7更新技术栈到最新稳定版本