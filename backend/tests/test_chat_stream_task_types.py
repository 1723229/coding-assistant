# -*- coding: utf-8 -*-
"""
Test cases for chat_stream task types.

Based on: backend/docs/chat_stream_task_types.md

This test file covers:
1. prd-decompose - PRD decomposition task
2. analyze-prd - PRD module analysis task
3. prd-change - PRD modification task
4. chat (default) - General chat task

Usage:
    cd backend
    
    # Run all tests
    python tests/test_chat_stream_task_types.py
    
    # Run specific test
    python tests/test_chat_stream_task_types.py --test prd-decompose
    python tests/test_chat_stream_task_types.py --test analyze-prd
    python tests/test_chat_stream_task_types.py --test prd-change
    python tests/test_chat_stream_task_types.py --test chat
    python tests/test_chat_stream_task_types.py --test workflow
"""

import asyncio
import argparse
import logging
import os
import sys
import uuid
from typing import List, Optional

# Set environment variables BEFORE importing SDK
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

# Test configuration
PRD_FILE_PATH = "/Users/spuerman/work/github_code/coding-assistant/backend/docs/prd-decompse-test-prd.md"
DEFAULT_WORKSPACE_ROOT = os.path.expanduser("~/workspace")


class ChatMessage:
    """Chat message wrapper for test output"""
    def __init__(self, msg):
        self.type = msg.type
        self.content = msg.content
        self.tool_name = msg.tool_name
        self.tool_input = msg.tool_input
        self.metadata = msg.metadata


async def stream_and_collect(
    prompt: str,
    session_id: str,
    task_type: str,
    max_messages: int = 1000,
    timeout: int = 600
) -> tuple[List, bool, Optional[str]]:
    """
    Stream chat and collect messages.
    
    Returns:
        Tuple of (messages, success, error_message)
    """
    from app.core.agent_service import agent_service
    
    messages = []
    text_buffer = []
    success = True
    error_message = None
    
    try:
        message_count = 0
        async for msg in agent_service.chat_stream(
            prompt=prompt,
            session_id=session_id,
            task_type=task_type,
        ):
            message_count += 1
            messages.append(msg)
            
            # Output based on message type
            if msg.type == "system":
                logger.info(f"[SYSTEM] {str(msg.content)[:200] if msg.content else ''}...")
            elif msg.type == "text_delta":
                print(msg.content, end="", flush=True)
                text_buffer.append(msg.content)
            elif msg.type == "text":
                if msg.content and msg.content not in ''.join(text_buffer):
                    print(msg.content, end="", flush=True)
            elif msg.type == "tool_use":
                logger.info(f"\n[TOOL] {msg.tool_name}: {str(msg.tool_input)[:200] if msg.tool_input else ''}...")
            elif msg.type == "tool_result":
                is_error = msg.metadata.get('is_error', False) if msg.metadata else False
                if is_error:
                    logger.warning(f"[TOOL_RESULT ERROR] {str(msg.content)[:300] if msg.content else ''}...")
                else:
                    logger.info(f"[TOOL_RESULT] {str(msg.content)[:200] if msg.content else ''}...")
            elif msg.type == "thinking":
                logger.info(f"[THINKING] {str(msg.content)[:100] if msg.content else ''}...")
            elif msg.type == "result":
                print()
                is_error = msg.metadata.get('is_error', False) if msg.metadata else False
                logger.info(f"[RESULT] Duration: {msg.metadata.get('duration_ms', 0)}ms, "
                           f"Cost: ${msg.metadata.get('total_cost_usd', 0):.4f}, "
                           f"Turns: {msg.metadata.get('num_turns', 0)}, "
                           f"Error: {is_error}")
                if is_error:
                    success = False
                    error_message = msg.content
            elif msg.type == "error":
                logger.error(f"[ERROR] {msg.content}")
                success = False
                error_message = msg.content
                break
            
            if message_count >= max_messages:
                logger.warning(f"Reached max messages limit: {max_messages}")
                break
                
    except asyncio.TimeoutError:
        logger.error(f"Timeout after {timeout}s")
        success = False
        error_message = "Timeout"
    except Exception as e:
        logger.exception(f"Error: {e}")
        success = False
        error_message = str(e)
    
    return messages, success, error_message


