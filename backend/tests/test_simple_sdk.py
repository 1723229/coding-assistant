# -*- coding: utf-8 -*-
"""
Simple SDK test to verify basic functionality.
"""

import asyncio
import logging
import os
import sys

# Set environment variables BEFORE importing SDK
os.environ["ANTHROPIC_API_KEY"] = "sk-IW3k4qZmyo9HiM1eh7w4BWpIbq1hgu9Oe9lARJxfgyF7IvYL"
os.environ["CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS"] = "1"

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    TextBlock,
)

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_simple_query():
    """Test simple query without custom workspace"""
    
    # Use project directory as workspace
    workspace = "/Users/spuerman/work/github_code/coding-assistant"
    
    logger.info(f"Workspace: {workspace}")
    logger.info(f"API Key: {os.environ.get('ANTHROPIC_API_KEY', '')[:20]}...")
    
    # Change to workspace directory
    os.chdir(workspace)
    logger.info(f"Changed to: {os.getcwd()}")
    
    options = ClaudeAgentOptions(
        cwd=workspace,
        permission_mode="bypassPermissions",
        include_partial_messages=True,
        setting_sources=["project", "local", "user"],
    )
    
    logger.info("Creating client...")
    client = ClaudeSDKClient(options=options)
    
    logger.info("Connecting...")
    await client.connect()
    logger.info("Connected!")
    
    # Simple test prompt
    prompt = "/prd-decompose /Users/spuerman/work/github_code/coding-assistant/backend/docs/prd-decompse-test-prd.md"
    
    logger.info(f"Sending query: {prompt}")
    await client.query(prompt)
    
    logger.info("Receiving response...")
    message_count = 0
    async for msg in client.receive_response():
        message_count += 1
        
        if isinstance(msg, SystemMessage):
            logger.info(f"[SYSTEM] subtype={msg.subtype}")
        elif isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    print(block.text, end="", flush=True)
        elif isinstance(msg, ResultMessage):
            print()
            logger.info(f"[RESULT] duration={msg.duration_ms}ms, turns={msg.num_turns}, error={msg.is_error}")
            logger.info(f"[RESULT] cost=${msg.total_cost_usd:.4f}")
        else:
            logger.debug(f"[MSG] type={type(msg).__name__}")
    
    logger.info(f"Total messages: {message_count}")
    
    await client.disconnect()
    logger.info("Disconnected")


if __name__ == "__main__":
    asyncio.run(test_simple_query())


