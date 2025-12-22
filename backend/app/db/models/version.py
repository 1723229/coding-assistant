"""
Version Model

版本管理数据模型
"""

from enum import Enum
from sqlalchemy import Column, BigInteger, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.db.base import Base, BaseModel


class VersionStatus(str, Enum):
    """版本状态枚举"""
    SPEC_GENERATING = "spec_generating"  # Spec生成中（容器运行）
    SPEC_GENERATED = "spec_generated"    # Spec已生成
    CODE_BUILDING = "code_building"      # 代码构建中（容器运行）
    BUILD_COMPLETED = "build_completed"  # 构建完成（容器销毁）
    DELETED = "deleted"  # 删除module


class Version(Base, BaseModel):
    """
    版本表

    记录模块的版本历史和Git提交信息
    """
    __tablename__ = "code_version"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="Primary Key ID")
    code = Column(String(64), nullable=False, comment="版本编号")
    module_id = Column(BigInteger, nullable=False, comment="所属模块ID")
    msg = Column(String(512), nullable=True, comment="提交信息，命名规范：[SpecCoding Auto Commit] - 具体commit内容")
    commit = Column(String(64), nullable=True, comment="Git commit ID")
    status = Column(String(32), nullable=False, default=VersionStatus.SPEC_GENERATING.value, comment="版本状态：spec_generating/spec_generated/code_building/build_completed")
    # spec_content = Column(String(10000), nullable=True, comment="生成的Spec内容")

    # Relationships
    # module = relationship("Module", backref="code_version")

    # Indexes
    __table_args__ = (
        Index("idx_version_module_id", "module_id"),
        Index("idx_version_code", "code"),
        Index("idx_version_commit", "commit"),
    )

    def __repr__(self):
        return f"<Version(id={self.id}, code={self.code}, commit={self.commit})>"
