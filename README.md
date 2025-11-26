# Claude Code 网页端在线编程平台

一个基于 Claude Agent SDK 的在线编程平台，提供实时聊天、代码编辑、GitHub 集成和 Docker 工作区隔离。

## 功能特性

- 🤖 **Claude AI 助手**：通过 WebSocket 实时流式对话
- 💻 **Monaco 编辑器**：专业的代码编辑体验
- 🔄 **会话管理**：支持多个独立会话
- 🐙 **GitHub 集成**：克隆仓库、提交代码、创建 PR
- 🐳 **Docker 隔离**：每个会话独立的工作区容器
- 📁 **文件管理**：浏览和编辑工作区文件

## 技术栈

### 后端
- **FastAPI**: 高性能 Web 框架
- **claude-agent-sdk-python**: Claude AI SDK
- **Docker SDK**: 容器管理
- **SQLAlchemy**: ORM 数据库访问 (MySQL)
- **PyGithub**: GitHub API 集成

### 前端
- **React 18**: UI 框架
- **TypeScript**: 类型安全
- **Vite**: 快速开发构建
- **TailwindCSS**: 样式框架
- **Monaco Editor**: 代码编辑器
- **Zustand**: 状态管理

## 架构设计

### 后端架构

采用分层架构设计，遵循 Clean Architecture 原则：

```
backend/app/
├── config/              # 配置模块
│   ├── settings.py      # 应用配置
│   └── logging_config.py # 日志配置
├── db/                  # 数据库层
│   ├── base.py          # 数据库引擎和基类
│   ├── models/          # ORM 模型
│   ├── repository/      # 数据访问层
│   └── schemas/         # Pydantic 模型
├── routers/             # API 路由层 (只负责路由定义)
│   ├── sessions.py      # 会话路由
│   ├── chat.py          # 聊天路由
│   ├── github.py        # GitHub 路由
│   └── workspace.py     # 工作空间路由
├── services/            # 业务逻辑层
│   ├── session_service.py    # 会话服务
│   ├── chat_service.py       # 聊天服务
│   ├── github_api_service.py # GitHub API 服务
│   ├── workspace_service.py  # 工作空间服务
│   ├── claude_service.py     # Claude AI 服务
│   └── docker_service.py     # Docker 服务
├── utils/               # 工具模块
│   ├── exceptions/      # 异常处理
│   └── model/           # 响应模型
└── main.py              # 应用入口
```

### 设计模式

1. **Repository Pattern**: 数据访问与业务逻辑分离
2. **Service Layer**: 所有业务逻辑在 Service 层实现
3. **BaseResponse**: 统一的 API 响应格式
4. **@log_print**: 方法级别的日志装饰器
5. **Exception Handlers**: 全局异常处理

### API 响应格式

所有非流式 API 返回统一的 `BaseResponse` 格式：

```json
{
    "code": 200,
    "message": "success",
    "data": {...}
}
```

列表响应使用 `ListResponse`：

```json
{
    "code": 200,
    "message": "success",
    "data": {
        "items": [...],
        "total": 10
    }
}
```

## 快速开始

### 1. 环境准备

```bash
# Python 3.12+
python --version

# Node.js 18+
node --version

# Docker (可选)
docker --version
```

### 2. 数据库配置

项目使用 MySQL 数据库，配置在 `backend/app/config/config.yaml`：

```yaml
database:
  type: mysql
  host: "172.27.1.20"
  port: 3306
  user: "employee_platform"
  password: "e_Plat123"
  name: "employee_platform"
  charset: "utf8mb4"
  pool_size: 10
  max_overflow: 20
  pool_recycle: 3600
```

数据库表名使用 `code_` 前缀：
- `code_sessions` - 会话表
- `code_messages` - 消息表
- `code_github_tokens` - GitHub Token 表
- `code_repositories` - 仓库表

### 3. 后端设置

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
python app/main.py
```

### 4. 前端设置

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 5. 访问应用

- 前端: `http://localhost:5173`
- 后端 API 文档: `http://localhost:8000/docs`
- 健康检查: `http://localhost:8000/health`

## 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ANTHROPIC_API_KEY` | Claude API 密钥 | - |
| `ANTHROPIC_BASE_URL` | API 基础 URL | `https://api.anthropic.com` |
| `GITHUB_TOKEN` | GitHub 访问令牌 | - |

### 日志配置

日志文件存储在 `backend/logs/` 目录：
- `app.log` - 应用日志
- 自动按天轮转，保留 30 天

## 故障排除

### WebSocket 连接失败

1. 确认后端服务正在运行（端口 8000）
2. 检查浏览器控制台错误信息
3. 查看后端日志中的 WebSocket 相关日志

### 数据库连接失败

1. 检查 MySQL 服务是否运行
2. 验证数据库配置是否正确
3. 确认网络连接正常

### Docker 容器创建失败

1. 确认 Docker 守护进程正在运行
2. 检查 Docker 镜像是否已构建
3. 查看后端日志中的 Docker 相关错误

## 开发者指南

### 添加新功能

1. **Service 层**：在 `backend/app/services/` 创建服务类
   - 使用 `@log_print` 装饰器
   - 返回 `BaseResponse` 或 `ListResponse`
   
2. **Router 层**：在 `backend/app/routers/` 添加路由
   - 只负责路由定义和参数验证
   - 业务逻辑委托给 Service
   
3. **前端**：
   - 在 `frontend/src/services/api.ts` 添加 API 调用
   - 在 `frontend/src/components/` 创建组件

### 代码规范

```python
# Service 方法示例
@log_print
async def get_session(self, session_id: str):
    """获取会话详情"""
    try:
        session = await self.session_repo.get_session_by_id(session_id)
        if not session:
            return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在")
        return BaseResponse.success(data=session.to_dict(), message="获取成功")
    except Exception as e:
        return BaseResponse.error(message=f"获取会话失败: {str(e)}")
```
