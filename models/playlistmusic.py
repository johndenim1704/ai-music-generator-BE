from sqlalchemy import Column, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from config.db import Base




class PlaylistMusic(Base):
    __tablename__ = 'playlist_music'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(Integer, ForeignKey('playlists.id' , ondelete="CASCADE"), nullable=False)
    music_id = Column(Integer, ForeignKey('music.id' , ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, default=0)  # To maintain order of songs in playlist
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    playlist = relationship("Playlist", back_populates="playlist_music")
    music = relationship("Music", back_populates="playlist_items")