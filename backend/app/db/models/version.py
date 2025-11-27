"""
Version Model

版本管理数据模型
"""

from sqlalchemy import Column, BigInteger, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.db.base import Base, BaseModel


class Version(Base, BaseModel):
    """
    版本表

    记录项目的版本历史和Git提交信息
    """
    __tablename__ = "code_version"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="Primary Key ID")
    code = Column(String(64), nullable=False, comment="版本编号")
    project_id = Column(BigInteger, ForeignKey("code_project.id", ondelete="CASCADE"), nullable=False, comment="所属项目ID")
    msg = Column(String(512), nullable=True, comment="提交信息，命名规范：[SpecCoding Auto Commit] - 具体commit内容")
    commit = Column(String(64), nullable=False, comment="Git commit ID")

    # Relationships
    # project = relationship("Project", backref="code_version")

    # Indexes
    __table_args__ = (
        Index("idx_version_project_id", "project_id"),
        Index("idx_version_code", "code"),
        Index("idx_version_commit", "commit"),
    )

    def __repr__(self):
        return f"<Version(id={self.id}, code={self.code}, commit={self.commit})>"
