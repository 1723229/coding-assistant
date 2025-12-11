# Chat Stream Task Types 说明文档

## 概述

`AgentService.chat_stream()` 方法支持多种任务类型（task_type），用于处理不同的 PRD 相关操作。每种任务类型对应不同的 prompt 格式和处理逻辑。

## API 签名

```python
async def chat_stream(
    self,
    prompt: str,
    session_id: str,
    task_type: str
) -> AsyncGenerator[ChatMessage, None]
```

## 任务类型详解

### 1. `prd-decompose` - PRD 分解任务

**用途**: 将完整的 PRD 文档分解为功能树结构

**Prompt 格式**: PRD 文件的绝对路径

**示例**:
```python
prompt = "/Users/john/workspace/abc123/prd.md"
session_id = "abc123"
task_type = "prd-decompose"
```

**内部转换**:
```
原始: /Users/john/workspace/abc123/prd.md
```

**输出**:/{user_home}/workspace/{session_id}/docs/PRD-gen/目录下，生成 `FEATURE_TREE.md` 功能树文件、`METADATA.json` 功能树结构文件


---


### 2. `confirm-prd` - PRD 审阅确认

**用途**: 用户已确认PRD修改完成，进行确认

**重要**: 必须使用与原始 PRD 相同的 `session_id`，以保持上下文一致性

**Prompt 格式**: 无

**格式规范**:
```

```

**示例**:
```python
prompt = ''
session_id = "abc123"  # 必须与原始PRD的session_id一致
task_type = "confirm-prd"
```

**输出**: 更新后的 `FEATURE_TREE.md` 功能树文件、`METADATA.json` 功能树结构文件

---


### 3. `analyze-prd` - PRD 模块分析任务

**用途**: 分析 PRD 中的特定功能模块，生成详细的模块设计文档，每次的session_id唯一，避免功能模块冲突

**Prompt 格式**: 命令行参数字符串

**参数说明**:
| 参数 | 说明 | 必填 |
|------|------|------|
| `--module` | 要分析的模块名称 | 是 |
| `--feature-tree` | 功能树文件绝对路径 | 是 |
| `--prd` | 原始 PRD 文件绝对路径 | 是 |

**示例**:
```python
prompt = '--module "D1组建团队" --feature-tree "/Users/john/workspace/abc123/FEATURE_TREE.md" --prd "/Users/john/workspace/abc123/prd.md"'
session_id = "abc123"
task_type = "analyze-prd"
```

**内部转换**:
```
原始: --module "D1组建团队" --feature-tree "..." --prd "..."
```

**输出**: /{user_home}/workspace/{session_id}/docs/PRD-gen/目录下，,生成模块详细设计文档 clarification.md

---

### 4. `prd-change` - PRD 修改任务

**用途**: 根据用户反馈修改已有的 PRD 内容

**重要**: 必须使用与原始 PRD 相同的 `session_id`，以保持上下文一致性

**Prompt 格式**: 用户审查和修改请求

**格式规范**:
```
User Review on "选中的内容", msg: "提出的需求"
```

**示例**:
```python
prompt = 'User Review on "用户登录模块", msg: "增加OAuth2.0第三方登录支持"'
session_id = "abc123"  # 必须与原始PRD的session_id一致
task_type = "prd-change"
```

**内部转换**: 无转换，prompt 直接传递

**输出**: 更新后的 PRD 内容

---

### 5. 默认/其他 - 通用对话任务

**用途**: 一般性的对话交互，不涉及特定的 PRD 操作

**Prompt 格式**: 自由格式的用户查询

**示例**:
```python
prompt = "请帮我解释一下微服务架构的优缺点"
session_id = "xyz789"
task_type = "chat"  # 或任何非上述类型的值
```

**内部转换**: 无转换，prompt 直接传递

---

## 工作流示例

### 完整的 PRD 处理流程

```python
# Step 1: 分解 PRD
await service.chat_stream(
    prompt="/path/to/prd.md",
    session_id="session-001",
    task_type="prd-decompose"
)

# Step 2: 分析具体模块
await service.chat_stream(
    prompt='--module "用户认证" --feature-tree "/path/to/FEATURE_TREE.md" --prd "/path/to/prd.md"',
    session_id="session-xxx",
    task_type="analyze-prd"
)

# Step 3: 根据反馈修改
await service.chat_stream(
    prompt='User Review on "登录流程", msg: "需要支持手机验证码登录"',
    session_id="session-001",  # 保持session一致
    task_type="prd-change"
)
```

## 返回值

所有任务类型都返回 `AsyncGenerator[ChatMessage, None]`，ChatMessage 包含以下类型：

| type | 说明 |
|------|------|
| `text_delta` | 文本增量内容 |
| `tool_use` | 工具调用 |
| `tool_result` | 工具执行结果 |
| `error` | 错误信息 |
| `interrupted` | 任务被中断/取消 |

## 注意事项

1. **Session 管理**: `prd-change` 任务必须使用与原始 PRD 相同的 session_id
2. **路径格式**: 所有文件路径必须是绝对路径
3. **编码**: prompt 中的中文内容需要正确处理 UTF-8 编码
4. **取消机制**: 所有任务都支持通过 session 取消
