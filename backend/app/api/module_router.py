"""
Module API Router

模块管理相关的API路由定义
支持 NODE 和 POINT 类型，POINT 类型管理 workspace 和容器
"""

import os
import uuid
import json
import asyncio
import logging
from pathlib import Path as FilePath
from fastapi import APIRouter, Query, Path, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from app.service.module_service import ModuleService
from app.db.schemas import ModuleCreate, ModuleUpdate
from app.utils import BaseResponse

logger = logging.getLogger(__name__)

# 创建路由器
module_router = APIRouter(prefix="/modules", tags=["modules"])

# 创建service实例
module_service = ModuleService()


@module_router.get(
    "/project/{project_id}",
    summary="获取项目的模块列表",
    operation_id="list_modules"
)
async def list_modules(
    project_id: int = Path(..., description="Project ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records"),
):
    """获取项目的模块列表（平铺结构）"""
    return await module_service.list_modules(project_id=project_id, skip=skip, limit=limit)


@module_router.get(
    "/project/{project_id}/tree",
    summary="获取项目的模块树",
    operation_id="get_module_tree"
)
async def get_module_tree(
    project_id: int = Path(..., description="Project ID")
):
    """获取项目的模块树形结构"""
    return await module_service.get_module_tree(project_id=project_id)


@module_router.post(
    "",
    summary="创建新模块",
    operation_id="create_module"
)
async def create_module(data: ModuleCreate):
    """
    创建新模块

    - NODE 类型：只创建记录，URL 与子节点共享
    - POINT 类型：创建 session，拉取代码到 workspace
    """
    return await module_service.create_module(data)


