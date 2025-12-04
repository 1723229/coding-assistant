import logging
from typing import Optional

from app.core.claude_service import session_manager, MessageType

logger = logging.getLogger(__name__)


async def generate_code_from_spec(
        spec_content: str,
        workspace_path: str,
        session_id: str,
        module_name: str,
        module_code: str
) -> Optional[str]:
    """
    使用 Claude 根据规格文档生成代码并commit

    Args:
        spec_content: 规格文档路径
        workspace_path: 工作空间路径
        session_id: 会话ID
        module_name: 模块名称
        module_code: 模块代码

    Returns:
        commit_id，失败返回 None
    """
    try:
        logger.info(f"Generating code from spec for module: {module_code}")
        # 构建提示词
        prompt = f"""你是一位资深的全栈开发工程师。我已经为你准备了一份详细的技术规格文档，请根据这份文档和代码，生成完整的代码实现。

模块信息：
- 模块名称：{module_name}
- 模块代码：{module_code}

技术规格文档内容：
{spec_content}

请根据上述技术规格文档，完成以下任务：

1. **仔细阅读工作空间中的现有代码**：使用Read工具查看当前项目结构和代码
2. **分析技术栈**：了解项目使用的技术栈、框架和编码规范
3. **生成代码**：根据规格文档，使用Write和Edit工具生成或修改代码文件
4. **确保代码质量**：
- 遵循项目现有的代码风格和规范
- 添加必要的注释和文档
- 确保代码的可读性和可维护性
- 处理错误和边界情况
5. **完整实现**：确保所有规格文档中描述的功能都已实现

注意事项：
- 不要只是生成示例代码，而是要生成可以直接运行的前后端完整代码
- 使用项目现有的目录结构和命名规范
- 如果需要安装新的依赖，请更新相应的依赖配置文件
- 生成的代码应该与现有代码无缝集成

请开始实现代码，使用工具直接修改工作空间中的文件。"""

        # 获取沙箱服务实例
        sandbox_service = await session_manager.get_service(
            session_id=session_id,
            workspace_path=workspace_path,
        )

        # 调用沙箱服务生成代码（使用streaming）
        logger.info("Calling sandbox service to generate code from spec...")

        # 收集所有消息用于日志
        all_messages = []
        async for msg in sandbox_service.chat_stream(prompt=prompt, session_id=session_id):
            all_messages.append(msg)
            # 记录重要的消息类型
            if msg.type in [MessageType.TOOL_USE.value, MessageType.ERROR.value]:
                logger.info(f"Claude message: {msg.type} - {msg.content[:200]}")

        # 检查是否成功
        has_error = any(msg.type == MessageType.ERROR.value for msg in all_messages)
        if has_error:
            logger.error("Claude encountered errors during code generation")
            return None

        logger.info("Code generation completed, now committing changes...")

        # 使用 GitHubService 进行本地 commit
        try:

            # Commit message
            commit_message = f"[SpecCoding Auto Commit] - {module_name} ({module_code}) 功能实现"

            # 执行commit
            from git import Repo
            repo = Repo(workspace_path)

            # Add all changes
            repo.git.add(A=True)

            # Check if there are changes to commit
            if repo.is_dirty() or repo.untracked_files:
                # Commit
                commit = repo.index.commit(commit_message)
                commit_id = commit.hexsha[:12]  # 使用前12位

                logger.info(f"Code committed successfully: {commit_id}")
                return commit_id
            else:
                logger.warning("No changes to commit")
                return None

        except Exception as e:
            logger.error(f"Failed to commit code: {e}", exc_info=True)
            return None

    except Exception as e:
        logger.error(f"Failed to generate code from spec: {e}", exc_info=True)
        return None


class PromptBuild:
    def __init__(self):
        pass
