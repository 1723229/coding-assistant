# -*- coding: utf-8 -*-
"""
Simple test to verify Write tool works correctly.
"""

import asyncio
import logging
import os
import sys

# Set environment variables BEFORE importing SDK
os.environ["ANTHROPIC_API_KEY"] = "sk-IW3k4qZmyo9HiM1eh7w4BWpIbq1hgu9Oe9lARJxfgyF7IvYL"
os.environ["CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS"] = "1"

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.agent_service import agent_service, DEFAULT_WORKSPACE_ROOT
import uuid

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,  # Enable DEBUG for detailed output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_simple_write():
    """Test simple Write tool with short content"""
    
    session_id = f"write-test-{uuid.uuid4().hex[:8]}"
    
    # Simple prompt that should trigger a Write tool call
    prompt = "Create a file at docs/test-output.md with content '# Hello World\\n\\nThis is a test file.'"
    
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Workspace: {DEFAULT_WORKSPACE_ROOT}/{session_id}")
    logger.info(f"Prompt: {prompt}")
    
    try:
        async for msg in agent_service.chat_stream(
            prompt=prompt,
            session_id=session_id,
        ):
            logger.info(f"[{msg.type}] {msg.content[:200] if msg.content else ''}")
            if msg.type == "tool_use":
                logger.info(f"  tool_name: {msg.tool_name}")
                logger.info(f"  tool_input: {msg.tool_input}")
            if msg.type == "result":
                logger.info(f"  metadata: {msg.metadata}")
                break
    
    except Exception as e:
        logger.exception(f"Test failed: {e}")
    
    finally:
        await agent_service.close_session(session_id)
        logger.info(f"Session closed: {session_id}")


async def main():
    """Run the test."""
    await test_simple_write()
    await agent_service.close_all_sessions()


if __name__ == "__main__":
    asyncio.run(main())

