from sqlalchemy import Column, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from config.db import Base
from sqlalchemy.schema import UniqueConstraint


class UserLikedMusic(Base):
    __tablename__ = 'user_liked_music'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    music_id = Column(Integer, ForeignKey('music.id', ondelete="CASCADE"), nullable=False)
    liked_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("Users", back_populates="liked_music")
    music = relationship("Music", back_populates="liked_by_users")
    
    # Ensure a user can't like the same song twice
    __table_args__ = (
         UniqueConstraint('user_id', 'music_id', name='uix_user_music_like'),
        {'mysql_engine': 'InnoDB'},
    )