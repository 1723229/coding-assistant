"""
Project Model

项目管理数据模型
"""

from sqlalchemy import Column, BigInteger, String, Index
from app.db.base import Base, BaseModel


class Project(Base, BaseModel):
    """
    项目表

    存储项目的基本信息，包括代码仓库和认证信息
    """
    __tablename__ = "projects"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="Primary Key ID")
    code = Column(String(64), nullable=False, unique=True, comment="项目代码，英文+数字，不区分大小写")
    name = Column(String(255), nullable=False, comment="项目名称")
    codebase = Column(String(512), nullable=False, comment="Git仓库地址")
    token = Column(String(512), nullable=False, comment="Git认证令牌")
    owner = Column(BigInteger, nullable=False, comment="持有者ID")

    # Indexes
    __table_args__ = (
        Index("idx_project_code", "code"),
        Index("idx_project_owner", "owner"),
    )

    def __repr__(self):
        return f"<Project(id={self.id}, code={self.code}, name={self.name})>"
