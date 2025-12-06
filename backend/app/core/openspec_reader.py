# -*- coding: utf-8 -*-
"""
OpenSpec Reader Tool

通过 spec_id 读取 OpenSpec 规格内容的工具类。
支持从容器外挂载目录读取 spec.md 文件。

目录结构:
    /workspace/openspec/changes/{spec_id}/specs/{component}/spec.md
    /workspace/openspec/changes/archive/{spec_id}/specs/{component}/spec.md
"""

import os
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SpecContent:
    """单个 spec.md 的内容"""
    component: str
    content: str
    path: str
    length: int = 0
    
    def __post_init__(self):
        self.length = len(self.content)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "content": self.content,
            "path": self.path,
            "length": self.length,
        }


@dataclass
class OpenSpecInfo:
    """OpenSpec 规格信息"""
    spec_id: str
    specs: List[SpecContent] = field(default_factory=list)
    is_archived: bool = False
    base_path: str = ""
    
    @property
    def total(self) -> int:
        return len(self.specs)
    
    @property
    def all_content(self) -> str:
        """合并所有 spec.md 的内容"""
        if not self.specs:
            return ""
        
        contents = []
        for spec in self.specs:
            contents.append(f"# Component: {spec.component}\n\n{spec.content}")
        
        return "\n\n---\n\n".join(contents)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "specs": [s.to_dict() for s in self.specs],
            "total": self.total,
            "is_archived": self.is_archived,
            "all_content": self.all_content,
        }


