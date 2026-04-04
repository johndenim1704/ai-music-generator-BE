from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship
from config.db import Base



class ListeningHistory (Base):
    __tablename__ = 'listening_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    music_id = Column(Integer, ForeignKey('music.id', ondelete="CASCADE"), nullable=False)
    played_at = Column(DateTime(timezone=True), server_default=func.now())
    play_duration = Column(Integer, nullable=True)  # How long the song was played (in seconds)
    completed = Column(Boolean, default=False)  # Whether the song was played completely
    device_info = Column(String(255), nullable=True)  # Optional: track device used                  
    
    # Relationships
    user = relationship("Users", back_populates="listening_history")
    music = relationship("Music", back_populates="listening_history")
