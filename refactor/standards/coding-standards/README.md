# 编码规范标准

## 📋 目录概述

本目录包含Lyss AI平台的完整编码规范，按照技术栈分类组织：

---

## 📚 规范文档

### **[通用编码原则](./general-principles.md)**
- 代码注释规范
- 错误处理原则
- 安全编码原则
- 通用检查清单

### **[Python (FastAPI) 编码规范](./python-fastapi.md)**
- 文件头注释和导入顺序
- 类定义和方法规范
- API路由设计
- 数据模型定义
- 异常处理机制

### **[Go 编码规范](./go-standards.md)**
- 包和文件注释
- 结构体定义规范
- 方法定义和错误处理
- HTTP处理器实现
- 自定义错误类型

### **[TypeScript/React 编码规范](./typescript-react.md)**
- 组件定义规范
- Hook设计模式
- 类型定义标准
- 状态管理最佳实践
- 性能优化指南

---

## 🔧 使用指南

1. **选择对应规范**：根据项目技术栈选择相应的编码规范文档
2. **遵循通用原则**：所有代码都应遵循通用编码原则
3. **代码审查**：使用各规范的检查清单进行代码审查
4. **工具集成**：配置相应的代码检查工具（ESLint、Pylint、golangci-lint等）

---

## 📋 快速检查清单

### **提交前检查**
- [ ] 代码符合对应技术栈的编码规范
- [ ] 注释使用中文且内容清晰
- [ ] 错误处理完整且具体
- [ ] 日志记录恰当
- [ ] 无硬编码敏感信息

### **代码审查检查**
- [ ] 代码结构清晰合理
- [ ] 函数/方法职责单一
- [ ] 变量命名语义明确
- [ ] 测试覆盖充分
- [ ] 性能考虑周到

---

## 🛠️ 工具配置

### **Python项目**
```bash
# 安装代码检查工具
pip install pylint black isort mypy

# 运行代码检查
pylint your_module.py
black --check your_module.py
isort --check-only your_module.py
mypy your_module.py
```

### **Go项目**
```bash
# 安装代码检查工具
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

# 运行代码检查
golangci-lint run
go fmt ./...
go vet ./...
```

### **TypeScript/React项目**
```bash
# 安装代码检查工具
npm install --save-dev eslint prettier @typescript-eslint/parser

# 运行代码检查
npm run lint
npm run type-check
npm run format:check
```