class OpenSpecReader:
    """
    OpenSpec 读取工具
    
    通过 spec_id 从工作空间目录读取 spec.md 内容。
    自动发现所有 component 目录。
    
    Usage:
        reader = OpenSpecReader(workspace_path="/path/to/workspace")
        
        # 获取所有可用的 spec_id
        spec_ids = reader.list_spec_ids()
        
        # 读取指定 spec_id 的所有 spec.md
        spec_info = reader.read_spec(spec_id="snake-game")
        print(spec_info.all_content)
        
        # 读取指定 component 的 spec.md
        content = reader.read_spec_content(spec_id="snake-game", component="game-component")
    """
    
    # OpenSpec 目录常量
    OPENSPEC_DIR = "openspec"
    CHANGES_DIR = "changes"
    ARCHIVE_DIR = "archive"
    SPECS_DIR = "specs"
    SPEC_FILE = "spec.md"
    PROPOSAL_FILE = "proposal.md"
    
    # 忽略的目录
    IGNORED_DIRS = {"archive", "dummy", ".git", "__pycache__"}
    
    def __init__(self, workspace_path: str):
        """
        初始化 OpenSpec 读取器
        
        Args:
            workspace_path: 工作空间路径（容器外挂载目录）
        """
        self.workspace_path = workspace_path
        self._changes_dir = os.path.join(workspace_path, self.OPENSPEC_DIR, self.CHANGES_DIR)
        self._archive_dir = os.path.join(self._changes_dir, self.ARCHIVE_DIR)
    
    def list_spec_ids(self, include_archived: bool = False) -> List[str]:
        """
        列出所有可用的 spec_id
        
        Args:
            include_archived: 是否包含已归档的规格
            
        Returns:
            spec_id 列表
        """
        spec_ids = []
        
        # 活跃的规格
        if os.path.exists(self._changes_dir):
            for item in os.listdir(self._changes_dir):
                item_path = os.path.join(self._changes_dir, item)
                if os.path.isdir(item_path) and item not in self.IGNORED_DIRS:
                    spec_ids.append(item)
        
        # 归档的规格
        if include_archived and os.path.exists(self._archive_dir):
            for item in os.listdir(self._archive_dir):
                item_path = os.path.join(self._archive_dir, item)
                if os.path.isdir(item_path) and item not in self.IGNORED_DIRS:
                    if item not in spec_ids:  # 避免重复
                        spec_ids.append(f"{item} (archived)")
        
        return sorted(spec_ids)
    
    def _find_spec_dir(self, spec_id: str) -> tuple[Optional[str], bool]:
        """
        查找 spec_id 对应的目录
        
        Args:
            spec_id: OpenSpec ID
            
        Returns:
            (目录路径, 是否归档)
        """
        # 先检查活跃目录
        active_path = os.path.join(self._changes_dir, spec_id)
        if os.path.exists(active_path):
            return active_path, False
        
        # 再检查归档目录
        archive_path = os.path.join(self._archive_dir, spec_id)
        if os.path.exists(archive_path):
            return archive_path, True
        
        return None, False
    
    def _discover_components(self, spec_dir: str) -> List[str]:
        """
        自动发现 specs 目录下的所有 component
        
        Args:
            spec_dir: spec_id 目录路径
            
        Returns:
            component 名称列表
        """
        specs_dir = os.path.join(spec_dir, self.SPECS_DIR)
        if not os.path.exists(specs_dir):
            return []
        
        components = []
        for item in os.listdir(specs_dir):
            item_path = os.path.join(specs_dir, item)
            if os.path.isdir(item_path):
                # 检查是否有 spec.md 文件
                spec_file = os.path.join(item_path, self.SPEC_FILE)
                if os.path.exists(spec_file):
                    components.append(item)
        
        return sorted(components)
    
    def read_spec(self, spec_id: str) -> Optional[OpenSpecInfo]:
        """
        读取指定 spec_id 的所有 spec.md 内容
        
        自动发现所有 component 并读取其 spec.md。
        
        Args:
            spec_id: OpenSpec ID (如: snake-game)
            
        Returns:
            OpenSpecInfo 对象，包含所有 spec.md 内容
            如果 spec_id 不存在则返回 None
        """
        spec_dir, is_archived = self._find_spec_dir(spec_id)
        if not spec_dir:
            logger.warning(f"OpenSpec '{spec_id}' not found")
            return None
        
        # 发现所有 component
        components = self._discover_components(spec_dir)
        if not components:
            logger.warning(f"No components found for spec '{spec_id}'")
            return OpenSpecInfo(
                spec_id=spec_id,
                specs=[],
                is_archived=is_archived,
                base_path=spec_dir,
            )
        
        # 读取每个 component 的 spec.md
        specs = []
        for component in components:
            content = self._read_spec_file(spec_dir, component)
            if content is not None:
                relative_path = os.path.join(
                    self.OPENSPEC_DIR, self.CHANGES_DIR,
                    self.ARCHIVE_DIR if is_archived else "",
                    spec_id, self.SPECS_DIR, component, self.SPEC_FILE
                ).replace("//", "/")
                
                specs.append(SpecContent(
                    component=component,
                    content=content,
                    path=relative_path,
                ))
        
        return OpenSpecInfo(
            spec_id=spec_id,
            specs=specs,
            is_archived=is_archived,
            base_path=spec_dir,
        )
    
    def _read_spec_file(self, spec_dir: str, component: str) -> Optional[str]:
        """
        读取单个 spec.md 文件
        
        Args:
            spec_dir: spec_id 目录路径
            component: 组件名称
            
        Returns:
            文件内容，读取失败返回 None
        """
        spec_file = os.path.join(spec_dir, self.SPECS_DIR, component, self.SPEC_FILE)
        
        if not os.path.exists(spec_file):
            logger.warning(f"spec.md not found: {spec_file}")
            return None
        
        try:
            with open(spec_file, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read {spec_file}: {e}")
            return None
    
    def read_spec_content(
        self,
        spec_id: str,
        component: Optional[str] = None,
    ) -> Optional[str]:
        """
        读取 spec.md 内容（简化接口）
        
        Args:
            spec_id: OpenSpec ID
            component: 组件名称（可选，不指定则返回所有内容合并）
            
        Returns:
            spec.md 内容字符串
        """
        spec_info = self.read_spec(spec_id)
        if not spec_info:
            return None
        
        if component:
            # 返回指定 component 的内容
            for spec in spec_info.specs:
                if spec.component == component:
                    return spec.content
            return None
        else:
            # 返回所有内容合并
            return spec_info.all_content
    
    def read_proposal(self, spec_id: str) -> Optional[str]:
        """
        读取 proposal.md 内容
        
        Args:
            spec_id: OpenSpec ID
            
        Returns:
            proposal.md 内容字符串，如果不存在则返回 None
            
        路径: /workspace/openspec/changes/{spec_id}/proposal.md
        """
        spec_dir, is_archived = self._find_spec_dir(spec_id)
        if not spec_dir:
            logger.warning(f"OpenSpec '{spec_id}' not found for proposal")
            return None
        
        proposal_file = os.path.join(spec_dir, self.PROPOSAL_FILE)
        
        if not os.path.exists(proposal_file):
            logger.warning(f"proposal.md not found: {proposal_file}")
            return None
        
        try:
            with open(proposal_file, "r", encoding="utf-8") as f:
                content = f.read()
                logger.info(f"Successfully read proposal.md for spec '{spec_id}', length: {len(content)}")
                return content
        except Exception as e:
            logger.error(f"Failed to read proposal.md for spec '{spec_id}': {e}")
            return None
    
    def get_spec_summary(self, spec_id: str) -> Optional[Dict[str, Any]]:
        """
        获取规格摘要信息（不读取完整内容）
        
        Args:
            spec_id: OpenSpec ID
            
        Returns:
            摘要信息字典
        """
        spec_dir, is_archived = self._find_spec_dir(spec_id)
        if not spec_dir:
            return None
        
        components = self._discover_components(spec_dir)
        
        return {
            "spec_id": spec_id,
            "is_archived": is_archived,
            "components": components,
            "total_components": len(components),
            "base_path": spec_dir,
        }


def get_spec_content_by_id(
    workspace_path: str,
    spec_id: str,
    component: Optional[str] = None,
) -> Optional[str]:
    """
    便捷函数：通过 spec_id 获取 spec.md 内容
    
    Args:
        workspace_path: 工作空间路径
        spec_id: OpenSpec ID
        component: 组件名称（可选）
        
    Returns:
        spec.md 内容
    
    Usage:
        content = get_spec_content_by_id(
            workspace_path="/path/to/workspace",
            spec_id="snake-game"
        )
    """
    reader = OpenSpecReader(workspace_path)
    return reader.read_spec_content(spec_id, component)


def get_proposal_content_by_id(
    workspace_path: str,
    spec_id: str,
) -> Optional[str]:
    """
    便捷函数：通过 spec_id 获取 proposal.md 内容
    
    Args:
        workspace_path: 工作空间路径
        spec_id: OpenSpec ID
        
    Returns:
        proposal.md 内容
        
    路径: /workspace/openspec/changes/{spec_id}/proposal.md
    
    Usage:
        content = get_proposal_content_by_id(
            workspace_path="/path/to/workspace",
            spec_id="snake-game"
        )
    """
    reader = OpenSpecReader(workspace_path)
    return reader.read_proposal(spec_id)


def list_available_specs(
    workspace_path: str,
    include_archived: bool = True,
) -> List[str]:
    """
    便捷函数：列出所有可用的 spec_id
    
    Args:
        workspace_path: 工作空间路径
        include_archived: 是否包含已归档的
        
    Returns:
        spec_id 列表
    """
    reader = OpenSpecReader(workspace_path)
    return reader.list_spec_ids(include_archived)

