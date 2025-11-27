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
    MENU = "MENU"  # 菜单项
    PAGE = "PAGE"  # 页面


class Module(Base, BaseModel):
    """
    模块表

    支持树形结构的项目模块管理
    """
    __tablename__ = "code_module"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="Primary Key ID")
    project_id = Column(BigInteger, ForeignKey("code_project.id", ondelete="CASCADE"), nullable=False, comment="所属项目ID")
    parent_id = Column(BigInteger, nullable=True, comment="父节点ID，空则为根节点")
    type = Column(SQLEnum(ModuleType), nullable=False, comment="模块类型：MENU-菜单项 PAGE-页面")
    name = Column(String(255), nullable=False, comment="模块名称")
    code = Column(String(64), nullable=False, comment="模块代码，在Project内唯一")
    url = Column(String(512), nullable=True, comment="可访问的链接")
    branch = Column(String(128), nullable=True, comment="Git分支")

    # Relationships
    # project = relationship("Project", backref="code_module")

    # Indexes
    __table_args__ = (
        Index("idx_module_project_id", "project_id"),
        Index("idx_module_parent_id", "parent_id"),
        Index("idx_module_project_code", "project_id", "code", unique=True),
    )

    def __repr__(self):
        return f"<Module(id={self.id}, code={self.code}, name={self.name}, type={self.type})>"
