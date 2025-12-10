# -*- coding: utf-8 -*-
"""
Simple test script for AgentService.

Tests basic streaming functionality and multi-turn conversation.

Usage:
    cd backend
    python tests/test_agent_simple.py
"""

import asyncio
import logging
import os
import sys
import uuid

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_simple_chat():
    """Test simple streaming chat."""
    from app.core.agent_service import agent_service, DEFAULT_WORKSPACE_ROOT

    session_id = f"test-simple-{uuid.uuid4().hex[:8]}"
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Workspace root: {DEFAULT_WORKSPACE_ROOT}")
    logger.info(f"Expected workspace: {os.path.join(DEFAULT_WORKSPACE_ROOT, session_id)}")

    # Simple prompt
    prompt = "What is 2 + 2? Just answer with the number, nothing else."

    try:
        message_count = 0
        text_content = []

        logger.info("Starting chat stream...")
        async for msg in agent_service.chat_stream(
                prompt=prompt,
                session_id=session_id,
        ):
            message_count += 1
            content_preview = msg.content[:100] if msg.content else ""
            logger.info(f"[{msg.type}] {content_preview}")

            if msg.type in ("text", "text_delta"):
                text_content.append(msg.content)

            if msg.type == "error":
                logger.error(f"Error: {msg.content}")
                break

            if msg.type == "result":
                logger.info(f"Result metadata: {msg.metadata}")
                break

        logger.info(f"Total messages: {message_count}")
        logger.info(f"Full text: {''.join(text_content)}")

        # Check workspace was created
        workspace_path = os.path.join(DEFAULT_WORKSPACE_ROOT, session_id)
        if os.path.exists(workspace_path):
            logger.info(f"Workspace created: {workspace_path}")
            # Check if .claude was copied
            claude_dir = os.path.join(workspace_path, ".claude")
            if os.path.exists(claude_dir):
                logger.info(f".claude directory copied successfully")
            else:
                logger.warning(f".claude directory not found in workspace")
        else:
            logger.warning(f"Workspace not found: {workspace_path}")

        return message_count > 0 and len(text_content) > 0

    except Exception as e:
        logger.exception(f"Test failed: {e}")
        return False

    finally:
        await agent_service.close_session(session_id)
        logger.info(f"Session closed")


async def test_multi_turn_conversation():
    """Test multi-turn conversation with same session_id."""
    from app.core.agent_service import agent_service, DEFAULT_WORKSPACE_ROOT

    session_id = f"test-multi-{uuid.uuid4().hex[:8]}"
    logger.info(f"\n{'='*60}")
    logger.info(f"TEST: Multi-Turn Conversation")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"{'='*60}")

    try:
        # Turn 1
        logger.info("\n--- Turn 1: Ask a question ---")
        messages1 = await agent_service.chat(
            prompt="Remember this number: 42. Just say 'OK, I remember 42'",
            session_id=session_id,
        )
        logger.info(f"Turn 1 messages: {len(messages1)}")
        for msg in messages1:
            if msg.type in ("text", "result"):
                logger.info(f"  [{msg.type}] {msg.content[:100] if msg.content else ''}")

        # Turn 2 - Continue with same session_id
        logger.info("\n--- Turn 2: Reference previous context ---")
        messages2 = await agent_service.chat(
            prompt="What number did I ask you to remember?",
            session_id=session_id,
        )
        logger.info(f"Turn 2 messages: {len(messages2)}")
        for msg in messages2:
            if msg.type in ("text", "result"):
                logger.info(f"  [{msg.type}] {msg.content[:100] if msg.content else ''}")

        # Check if session is still active
        sessions = agent_service.list_sessions()
        session_active = any(s['session_id'] == session_id for s in sessions)
        logger.info(f"Session still active after multi-turn: {session_active}")

        return len(messages1) > 0 and len(messages2) > 0

    except Exception as e:
        logger.exception(f"Test failed: {e}")
        return False

    finally:
        await agent_service.close_session(session_id)
        logger.info(f"Session closed")


async def main():
    """Run the simple test."""
    logger.info("=" * 60)
    logger.info("AgentService Test Suite")
    logger.info("=" * 60)

    results = {}

    # Test 1: Simple chat
    logger.info("\n" + "=" * 60)
    logger.info("TEST 1: Simple Streaming Chat")
    logger.info("=" * 60)
    results["simple_chat"] = await test_simple_chat()

    # Test 2: Multi-turn conversation
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Multi-Turn Conversation")
    logger.info("=" * 60)
    results["multi_turn"] = await test_multi_turn_conversation()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        logger.info(f"  {test_name}: {status}")

    passed = sum(1 for r in results.values() if r)
    failed = len(results) - passed
    logger.info(f"\nTotal: {passed} passed, {failed} failed")
    logger.info("=" * 60)

    # Cleanup
    from app.core.agent_service import agent_service
    await agent_service.close_all_sessions()

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
