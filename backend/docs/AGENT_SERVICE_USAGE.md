# AgentService 使用指南

## 概述

`AgentService` 是一个简化的 Claude Agent SDK 集成服务，提供流式和非流式对话功能，支持多轮会话。

## 特性

- **流式对话**: 实时返回响应
- **非流式对话**: 等待完整响应后返回
- **多轮会话**: 通过 `session_id` 维护对话上下文
- **自动 workspace 管理**: 自动在 `{user_home}/workspace/{session_id}` 创建工作目录
- **自动配置复制**: 自动复制项目的 `.claude` 配置到 workspace

## 快速开始

### 基本用法

```python
import asynciotem
from app.core.agent_service import agent_service

async def main():
    # 流式对话
    async for msg in agent_service.chat_stream(
        prompt="创建一个 hello.py 文件",
        session_id="my-session-001",
    ):
        print(f"[{msg.type}] {msg.content}")
    
    # 关闭会话
    await agent_service.close_session("my-session-001")

asyncio.run(main())
```

### 非流式对话

```python
import asyncio
from app.core.agent_service import agent_service

async def main():
    # 非流式对话 - 等待完整响应
    messages = await agent_service.chat(
        prompt="What is 2 + 2?",
        session_id="my-session-002",
    )
    
    for msg in messages:
        print(f"[{msg.type}] {msg.content}")
    
    await agent_service.close_session("my-session-002")

asyncio.run(main())
```

### 多轮对话

```python
import asyncio
from app.core.agent_service import agent_service

async def main():
    session_id = "multi-turn-session"
    
    # 第一轮对话
    messages1 = await agent_service.chat(
        prompt="记住这个数字: 42",
        session_id=session_id,
    )
    print("Turn 1:", messages1[-1].content if messages1 else "")
    
    # 第二轮对话 - 使用相同的 session_id 继续
    messages2 = await agent_service.chat(
        prompt="我让你记住的数字是什么?",
        session_id=session_id,
    )
    print("Turn 2:", messages2[-1].content if messages2 else "")
    
    # 完成后关闭会话
    await agent_service.close_session(session_id)

asyncio.run(main())
```

## API 参考

### `chat_stream(prompt, session_id)`

流式对话方法。

**参数:**
- `prompt` (str): 用户提示/查询
- `session_id` (str): 唯一会话标识符

**返回:**
- `AsyncGenerator[ChatMessage, None]`: 异步生成器，逐条返回消息

**示例:**
```python
async for msg in agent_service.chat_stream("Hello", "session-001"):
    if msg.type == "text":
        print(msg.content)
```

### `chat(prompt, session_id)`

非流式对话方法。

**参数:**
- `prompt` (str): 用户提示/查询
- `session_id` (str): 唯一会话标识符

**返回:**
- `List[ChatMessage]`: 所有响应消息的列表

**示例:**
```python
messages = await agent_service.chat("Hello", "session-001")
for msg in messages:
    print(f"[{msg.type}] {msg.content}")
```

### `close_session(session_id)`

关闭指定会话。

**参数:**
- `session_id` (str): 要关闭的会话 ID

**返回:**
- `bool`: 是否成功关闭

**示例:**
```python
await agent_service.close_session("session-001")
```

### `cancel_task(session_id)`

取消正在进行的任务。

**参数:**
- `session_id` (str): 要取消的会话 ID

**返回:**
- `bool`: 是否成功发送取消请求

### `list_sessions()`

列出所有活跃会话。

**返回:**
- `List[Dict]`: 会话信息列表

**示例:**
```python
sessions = agent_service.list_sessions()
for s in sessions:
    print(f"Session: {s['session_id']}, Workspace: {s['workspace_path']}")
```

### `close_all_sessions()`

关闭所有会话。

**示例:**
```python
await agent_service.close_all_sessions()
```

## ChatMessage 结构

```python
@dataclass
class ChatMessage:
    type: str           # 消息类型: text, text_delta, tool_use, tool_result, system, result, error
    content: str        # 消息内容
    tool_name: str      # 工具名称 (仅 tool_use 类型)
    tool_input: dict    # 工具输入 (仅 tool_use 类型)
    metadata: dict      # 元数据
    timestamp: str      # 时间戳
```

### 消息类型说明

| 类型 | 说明 |
|------|------|
| `system` | 系统消息 |
| `text` | 完整文本响应 |
| `text_delta` | 流式文本片段 |
| `tool_use` | 工具调用 |
| `tool_result` | 工具执行结果 |
| `thinking` | 思考过程 |
| `result` | 最终结果 (包含 cost, duration 等元数据) |
| `error` | 错误信息 |
| `interrupted` | 任务被中断 |

## Workspace 规则

- 路径: `{user_home}/workspace/{session_id}`
- 示例: `/Users/john/workspace/my-session-001`
- 自动创建: 如果不存在会自动创建
- 配置复制: 自动从项目根目录复制 `.claude` 目录

## 会话管理

### 会话生命周期

1. **创建**: 首次调用 `chat_stream` 或 `chat` 时自动创建
2. **复用**: 使用相同 `session_id` 会复用现有会话
3. **关闭**: 调用 `close_session` 或 `close_all_sessions` 关闭

### 资源释放

建议在以下情况关闭会话:
- 用户明确结束对话
- 长时间无活动
- 应用退出前

```python
# 单个会话
await agent_service.close_session("session-001")

# 所有会话
await agent_service.close_all_sessions()
```

## 配置

环境变量从 `config.yaml` 的 `executor` 部分读取:

```yaml
executor:
  anthropic_api_key: "your-api-key"
  anthropic_base_url: "https://api.anthropic.com"
  anthropic_model: "claude-sonnet-4-20250514"
```

## 完整示例

```python
import asyncio
import uuid
from app.core.agent_service import agent_service

async def coding_assistant():
    """一个简单的编程助手示例"""
    session_id = f"coding-{uuid.uuid4().hex[:8]}"
    
    try:
        print("编程助手已启动，输入 'quit' 退出")
        
        while True:
            user_input = input("\n你: ").strip()
            if user_input.lower() == 'quit':
                break
            
            print("\n助手: ", end="", flush=True)
            async for msg in agent_service.chat_stream(
                prompt=user_input,
                session_id=session_id,
            ):
                if msg.type == "text_delta":
                    print(msg.content, end="", flush=True)
                elif msg.type == "result":
                    print(f"\n[完成: {msg.metadata.get('duration_ms', 0)}ms]")
            
    finally:
        await agent_service.close_session(session_id)
        print("\n会话已关闭")

if __name__ == "__main__":
    asyncio.run(coding_assistant())
```