# =============================================================================
# Test 1: prd-decompose - PRD Decomposition Task
# =============================================================================
async def test_prd_decompose():
    """
    Test PRD decomposition task.
    
    Task Type: prd-decompose
    Prompt Format: PRD file absolute path
    Expected Output: FEATURE_TREE.md, METADATA.json in docs/PRD-Gen/
    """
    from app.core.agent_service import agent_service
    
    session_id = f"test-decompose-{uuid.uuid4().hex[:8]}"
    workspace_path = os.path.join(DEFAULT_WORKSPACE_ROOT, session_id)
    
    logger.info("=" * 60)
    logger.info("Test 1: prd-decompose - PRD Decomposition Task")
    logger.info("=" * 60)
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Workspace: {workspace_path}")
    logger.info(f"PRD File: {PRD_FILE_PATH}")
    logger.info(f"Task Type: prd-decompose")
    logger.info("=" * 60)
    
    # Check PRD file exists
    if not os.path.exists(PRD_FILE_PATH):
        logger.error(f"PRD file not found: {PRD_FILE_PATH}")
        return False
    
    # Prompt is just the file path (task_type handles the conversion)
    prompt = PRD_FILE_PATH
    
    logger.info(f"Prompt: {prompt}")
    logger.info(f"Internal conversion: /prd-decompose {prompt}")
    logger.info("=" * 60)
    
    try:
        messages, success, error = await stream_and_collect(
            prompt=prompt,
            session_id=session_id,
            task_type="prd-decompose",
        )
        
        logger.info("=" * 60)
        logger.info(f"Total messages: {len(messages)}")
        
        # Check expected outputs
        feature_tree_path = os.path.join(workspace_path, "docs", "PRD-Gen", "FEATURE_TREE.md")
        metadata_path = os.path.join(workspace_path, "docs", "PRD-Gen", "METADATA.json")
        
        if os.path.exists(feature_tree_path):
            logger.info(f"✓ FEATURE_TREE.md created: {feature_tree_path}")
        else:
            logger.warning(f"✗ FEATURE_TREE.md not found: {feature_tree_path}")
            
        if os.path.exists(metadata_path):
            logger.info(f"✓ METADATA.json created: {metadata_path}")
        else:
            logger.warning(f"✗ METADATA.json not found: {metadata_path}")
        
        logger.info("=" * 60)
        return success
        
    finally:
        await agent_service.close_session(session_id)
        logger.info(f"Session closed: {session_id}")


# =============================================================================
# Test 2: analyze-prd - PRD Module Analysis Task
# =============================================================================
async def test_analyze_prd():
    """
    Test PRD module analysis task.
    
    Task Type: analyze-prd
    Prompt Format: --module "模块名" --feature-tree "路径" --prd "路径"
    Expected Output: clarification.md in docs/PRD-Gen/
    
    Note: This test requires an existing FEATURE_TREE.md from prd-decompose
    """
    from app.core.agent_service import agent_service
    
    # Use a unique session_id for analyze-prd (as per docs)
    session_id = f"test-analyze-{uuid.uuid4().hex[:8]}"
    workspace_path = os.path.join(DEFAULT_WORKSPACE_ROOT, session_id)
    
    # For this test, we'll use a pre-existing feature tree path
    # In real workflow, this would come from a previous prd-decompose session
    feature_tree_path = "/Users/spuerman/work/github_code/coding-assistant/backend/docs/sample-feature-tree.md"
    
    logger.info("=" * 60)
    logger.info("Test 2: analyze-prd - PRD Module Analysis Task")
    logger.info("=" * 60)
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Workspace: {workspace_path}")
    logger.info(f"Task Type: analyze-prd")
    logger.info("=" * 60)
    
    # Check PRD file exists
    if not os.path.exists(PRD_FILE_PATH):
        logger.error(f"PRD file not found: {PRD_FILE_PATH}")
        return False
    
    # Prompt format: command line arguments
    module_name = "D1组建团队"
    prompt = f'--module "{module_name}" --feature-tree "{feature_tree_path}" --prd "{PRD_FILE_PATH}"'
    
    logger.info(f"Prompt: {prompt}")
    logger.info(f"Internal conversion: /analyze-prd {prompt}")
    logger.info("=" * 60)
    
    try:
        messages, success, error = await stream_and_collect(
            prompt=prompt,
            session_id=session_id,
            task_type="analyze-prd",
        )
        
        logger.info("=" * 60)
        logger.info(f"Total messages: {len(messages)}")
        
        # Check expected output
        clarification_path = os.path.join(workspace_path, "docs", "PRD-Gen", "clarification.md")
        if os.path.exists(clarification_path):
            logger.info(f"✓ clarification.md created: {clarification_path}")
        else:
            logger.warning(f"✗ clarification.md not found: {clarification_path}")
        
        logger.info("=" * 60)
        return success
        
    finally:
        await agent_service.close_session(session_id)
        logger.info(f"Session closed: {session_id}")


