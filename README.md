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
- **SQLAlchemy**: ORM 数据库访问
- **PyGithub**: GitHub API 集成

### 前端
- **React 18**: UI 框架
- **TypeScript**: 类型安全
- **Vite**: 快速开发构建
- **TailwindCSS**: 样式框架
- **Monaco Editor**: 代码编辑器
- **Zustand**: 状态管理

## 快速开始

### 1. 环境准备

```bash
# Python 3.12+
python --version

# Node.js 18+
node --version

# Docker
docker --version
```

### 2. 后端设置

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 前端设置

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install pnpm

pnpm install

# 启动开发服务器
pnpm run dev
```

### 4. 访问应用

打开浏览器访问：`http://localhost:5173`

## 使用说明

### 创建会话

1. 点击左侧 **"New Session"** 按钮
2. 输入会话名称
3. （可选）输入 GitHub 仓库 URL

### 聊天对话

1. 在右侧聊天面板输入消息
2. 等待 Claude 实时流式响应
3. 支持中断正在进行的响应

### 文件操作

1. 在文件树中浏览工作区文件
2. 点击文件在编辑器中打开
3. 编辑后自动保存

### GitHub 集成

1. 在 GitHub 面板输入仓库 URL
2. 点击 **"Clone Repository"** 克隆代码
3. 修改代码后可提交和推送

## 项目结构

```
cc_python/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── routers/     # API 路由
│   │   ├── services/    # 业务逻辑
│   │   ├── models.py    # 数据模型
│   │   └── main.py      # 应用入口
│   └── requirements.txt
│
├── frontend/            # React 前端
│   ├── src/
│   │   ├── components/  # UI 组件
│   │   ├── hooks/       # 自定义 Hooks
│   │   ├── contexts/    # Context Providers
│   │   ├── lib/         # 工具库
│   │   └── services/    # API 客户端
│   └── package.json
│
└── docker/              # Docker 配置
    └── workspace/       # 工作区镜像
```

## 架构亮点

### WebSocket 管理

采用单例模式 + React Context 的架构：

```typescript
// 单例管理器（websocket.ts）
class WebSocketManager {
  // 全局连接管理
  // 事件发射器模式
}

// Context 状态（WebSocketContext.tsx）
<WebSocketProvider>
  // 提供全局 isConnected 状态
  // 自动连接管理
</WebSocketProvider>

// 组件使用
const { isConnected, send } = useWebSocketContext();
```

### Docker 工作区隔离

每个会话创建独立 Docker 容器：

- 隔离的文件系统
- 独立的命令执行环境
- 安全的代码运行沙箱

### 流式响应

后端通过 WebSocket 推送 Claude 的流式响应：

```python
async for event in client.query(messages):
    if event.type == "text_delta":
        await websocket.send_json({
            "type": "text_delta",
            "content": event.text
        })
```

## 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ANTHROPIC_API_KEY` | Claude API 密钥 | - |
| `ANTHROPIC_BASE_URL` | API 基础 URL | `https://api.anthropic.com` |
| `GITHUB_TOKEN` | GitHub 访问令牌 | - |
| `DATABASE_URL` | 数据库连接 | `sqlite+aiosqlite:///./sessions.db` |
| `DOCKER_HOST` | Docker 守护进程地址 | `unix:///var/run/docker.sock` |
| `WORKSPACE_BASE_PATH` | 工作区基础路径 | `workspaces` |

## 故障排除

### WebSocket 连接失败

1. 确认后端服务正在运行（端口 8000）
2. 检查浏览器控制台错误信息
3. 查看后端日志中的 WebSocket 相关日志

### Docker 容器创建失败

1. 确认 Docker 守护进程正在运行
2. 检查 Docker 镜像是否已构建
3. 查看后端日志中的 Docker 相关错误

### 会话无法加载

1. 检查数据库文件 `sessions.db` 是否存在
2. 确认数据库权限正常
3. 重启后端服务重新初始化数据库

## 开发者指南

### 添加新功能

1. **后端 API**：在 `backend/app/routers/` 添加路由
2. **前端服务**：在 `frontend/src/services/api.ts` 添加 API 调用
3. **UI 组件**：在 `frontend/src/components/` 创建组件
4. **状态管理**：在 `frontend/src/hooks/` 添加 Zustand store

### 调试技巧

**后端**：
```bash
# 查看详细日志
uvicorn app.main:app --reload --log-level debug
```

**前端**：
```javascript
// 浏览器控制台查看状态
console.log(useSessionStore.getState())
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
