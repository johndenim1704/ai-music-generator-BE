from config.db import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship



class Music(Base):
    __tablename__ = 'music'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    artist = Column(String(255), nullable=False)
    album = Column(String(255), nullable=False)
    genre = Column(String(255), nullable=False)
    track_type = Column(String(255), nullable=False)  # e.g., single, album, EP
    mood = Column(String(255), nullable=False)
    instruments = Column(String(255), nullable=False)
    bpm = Column(Integer)
    duration = Column(Integer)
    mp3_url = Column(String(500), nullable=True)
    wav_url = Column(String(500), nullable=True)  # New: URL for WAV file
    cover_image_url = Column(String(500), nullable=True)
    is_ai_generated = Column(Boolean, default=False)
    is_free = Column(Boolean, default=False)
    price = Column(Float, nullable=False)
    release_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    likes_count = Column(Integer, nullable=False, default=0, server_default="0")


    # Relationships
    user = relationship("Users", back_populates="music")
    licenses = relationship("License", back_populates="music", cascade="all, delete")
    liked_by_users = relationship("UserLikedMusic", back_populates="music",cascade="all, delete-orphan")
    playlist_items = relationship("PlaylistMusic", back_populates="music",cascade="all, delete-orphan")
    listening_history = relationship("ListeningHistory", back_populates="music" , cascade="all, delete-orphan")