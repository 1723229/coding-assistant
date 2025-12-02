"""
Module Model

模块管理数据模型
"""

from sqlalchemy import Column, BigInteger, String, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.db.base import Base, BaseModel


class ModuleType(str, enum.Enum):
    """模块类型枚举"""
    NODE = "NODE"  # 功能节点（功能说明，与子节点共享URL）
    POINT = "POINT"  # 功能点（独立功能，创建session和workspace）


class Module(Base, BaseModel):
    """
    模块表

    支持树形结构的项目模块管理
    """
    __tablename__ = "code_module"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="Primary Key ID")
    project_id = Column(BigInteger, ForeignKey("code_project.id", ondelete="CASCADE"), nullable=False, comment="所属项目ID")
    parent_id = Column(BigInteger, nullable=True, comment="父节点ID，空则为根节点")
    type = Column(SQLEnum(ModuleType), nullable=False, comment="模块类型：NODE-功能节点 POINT-功能点")
    name = Column(String(255), nullable=False, comment="模块名称")
    code = Column(String(64), nullable=False, comment="模块代码，在Project内唯一")
    url = Column(String(512), nullable=True, comment="可访问的链接（NODE类型与子节点共享）")
    require_content = Column(String(2000), nullable=True, comment="功能需求描述")
    preview_url = Column(String(512), nullable=True, comment="预览页面URL")
    spec_file_path = Column(String(512), nullable=True, comment="spec_file_path")

    # POINT 类型的 session 和 workspace 管理字段
    session_id = Column(String(64), nullable=True, unique=True, index=True, comment="会话ID（仅POINT类型）")
    workspace_path = Column(String(512), nullable=True, comment="工作空间路径（仅POINT类型）")
    container_id = Column(String(128), nullable=True, comment="Docker容器ID（仅POINT类型）")
    branch = Column(String(128), nullable=True, comment="Git分支（仅POINT类型）")
    latest_commit_id = Column(String(64), nullable=True, comment="最新commit ID（仅POINT类型）")
    is_active = Column(BigInteger, nullable=False, default=1, comment="是否激活")

    # Relationships
    # project = relationship("Project", backref="code_module")

    # Indexes
    __table_args__ = (
        Index("idx_module_project_id", "project_id"),
        Index("idx_module_parent_id", "parent_id"),
        Index("idx_module_session_id", "session_id"),
        Index("idx_module_project_code", "project_id", "code", unique=True),
    )

    def __repr__(self):
        return f"<Module(id={self.id}, code={self.code}, name={self.name}, type={self.type})>"