@module_router.post(
    "/stream",
    summary="创建新模块（流式）",
    operation_id="create_module_stream"
)
async def create_module_stream(data: ModuleCreate):
    """
    创建新模块（SSE流式）

    实时返回创建进度，用于POINT类型模块的长时间操作

    事件类型：
    - connected: 连接建立
    - step: 步骤进度更新
    - error: 错误信息
    - complete: 创建完成
    """
    return StreamingResponse(
        module_service.create_module_stream(data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@module_router.post(
    "/optimize/{session_id}/stream",
    summary="优化模块代码（流式）",
    operation_id="optimize_module_stream"
)
async def optimize_module_stream(
    session_id: str = Path(..., description="Session ID"),
    optimization_request: dict = None
):
    """
    优化已创建的POINT类型模块（SSE流式）

    根据用户新的需求对现有代码进行优化，实时返回优化进度

    请求体:
    {
        "content": "优化需求描述",
        "updated_by": "用户标识"
    }

    事件类型：
    - connected: 连接建立
    - step: 步骤进度更新
    - error: 错误信息
    - complete: 优化完成
    """
    content = optimization_request.get("content") if optimization_request else ""
    updated_by = optimization_request.get("updated_by") if optimization_request else None

    return StreamingResponse(
        module_service.optimize_module_stream(session_id, content, updated_by),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@module_router.post(
    "/build/{session_id}/stream",
    summary="优化模块代码（流式）",
    operation_id="build_module_stream"
)
async def build_module_stream(
    session_id: str = Path(..., description="Session ID"),
    optimization_request: dict = None
):
    """
    优化已创建的POINT类型模块（SSE流式）

    事件类型：
    - connected: 连接建立
    - step: 步骤进度更新
    - error: 错误信息
    - complete: 优化完成
    """
    content = optimization_request.get("content") if optimization_request else ""
    updated_by = optimization_request.get("updated_by") if optimization_request else None
    return StreamingResponse(
        module_service.build_module_stream(session_id, content, updated_by),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@module_router.get(
    "/{module_id}",
    summary="获取模块详情",
    operation_id="get_module"
)
async def get_module(
    module_id: int = Path(..., description="Module ID")
):
    """根据ID获取模块详情"""
    return await module_service.get_module(module_id)


@module_router.get(
    "/session/{session_id}",
    summary="根据Session ID获取模块",
    operation_id="get_module_by_session_id"
)
async def get_module_by_session_id(
    session_id: str = Path(..., description="Session ID")
):
    """根据 session_id 获取 POINT 类型模块详情"""
    return await module_service.get_module_by_session_id(session_id)


@module_router.put(
    "/{module_id}",
    summary="更新模块",
    operation_id="update_module"
)
async def update_module(
    module_id: int = Path(..., description="Module ID"),
    data: ModuleUpdate = None,
):
    """更新模块信息"""
    return await module_service.update_module(module_id, data)


@module_router.delete(
    "/{module_id}",
    summary="删除模块",
    operation_id="delete_module"
)
async def delete_module(
    module_id: int = Path(..., description="Module ID")
):
    """
    删除模块（级联删除子模块）

    POINT 类型会清理 workspace 和容器
    """
    return await module_service.delete_module(module_id)


@module_router.post(
    "/{module_id}/pull",
    summary="拉取模块代码",
    operation_id="pull_module_code"
)
async def pull_module_code(
    module_id: int = Path(..., description="Module ID")
):
    """
    拉取 POINT 类型模块的最新代码

    从 Git 仓库拉取最新代码到 workspace
    """
    return await module_service.pull_module_code(module_id)


@module_router.post(
    "/{module_id}/container/restart",
    summary="重启模块容器",
    operation_id="restart_module_container"
)
async def restart_module_container(
    module_id: int = Path(..., description="Module ID")
):
    """
    重启 POINT 类型模块的 Docker 容器

    用于解决容器故障或应用环境配置变更后的重启需求
    """
    return await module_service.restart_module_container(module_id)


@module_router.post(
    "/upload/stream",
    summary="上传文件并流式处理（创建模块）",
    operation_id="upload_file_stream"
)
async def upload_file_stream(
    file: UploadFile = File(..., description="上传的文件（支持 .docx, .md）"),
    session_id: str = Query(..., description="会话ID"),
):
    """
    上传文件并流式处理PRD分解任务

    支持的文件格式：
    - .docx: Word文档，自动转换为Markdown
    - .md: Markdown文件
    - .txt: 纯文本文件

    流程：
    1. 接收文件上传
    2. 根据文件类型转换为Markdown
    3. 保存到 workspace/{session_id}/prd.md
    4. 调用 chat_stream 进行 prd-decompose 任务
    5. 读取生成的 FEATURE_TREE.md 和 METADATA.json
    6. 返回给前端

    事件类型：
    - connected: 连接建立
    - step: 步骤进度更新
    - error: 错误信息
    - complete: 处理完成，包含 feature_tree 和 metadata
    """
    return StreamingResponse(
        module_service.upload_file_and_create_module_stream(
            file=file,
            session_id=session_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@module_router.post(
    "/prd/change/stream",
    summary="PRD修改任务（流式）",
    operation_id="prd_change_stream"
)
async def prd_change_stream(
    session_id: str = Query(..., description="会话ID（必须与原始PRD相同）"),
    selected_content: str = Query(..., description="选中的内容"),
    msg: str = Query(..., description="提出的需求"),
):
    """
    PRD修改任务（流式）

    根据用户反馈修改已有的 PRD 内容

    **重要**: 必须使用与原始 PRD 相同的 session_id

    Prompt 格式: User Review on "{selected_content}", msg: "{msg}"

    流程：
    1. 验证 session_id 对应的目录和文件是否存在
    2. 构建 prompt
    3. 调用 chat_stream 进行 prd-change 任务
    4. 读取更新后的 FEATURE_TREE.md 和 METADATA.json
    5. 返回给前端

    事件类型：
    - connected: 连接建立
    - step: 步骤进度更新
    - error: 错误信息（包括 session_id 错误或文件缺失）
    - complete: 处理完成，包含更新后的 feature_tree 和 metadata

    示例:
    - session_id: "abc123"
    - selected_content: "用户登录模块"
    - msg: "增加OAuth2.0第三方登录支持"
    """
    return StreamingResponse(
        module_service.prd_change_stream(
            session_id=session_id,
            selected_content=selected_content,
            msg=msg,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@module_router.post(
    "/prd/confirm/stream",
    summary="PRD审阅确认任务（流式）",
    operation_id="confirm_prd_stream"
)
async def confirm_prd_stream(
    session_id: str = Query(..., description="会话ID（必须与原始PRD相同）"),
):
    """
    PRD审阅确认任务（流式）

    用户已确认PRD修改完成，进行确认

    **重要**: 必须使用与原始 PRD 相同的 session_id

    **Prompt**: 无需传递内容，prompt 为空字符串

    流程：
    1. 验证 session_id 对应的目录和文件是否存在
    2. 调用 chat_stream 进行 confirm-prd 任务
    3. 读取更新后的 FEATURE_TREE.md 和 METADATA.json
    4. 返回给前端

    事件类型：
    - connected: 连接建立
    - step: 步骤进度更新
    - error: 错误信息（包括 session_id 错误或文件缺失）
    - complete: 处理完成，包含更新后的 feature_tree 和 metadata

    示例:
    - session_id: "abc123"
    """
    return StreamingResponse(
        module_service.confirm_prd_stream(
            session_id=session_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@module_router.post(
    "/create/from-metadata",
    summary="从METADATA.json批量创建项目和模块",
    operation_id="create_modules_from_metadata"
)
async def create_modules_from_metadata(
    session_id: str = Query(..., description="会话ID"),
):
    """
    从 METADATA.json 批量创建 project 和 modules

    流程：
    1. 读取 {workspace}/{session_id}/docs/PRD-GEN/METADATA.json
    2. 根据 system_info.name_zh 创建 project（codebase_url 和 token 暂不填写）
    3. 根据 features 递归创建 modules:
       - is_leaf: true  -> POINT 类型
       - is_leaf: false -> NODE 类型
    4. 插入 sys_module 表（用于 UI 菜单）

    **注意**:
    - 只做入库操作，不拉取代码、不创建容器
    - 如果 project 或 module 已存在，则跳过创建
    - 使用普通 HTTP 接口，非 SSE 流

    返回:
    - project_id: 创建的项目ID
    - project_name: 项目名称
    - module_count: 创建的模块数量
    - modules: 创建的模块列表

    示例:
    - session_id: "abc123"
    """
    data =  await module_service.create_modules_from_metadata(session_id=session_id)
    return BaseResponse.success(
        data=data,
        message=f"成功创建项目和 {data.get("module_count")} 个模块"
    )


@module_router.post(
    "/analyze-prd/stream",
    summary="PRD模块分析任务（流式）",
    operation_id="analyze_prd_module_stream"
)
async def analyze_prd_module_stream(
    session_id: str = Query(..., description="模块的session_id（每次唯一）"),
    module_name: str = Query(..., description="要分析的模块名称"),
    prd_session_id: str = Query(..., description="PRD的session_id"),
):
    """
    PRD模块分析任务（流式）

    分析 PRD 中的特定功能模块，生成详细的模块设计文档

    **重要**:
    - session_id: 模块自己的 session_id（每次唯一，避免冲突）
    - prd_session_id: PRD 的 session_id（用于定位 FEATURE_TREE.md 和 prd.md）

    **Prompt 格式**: --module "{module_name}" --feature-tree "..." --prd "..."

    流程：
    1. 验证模块的 session_id 和 workspace
    2. 验证 PRD 的 FEATURE_TREE.md 和 prd.md
    3. 构建 prompt
    4. 调用 chat_stream 进行 analyze-prd 任务
    5. 读取生成的 clarification.md
    6. 保存到 module.require_content
    7. 返回给前端

    事件类型：
    - connected: 连接建立
    - step: 步骤进度更新
    - error: 错误信息
    - complete: 处理完成，包含 clarification_content

    示例:
    - session_id: "module-uuid-123"
    - module_name: "D1组建团队"
    - prd_session_id: "prd-uuid-456"
    """
    return StreamingResponse(
        module_service.analyze_prd_module_stream(
            session_id=session_id,
            module_name=module_name,
            prd_session_id=prd_session_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@module_router.post(
    "/prepare-and-generate-spec/stream",
    summary="准备环境并生成Spec（流式）",
    operation_id="prepare_and_generate_spec_stream"
)
async def prepare_and_generate_spec_stream(
    session_id: str = Query(..., description="模块的session_id"),
    content: str = Query(None, description="需求内容")
):
    """
    准备环境并生成 Spec（流式）

    智能检查并准备所有必要的环境，然后生成技术规格文档

    **流程**:
    1. 验证 project 配置（Git地址和Token）
    2. 检查工作空间代码
       - 无代码：拉取代码 → 创建分支
       - 有代码：跳过
    3. 检查容器状态
       - 无容器：检查容器阈值 → 创建容器
       - 有容器：跳过
    4. 创建/更新 Version 记录
    5. 生成 Spec 文档
    6. 更新 Version 状态为 SPEC_GENERATED

    **事件类型**:
    - connected: 连接建立
    - step: 步骤进度更新
    - error: 错误信息
    - complete: 处理完成，包含 spec_content 和 version_id

    **使用场景**:
    - 模块创建后首次生成 Spec
    - 重新生成 Spec（容器可能已清理）
    - 环境异常后恢复生成

    示例:
    - session_id: "module-uuid-123"
    - content: ""
    """
    return StreamingResponse(
        module_service.prepare_and_generate_spec_stream(
            session_id=session_id,
            content=content
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
