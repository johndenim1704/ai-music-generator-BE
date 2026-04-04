from sqlalchemy import Column, Integer, String, ForeignKey, Enum, UniqueConstraint
from config.db import Base
from enums.providerenum import ProviderEnum
from sqlalchemy.orm import relationship


class AuthProvider(Base):
    __tablename__ = 'auth_providers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    provider = Column(Enum(ProviderEnum), nullable=False)
    provider_id = Column(String(512), nullable=True)  # For Google/Facebook
    password_hash = Column(String(255), nullable=True)  # Only for local

    # Relationships
    user = relationship("Users", back_populates="auth_providers")

    __table_args__ = (
        UniqueConstraint('provider', 'provider_id', name='uq_provider_provider_id'),
    )
