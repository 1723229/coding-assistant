# -*- coding: utf-8 -*-
"""
OpenSpec 提示词组装器模块

提供 OpenSpec 命令的提示词组装和 ID 提取功能。

支持的任务类型:
- spec: 执行 proposal → 提取 ID → 自动执行 preview
- preview: 提取 ID → 执行 preview + prompt
- build: 提取 ID → 执行 apply → 执行 archive

使用示例:
    from executor.services.openspec_prompt_builder import OpenSpecPromptBuilder
    
    # 组装 proposal 提示词
    prompt = OpenSpecPromptBuilder.build_proposal_prompt(user_prompt)
    
    # 从输出中提取 ID
    spec_id = OpenSpecPromptBuilder.extract_spec_id_from_output(output)
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OpenSpecPromptBuilder:
    """
    OpenSpec 提示词组装器
    
    负责根据不同任务类型组装完整的 OpenSpec 命令提示词，
    以及从 openspec list 输出中提取 ID。
    """
    
    # OpenSpec 命令前缀
    COMMAND_PREFIX = "/openspec:"
    
    # 各命令名称
    CMD_PROPOSAL = "proposal"
    CMD_PREVIEW = "preview"
    CMD_APPLY = "apply"
    CMD_ARCHIVE = "archive"
    CMD_LIST = "list"
    
    # 完整命令
    ARCHIVE_COMMAND = f"{COMMAND_PREFIX}{CMD_ARCHIVE}"
    
    # openspec list 系统命令（获取当前 changes 列表）
    LIST_SYSTEM_COMMAND = "openspec list"
    
    # Preview 时的额外说明
    PREVIEW_NOTE = "Note: 必须完整实现可运行的前端预览功能，无需向用户确认。"
    
    @classmethod
    def build_proposal_prompt(cls, user_prompt: str) -> str:
        """
        组装 proposal 提示词
        
        Args:
            user_prompt: 用户提供的提示词，包含模块信息和需求描述
                示例:
                <Module Info>
                name:问题管理，english name: Problem Management ,Module URL: /quality8d/problem-records
                
                <User's Proposal>
                Please read doc\\PRD\\质量问题管理.md for detailed description.
            
        Returns:
            完整的 proposal 命令提示词
        """
        return f"{cls.COMMAND_PREFIX}{cls.CMD_PROPOSAL} {user_prompt}"
    
    @classmethod
    def build_preview_prompt(cls, spec_id: str, user_prompt: str = "") -> str:
        """
        组装 preview 提示词
        
        Args:
            spec_id: OpenSpec ID
            user_prompt: 可选的用户反馈/评审意见
                示例:
                <User's review>
                所有页都不能滚动，导致部分内容无法查看
            
        Returns:
            完整的 preview 命令提示词
        """
        base_prompt = f"{cls.COMMAND_PREFIX}{cls.CMD_PREVIEW} {spec_id}"
        
        if user_prompt:
            return f"{base_prompt}\n\n{cls.PREVIEW_NOTE}\n\n{user_prompt}"
        return f"{base_prompt}\n\n{cls.PREVIEW_NOTE}"
    
    @classmethod
    def build_apply_prompt(cls, spec_id: str) -> str:
        """
        组装 apply 提示词
        
        Args:
            spec_id: OpenSpec ID
            
        Returns:
            完整的 apply 命令提示词
        """
        return f"{cls.COMMAND_PREFIX}{cls.CMD_APPLY} {spec_id}"
    
    @classmethod
    def build_archive_prompt(cls) -> str:
        """
        组装 archive 提示词
        
        Returns:
            archive 命令提示词
        """
        return cls.ARCHIVE_COMMAND
    
    @classmethod
    def build_list_prompt(cls) -> str:
        """
        组装获取 OpenSpec ID 的提示词
        
        使用 openspec list 系统命令获取当前 changes 列表
        
        Returns:
            用于获取 ID 的 bash 命令提示词
        """
        return f"执行命令获取 OpenSpec ID: `{cls.LIST_SYSTEM_COMMAND}`"
    
    @classmethod
    def extract_spec_id_from_output(cls, output: str) -> Optional[str]:
        """
        从 openspec list 命令输出中提取最新的 ID
        
        支持的输出格式:
        1. openspec list 输出格式:
           Changes:
               add-snake-game-to-problem-management     No tasks
           或
           Changes:
               add-snake-game-module      0/27 tasks
        2. ID: xxx 或 id: xxx 格式
        
        Args:
            output: openspec list 命令的输出文本
            
        Returns:
            提取到的 ID，如果未找到则返回 None
        """
        if not output:
            logger.warning("Empty output provided for ID extraction")
            return None
        
        # 检查是否没有 changes
        if "No active changes found" in output:
            logger.warning("No active changes found in openspec list output")
            return None
        
        # 格式1: openspec list 输出格式
        # Changes:
        #     add-snake-game-to-problem-management     No tasks
        # 或
        #     add-snake-game-module      0/27 tasks
        # 匹配 Changes: 后面缩进的行，提取第一个单词（ID）
        openspec_list_pattern = r'Changes:\s*\n\s+([a-zA-Z][a-zA-Z0-9_-]*(?:-[a-zA-Z0-9_]+)+)'
        openspec_matches = re.findall(openspec_list_pattern, output)
        
        if openspec_matches:
            spec_id = openspec_matches[0]
            logger.info(f"Extracted spec ID from openspec list format: {spec_id}")
            return spec_id
        
        # 格式2: 匹配行首的 ID（带 tasks 计数或 No tasks）
        # add-snake-game-module      0/27 tasks
        # add-snake-game-to-problem-management     No tasks
        tasks_pattern = r'^\s+([a-zA-Z][a-zA-Z0-9_-]*(?:-[a-zA-Z0-9_]+)+)\s+(?:\d+/\d+\s+tasks|No\s+tasks)'
        tasks_matches = re.findall(tasks_pattern, output, re.MULTILINE)
        
        if tasks_matches:
            spec_id = tasks_matches[0]
            logger.info(f"Extracted spec ID from tasks pattern: {spec_id}")
            return spec_id
        
        # 格式3: ID: xxx 或 id: xxx
        id_pattern = r'(?:ID|id|Id):\s*([a-zA-Z][a-zA-Z0-9_-]*(?:-[a-zA-Z0-9_]+)+)'
        id_matches = re.findall(id_pattern, output)
        
        if id_matches:
            spec_id = id_matches[0]
            logger.info(f"Extracted spec ID from 'ID:' pattern: {spec_id}")
            return spec_id
        
        # 不再使用宽泛的连字符匹配，避免匹配到 org-xxx 等非 ID 字符串
        
        logger.warning(f"Failed to extract spec ID from output (length={len(output)})")
        return None
    
    @classmethod
    def get_task_type_description(cls, task_type: str) -> str:
        """
        获取任务类型的描述
        
        Args:
            task_type: 任务类型 (spec, preview, build)
            
        Returns:
            任务类型的中文描述
        """
        descriptions = {
            "spec": "创建规格并预览 (proposal → list → preview)",
            "preview": "预览现有规格 (list → preview)",
            "build": "构建并归档 (list → apply → archive)",
        }
        return descriptions.get(task_type, f"未知任务类型: {task_type}")