# =============================================================================
# Test 3: prd-change - PRD Modification Task
# =============================================================================
async def test_prd_change():
    """
    Test PRD modification task.
    
    Task Type: prd-change
    Prompt Format: User Review on "选中的内容", msg: "提出的需求"
    Important: Must use same session_id as original PRD
    
    Note: This test simulates a modification request
    """
    from app.core.agent_service import agent_service
    
    # In real workflow, this should be the same session_id as prd-decompose
    # For testing, we create a new session
    session_id = f"test-change-{uuid.uuid4().hex[:8]}"
    workspace_path = os.path.join(DEFAULT_WORKSPACE_ROOT, session_id)
    
    logger.info("=" * 60)
    logger.info("Test 3: prd-change - PRD Modification Task")
    logger.info("=" * 60)
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Workspace: {workspace_path}")
    logger.info(f"Task Type: prd-change")
    logger.info("=" * 60)
    
    # Prompt format: User review message
    selected_content = "D1组建团队"
    change_request = "增加团队成员角色权限配置功能"
    prompt = f'User Review on "{selected_content}", msg: "{change_request}"'
    
    logger.info(f"Prompt: {prompt}")
    logger.info("Internal conversion: None (prompt passed through unchanged)")
    logger.info("=" * 60)
    
    try:
        messages, success, error = await stream_and_collect(
            prompt=prompt,
            session_id=session_id,
            task_type="prd-change",
        )
        
        logger.info("=" * 60)
        logger.info(f"Total messages: {len(messages)}")
        logger.info("=" * 60)
        return success
        
    finally:
        await agent_service.close_session(session_id)
        logger.info(f"Session closed: {session_id}")


# =============================================================================
# Test 4: chat (default) - General Chat Task
# =============================================================================
async def test_chat():
    """
    Test general chat task.
    
    Task Type: chat (or any non-special type)
    Prompt Format: Free-form user query
    """
    from app.core.agent_service import agent_service
    
    session_id = f"test-chat-{uuid.uuid4().hex[:8]}"
    workspace_path = os.path.join(DEFAULT_WORKSPACE_ROOT, session_id)
    
    logger.info("=" * 60)
    logger.info("Test 4: chat - General Chat Task")
    logger.info("=" * 60)
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Workspace: {workspace_path}")
    logger.info(f"Task Type: chat")
    logger.info("=" * 60)
    
    # Free-form prompt
    prompt = "请帮我解释一下什么是8D问题解决法？简要回答即可。"
    
    logger.info(f"Prompt: {prompt}")
    logger.info("Internal conversion: None (prompt passed through unchanged)")
    logger.info("=" * 60)
    
    try:
        messages, success, error = await stream_and_collect(
            prompt=prompt,
            session_id=session_id,
            task_type="chat",
        )
        
        logger.info("=" * 60)
        logger.info(f"Total messages: {len(messages)}")
        logger.info("=" * 60)
        return success
        
    finally:
        await agent_service.close_session(session_id)
        logger.info(f"Session closed: {session_id}")


