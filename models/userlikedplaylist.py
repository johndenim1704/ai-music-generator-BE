from sqlalchemy import Column, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from config.db import Base
from sqlalchemy.schema import UniqueConstraint


class UserLikedPlaylist(Base):
    __tablename__ = 'user_liked_playlists'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    playlist_id = Column(Integer, ForeignKey('playlists.id', ondelete="CASCADE"), nullable=False)
    liked_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("Users")  
    playlist = relationship("Playlist")

    __table_args__ = (
    UniqueConstraint('user_id', 'playlist_id', name='uix_user_playlist_like'),
    )