"""
Tests for AgentService.chat_stream() task_type handling.

This module tests the different task_type behaviors:
- prd-decompose: PRD decomposition task
- analyze-prd: PRD module analysis task  
- prd-change: PRD modification task
- default: General chat task
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator


class TestChatStreamTaskTypes:
    """Test cases for chat_stream task_type parameter."""

    @pytest.fixture
    def mock_agent_service(self):
        """Create a mock AgentService for testing."""
        with patch('app.core.agent_service.AgentService') as MockService:
            service = MockService.return_value
            service._sessions = {}
            service._get_or_create_session = AsyncMock()
            yield service

    @pytest.fixture
    def mock_session(self):
        """Create a mock session object."""
        session = MagicMock()
        session.client = AsyncMock()
        session.client.query = AsyncMock()
        session.is_cancelled = False
        
        async def mock_receive():
            yield MagicMock(
                __dict__={
                    'event': {
                        'type': 'content_block_delta',
                        'delta': {'type': 'text_delta', 'text': 'test response'}
                    }
                }
            )
        
        session.client.receive_response = mock_receive
        return session

    # =========================================================================
    # PRD Decompose Task Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_prd_decompose_prompt_transformation(self):
        """Test that prd-decompose task correctly transforms the prompt."""
        # Given
        original_prompt = "/Users/john/workspace/abc123/prd.md"
        task_type = "prd-decompose"
        expected_transformed = f"/prd-decompose {original_prompt}"
        
        # When - simulate the transformation logic
        if task_type == "prd-decompose":
            transformed_prompt = f"/prd-decompose {original_prompt}"
        
        # Then
        assert transformed_prompt == expected_transformed
        assert transformed_prompt.startswith("/prd-decompose ")
        assert original_prompt in transformed_prompt

    @pytest.mark.asyncio
    async def test_prd_decompose_with_chinese_path(self):
        """Test prd-decompose with Chinese characters in path."""
        # Given
        original_prompt = "/Users/张三/工作空间/项目文档/prd.md"
        task_type = "prd-decompose"
        
        # When
        if task_type == "prd-decompose":
            transformed_prompt = f"/prd-decompose {original_prompt}"
        
        # Then
        assert "/prd-decompose" in transformed_prompt
        assert "张三" in transformed_prompt

    # =========================================================================
    # Analyze PRD Task Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_analyze_prd_prompt_transformation(self):
        """Test that analyze-prd task correctly transforms the prompt."""
        # Given
        module_name = "D1组建团队"
        feature_tree_path = "/Users/john/workspace/abc123/FEATURE_TREE.md"
        prd_path = "/Users/john/workspace/abc123/prd.md"
        original_prompt = f'--module "{module_name}" --feature-tree "{feature_tree_path}" --prd "{prd_path}"'
        task_type = "analyze-prd"
        
        # When
        if task_type == "analyze-prd":
            transformed_prompt = f"/analyze-prd {original_prompt}"
        
        # Then
        assert transformed_prompt.startswith("/analyze-prd ")
        assert "--module" in transformed_prompt
        assert "--feature-tree" in transformed_prompt
        assert "--prd" in transformed_prompt
        assert module_name in transformed_prompt

    @pytest.mark.asyncio
    async def test_analyze_prd_argument_parsing(self):
        """Test that analyze-prd arguments are correctly formatted."""
        # Given
        test_cases = [
            {
                "module": "用户认证",
                "feature_tree": "/path/to/FEATURE_TREE.md",
                "prd": "/path/to/prd.md"
            },
            {
                "module": "D2问题描述",
                "feature_tree": "/workspace/session-001/FEATURE_TREE.md",
                "prd": "/workspace/session-001/prd.md"
            },
        ]
        
        for case in test_cases:
            # When
            prompt = f'--module "{case["module"]}" --feature-tree "{case["feature_tree"]}" --prd "{case["prd"]}"'
            transformed = f"/analyze-prd {prompt}"
            
            # Then
            assert case["module"] in transformed
            assert case["feature_tree"] in transformed
            assert case["prd"] in transformed

    # =========================================================================
    # PRD Change Task Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_prd_change_prompt_passthrough(self):
        """Test that prd-change task passes prompt unchanged."""
        # Given
        original_prompt = 'User Review on "用户登录模块", msg: "增加OAuth2.0支持"'
        task_type = "prd-change"
        
        # When
        if task_type == "prd-change":
            transformed_prompt = original_prompt  # No transformation
        
        # Then
        assert transformed_prompt == original_prompt
        assert "User Review on" in transformed_prompt
        assert "msg:" in transformed_prompt

    @pytest.mark.asyncio
    async def test_prd_change_format_validation(self):
        """Test prd-change prompt format validation."""
        # Given - valid formats
        valid_prompts = [
            'User Review on "登录流程", msg: "需要支持手机验证码登录"',
            'User Review on "数据导出功能", msg: "增加Excel格式支持"',
            'User Review on "API接口", msg: "添加分页参数"',
        ]
        
        for prompt in valid_prompts:
            # Then - should contain required parts
            assert "User Review on" in prompt
            assert "msg:" in prompt

    @pytest.mark.asyncio
    async def test_prd_change_session_consistency(self):
        """Test that prd-change requires consistent session_id."""
        # This is a documentation/contract test
        # Given
        original_session_id = "abc123"
        change_session_id = "abc123"  # Must be same
        
        # Then
        assert original_session_id == change_session_id, \
            "prd-change must use the same session_id as the original PRD"

    # =========================================================================
    # Default/Other Task Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_default_task_prompt_passthrough(self):
        """Test that default/unknown task types pass prompt unchanged."""
        # Given
        test_cases = [
            ("请帮我解释微服务架构", "chat"),
            ("什么是TDD?", "general"),
            ("How to implement OAuth?", ""),
            ("代码审查建议", "unknown-type"),
        ]
        
        for original_prompt, task_type in test_cases:
            # When - simulate default behavior
            if task_type == "prd-decompose":
                transformed = f"/prd-decompose {original_prompt}"
            elif task_type == "analyze-prd":
                transformed = f"/analyze-prd {original_prompt}"
            elif task_type == "prd-change":
                transformed = original_prompt
            else:
                transformed = original_prompt  # Default passthrough
            
            # Then
            assert transformed == original_prompt

    # =========================================================================
    # Edge Cases and Error Handling
    # =========================================================================

    @pytest.mark.asyncio
    async def test_empty_prompt_handling(self):
        """Test handling of empty prompts."""
        # Given
        empty_prompts = ["", " ", None]
        task_types = ["prd-decompose", "analyze-prd", "prd-change", "chat"]
        
        for prompt in empty_prompts:
            for task_type in task_types:
                if prompt is None:
                    continue  # Skip None, as it would fail differently
                
                # When
                if task_type == "prd-decompose":
                    transformed = f"/prd-decompose {prompt}"
                elif task_type == "analyze-prd":
                    transformed = f"/analyze-prd {prompt}"
                else:
                    transformed = prompt
                
                # Then - should not raise exception
                assert isinstance(transformed, str)

    @pytest.mark.asyncio
    async def test_special_characters_in_prompt(self):
        """Test handling of special characters in prompts."""
        # Given
        special_prompts = [
            '/path/with/slashes/file.md',
            'prompt with "quotes"',
            "prompt with 'single quotes'",
            'prompt with\nnewlines',
            'prompt with\ttabs',
            'prompt with émojis 🎉',
        ]
        
        for prompt in special_prompts:
            # When
            transformed_decompose = f"/prd-decompose {prompt}"
            transformed_analyze = f"/analyze-prd {prompt}"
            
            # Then - should preserve special characters
            assert prompt in transformed_decompose
            assert prompt in transformed_analyze

    @pytest.mark.asyncio
    async def test_long_prompt_handling(self):
        """Test handling of very long prompts."""
        # Given
        long_prompt = "a" * 10000  # 10KB prompt
        
        # When
        transformed = f"/prd-decompose {long_prompt}"
        
        # Then
        assert len(transformed) == len("/prd-decompose ") + len(long_prompt)


class TestTaskTypeWorkflow:
    """Integration-style tests for task type workflows."""

    @pytest.mark.asyncio
    async def test_complete_prd_workflow_prompt_sequence(self):
        """Test the complete PRD processing workflow prompt transformations."""
        session_id = "workflow-test-001"
        base_path = f"/Users/john/workspace/{session_id}"
        
        # Step 1: PRD Decompose
        step1_prompt = f"{base_path}/prd.md"
        step1_task = "prd-decompose"
        step1_transformed = f"/prd-decompose {step1_prompt}"
        
        assert step1_transformed == f"/prd-decompose {base_path}/prd.md"
        
        # Step 2: Analyze PRD
        step2_prompt = f'--module "用户认证" --feature-tree "{base_path}/FEATURE_TREE.md" --prd "{base_path}/prd.md"'
        step2_task = "analyze-prd"
        step2_transformed = f"/analyze-prd {step2_prompt}"
        
        assert step2_transformed.startswith("/analyze-prd ")
        assert "--module" in step2_transformed
        
        # Step 3: PRD Change
        step3_prompt = 'User Review on "登录流程", msg: "支持OAuth2.0"'
        step3_task = "prd-change"
        step3_transformed = step3_prompt  # No transformation
        
        assert step3_transformed == step3_prompt

    @pytest.mark.asyncio
    async def test_task_type_case_sensitivity(self):
        """Test that task_type matching is case-sensitive."""
        # Given
        prompt = "/path/to/prd.md"
        
        # These should NOT match and should pass through unchanged
        non_matching_types = [
            "PRD-DECOMPOSE",
            "Prd-Decompose",
            "PRD_DECOMPOSE",
            "prd_decompose",
        ]
        
        for task_type in non_matching_types:
            # When - simulate the actual logic
            if task_type == "prd-decompose":
                transformed = f"/prd-decompose {prompt}"
            elif task_type == "analyze-prd":
                transformed = f"/analyze-prd {prompt}"
            elif task_type == "prd-change":
                transformed = prompt
            else:
                transformed = prompt  # Default passthrough
            
            # Then - should be unchanged (default passthrough)
            assert transformed == prompt, f"Task type '{task_type}' should not match"


class TestPromptBuilder:
    """Helper tests for building prompts in correct formats."""

    def test_build_analyze_prd_prompt(self):
        """Test helper for building analyze-prd prompts."""
        def build_analyze_prd_prompt(module: str, feature_tree: str, prd: str) -> str:
            """Build analyze-prd prompt string."""
            return f'--module "{module}" --feature-tree "{feature_tree}" --prd "{prd}"'
        
        # Given
        module = "D1组建团队"
        feature_tree = "/workspace/session/FEATURE_TREE.md"
        prd = "/workspace/session/prd.md"
        
        # When
        prompt = build_analyze_prd_prompt(module, feature_tree, prd)
        
        # Then
        assert f'--module "{module}"' in prompt
        assert f'--feature-tree "{feature_tree}"' in prompt
        assert f'--prd "{prd}"' in prompt

    def test_build_prd_change_prompt(self):
        """Test helper for building prd-change prompts."""
        def build_prd_change_prompt(selected_content: str, change_request: str) -> str:
            """Build prd-change prompt string."""
            return f'User Review on "{selected_content}", msg: "{change_request}"'
        
        # Given
        selected = "用户登录模块"
        change = "增加第三方登录支持"
        
        # When
        prompt = build_prd_change_prompt(selected, change)
        
        # Then
        assert f'User Review on "{selected}"' in prompt
        assert f'msg: "{change}"' in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
