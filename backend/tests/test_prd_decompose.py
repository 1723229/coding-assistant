# -*- coding: utf-8 -*-
"""
Test script for PRD decompose command.

Usage:
    cd backend
    python tests/test_prd_decompose.py
"""

import asyncio
import logging
import os
import sys
import uuid

os.environ["ANTHROPIC_API_KEY"] = "sk-TJEkNlNoEZHOElwi7u1j2XTE9opsSXbbaqPCRufNPiGDc4VL"
os.environ["CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS"] = "1"

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_prd_decompose():
    """Test PRD decompose command with absolute file path"""
    from app.core.agent_service import agent_service, DEFAULT_WORKSPACE_ROOT

    session_id = f"prd-test-{uuid.uuid4().hex[:8]}"
    
    # Absolute file path
    file_path = "/Users/spuerman/work/github_code/coding-assistant/backend/docs/prd-decompse-test-prd.md"
    
    logger.info("=" * 60)
    logger.info("PRD Decompose Test")
    logger.info("=" * 60)
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Workspace: {DEFAULT_WORKSPACE_ROOT}/{session_id}")
    logger.info(f"File path: {file_path}")
    
    # Check file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    # Prompt for PRD decompose with absolute path
    prompt = f"/prd-decompose {file_path}"
    
    logger.info("=" * 60)
    logger.info(f"Executing:cla {prompt}")
    logger.info("=" * 60)
    
    try:
        message_count = 0
        text_buffer = []
        
        async for msg in agent_service.chat_stream(
            prompt=prompt,
            session_id=session_id,
        ):
            print(f"msg:------{msg}")
            message_count += 1
            
            # Output based on message type
            if msg.type == "system":
                logger.info(f"[SYSTEM] {msg.content if msg.content else ''}...")
            elif msg.type == "text_delta":
                print(msg.content, end="", flush=True)
                text_buffer.append(msg.content)
            elif msg.type == "text":
                if msg.content and msg.content not in ''.join(text_buffer):
                    print(msg.content, end="", flush=True)
            elif msg.type == "tool_use":
                logger.info(f"\n[TOOL] {msg.tool_name}: {str(msg.tool_input) if msg.tool_input else ''}...")
            elif msg.type == "tool_result":
                logger.info(f"[TOOL_RESULT] {msg if msg.content else ''}...")
            elif msg.type == "thinking":
                logger.info(f"[THINKING] {msg if msg.content else ''}...")
            elif msg.type == "result":
                print()
                logger.info(f"[RESULT] Duration: {msg.metadata.get('duration_ms', 0)}ms, "
                           f"Cost: ${msg.metadata.get('total_cost_usd', 0):.4f}, "
                           f"Turns: {msg.metadata.get('num_turns', 0)}, "
                           f"Error: {msg.metadata.get('is_error', False)}")
            elif msg.type == "error":
                logger.error(f"[ERROR] {msg.content}")
                break
        
        logger.info("=" * 60)
        logger.info(f"Total messages: {message_count}")
        logger.info("=" * 60)
        
        return message_count > 0
        
    except Exception as e:
        logger.exception(f"Test failed: {e}")
        return False
    
    finally:
        await agent_service.close_session(session_id)
        logger.info(f"Session closed: {session_id}")


async def main():
    """Run the test."""
    success = await test_prd_decompose()
    
    logger.info("=" * 60)
    logger.info(f"Test result: {'PASS' if success else 'FAIL'}")
    logger.info("=" * 60)
    
    from app.core.agent_service import agent_service
    await agent_service.close_all_sessions()
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