# =============================================================================
# Test 5: Complete Workflow - Full PRD Processing Flow
# =============================================================================
async def test_workflow():
    """
    Test complete PRD processing workflow.
    
    Steps:
    1. prd-decompose: Decompose PRD into feature tree
    2. analyze-prd: Analyze specific module
    3. prd-change: Modify based on feedback
    
    Note: Steps 2 and 3 depend on Step 1 output
    """
    from app.core.agent_service import agent_service
    
    # Use consistent session_id for the workflow
    base_session_id = f"test-workflow-{uuid.uuid4().hex[:8]}"
    workspace_path = os.path.join(DEFAULT_WORKSPACE_ROOT, base_session_id)
    
    logger.info("=" * 60)
    logger.info("Test 5: Complete Workflow - Full PRD Processing")
    logger.info("=" * 60)
    logger.info(f"Base Session ID: {base_session_id}")
    logger.info(f"Workspace: {workspace_path}")
    logger.info("=" * 60)
    
    results = {}
    
    # Step 1: PRD Decompose
    logger.info("\n" + "=" * 60)
    logger.info("Step 1: PRD Decompose")
    logger.info("=" * 60)
    
    try:
        messages, success, error = await stream_and_collect(
            prompt=PRD_FILE_PATH,
            session_id=base_session_id,
            task_type="prd-decompose",
        )
        results["prd-decompose"] = success
        
        if not success:
            logger.error(f"Step 1 failed: {error}")
            # Don't close session, we'll continue to step 3 which needs the same session
        else:
            logger.info("Step 1 completed successfully")
            
    except Exception as e:
        logger.exception(f"Step 1 error: {e}")
        results["prd-decompose"] = False
    
    # Step 2: Analyze Module (uses different session_id as per docs)
    logger.info("\n" + "=" * 60)
    logger.info("Step 2: Analyze Module")
    logger.info("=" * 60)
    
    analyze_session_id = f"test-workflow-analyze-{uuid.uuid4().hex[:8]}"
    feature_tree_path = os.path.join(workspace_path, "docs", "PRD-Gen", "FEATURE_TREE.md")
    
    try:
        module_name = "D1组建团队"
        prompt = f'--module "{module_name}" --feature-tree "{feature_tree_path}" --prd "{PRD_FILE_PATH}"'
        
        messages, success, error = await stream_and_collect(
            prompt=prompt,
            session_id=analyze_session_id,
            task_type="analyze-prd",
        )
        results["analyze-prd"] = success
        
        if not success:
            logger.error(f"Step 2 failed: {error}")
        else:
            logger.info("Step 2 completed successfully")
            
    except Exception as e:
        logger.exception(f"Step 2 error: {e}")
        results["analyze-prd"] = False
    finally:
        await agent_service.close_session(analyze_session_id)
    
    # Step 3: PRD Change (uses same session_id as step 1)
    logger.info("\n" + "=" * 60)
    logger.info("Step 3: PRD Change")
    logger.info("=" * 60)
    
    try:
        prompt = 'User Review on "D1组建团队", msg: "增加团队成员角色权限配置功能"'
        
        messages, success, error = await stream_and_collect(
            prompt=prompt,
            session_id=base_session_id,  # Same session as step 1
            task_type="prd-change",
        )
        results["prd-change"] = success
        
        if not success:
            logger.error(f"Step 3 failed: {error}")
        else:
            logger.info("Step 3 completed successfully")
            
    except Exception as e:
        logger.exception(f"Step 3 error: {e}")
        results["prd-change"] = False
    finally:
        await agent_service.close_session(base_session_id)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Workflow Summary")
    logger.info("=" * 60)
    for step, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"  {step}: {status}")
    logger.info("=" * 60)
    
    return all(results.values())


# =============================================================================
# Main Entry Point
# =============================================================================
async def main(test_name: Optional[str] = None):
    """Run tests."""
    from app.core.agent_service import agent_service
    
    test_map = {
        "prd-decompose": test_prd_decompose,
        "analyze-prd": test_analyze_prd,
        "prd-change": test_prd_change,
        "chat": test_chat,
        "workflow": test_workflow,
    }
    
    results = {}
    
    if test_name:
        # Run specific test
        if test_name not in test_map:
            logger.error(f"Unknown test: {test_name}")
            logger.info(f"Available tests: {', '.join(test_map.keys())}")
            return False
        
        logger.info(f"Running test: {test_name}")
        results[test_name] = await test_map[test_name]()
    else:
        # Run all tests
        logger.info("Running all tests...")
        for name, test_func in test_map.items():
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Running: {name}")
            logger.info("=" * 60)
            try:
                results[name] = await test_func()
            except Exception as e:
                logger.exception(f"Test {name} failed with exception: {e}")
                results[name] = False
    
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    
    all_passed = True
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    logger.info("=" * 60)
    logger.info(f"Overall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    logger.info("=" * 60)
    
    # Cleanup
    await agent_service.close_all_sessions()
    
    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test chat_stream task types")
    parser.add_argument(
        "--test",
        type=str,
        choices=["prd-decompose", "analyze-prd", "prd-change", "chat", "workflow"],
        help="Run specific test (default: run all tests)"
    )
    args = parser.parse_args()
    
    success = asyncio.run(main(args.test))
    sys.exit(0 if success else 1)
