import logging
from typing import Optional, Tuple, Any, Coroutine

from app.core.sandbox_service import session_manager, MessageType
from app.core.openspec_reader import get_proposal_content_by_id
from asyncio import Queue

logger = logging.getLogger(__name__)


async def generate_code_from_spec(
        spec_content: str,
        workspace_path: str,
        session_id: str,
        module_name: str,
        module_code: str,
        module_url: str,
        task_type: str,
        message_queue: Queue
) -> tuple[str | None, list[Any], list[Any], Any] | tuple[str | None, list[Any], list[Any], None] | tuple[
    str | None, list[Any], list[Any], str]:
    """
    使用 Claude 根据规格文档生成代码并commit

    Args:
        spec_content: 规格文档路径
        workspace_path: 工作空间路径
        session_id: 会话ID
        module_name: 模块名称
        module_code: 模块代码

    Returns:
        Tuple[commit_id, proposal_content]，失败返回 (None, None)
    """
    spec_id = None
    proposal_content = None
    
    try:
        logger.info(f"Generating code from spec for module: {module_code}")
        # 构建提示词

        if task_type == "spec":
            prompt = f"<Module Info>\n name: {module_name}，english name: {module_code},Module URL:{module_url}\n <User's Proposal>\n  {spec_content} \n - 强调：不允许反问用户，不需要澄清，不允许让用户确认，直接开始执行"
        elif task_type == "preview":
            prompt= f"<User's review>\n {spec_content} \n - 强调：不允许反问用户，不需要澄清，不允许让用户确认，直接开始执行"
        else:
            prompt = spec_content

        logger.info(f"Generating code from spec for task: {task_type} \n prompt : {prompt}")

        # 获取沙箱服务实例
        sandbox_service = await session_manager.get_service(
            session_id=session_id,
            workspace_path=workspace_path,
        )

        # 调用沙箱服务生成代码（使用streaming）
        logger.info("Calling sandbox service to generate code from spec...")

        # 收集所有消息用于日志
        all_messages = []
        to_data = []
        result = []
        async for msg in sandbox_service.chat_stream(prompt=prompt, session_id=session_id, task_type=task_type):
            all_messages.append(msg)
            if msg.type == MessageType.TEXT or msg.type == MessageType.TEXT_DELTA:
                to_data.append(msg.content)
                await message_queue.put(msg)
            if msg.type == MessageType.RESULT:
                result.append(msg.content)
                await message_queue.put(msg)
            # 记录重要的消息类型
            if msg.type in [MessageType.TOOL_USE.value, MessageType.ERROR.value]:
                logger.info(f"Claude message: {msg.type} - {msg.content[:200]}")
            
            # 捕获 spec_id 消息，提取 spec_id 并读取 proposal.md
            # 注意: executor 内部使用 "_spec_id"，但对外暴露的是 "spec_id" (无下划线)
            if msg.type == "spec_id" and msg.content:
                spec_id = msg.content
                logger.info(f"Extracted spec_id: {spec_id}, reading proposal.md...")
                proposal_content = get_proposal_content_by_id(
                    workspace_path=workspace_path,
                    spec_id=spec_id
                )
                if proposal_content:
                    logger.info(f"Successfully read proposal.md for spec_id: {spec_id}, length: {len(proposal_content)}")
                else:
                    logger.warning(f"Failed to read proposal.md for spec_id: {spec_id}")
        await message_queue.put(None)

        # 检查是否成功
        has_error = any(msg.type == MessageType.ERROR.value for msg in all_messages)
        if has_error:
            logger.error("Claude encountered errors during code generation")
            return proposal_content, to_data, result, msg.content

        logger.info("Code generation completed, now committing changes...")
        return proposal_content, to_data, result, None

    except Exception as e:
        logger.error(f"Failed to generate code from spec: {e}", exc_info=True)
        return proposal_content, [], [], f"Failed to generate code from spec: {e}"


class PromptBuild:
    def __init__(self):
        pass
