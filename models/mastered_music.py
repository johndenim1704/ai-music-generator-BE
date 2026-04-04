from config.db import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

class MasteredMusic(Base):
    __tablename__ = 'mastered_music'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    genre = Column(String(100), nullable=False)
    mastered_url = Column(String(500), nullable=False)
    original_lufs = Column(Float, nullable=False)
    original_music_url = Column(String(500), nullable=False)
    target_lufs = Column(Float, nullable=False)
    profile = Column(String(50), nullable=False)
    quality_mode = Column(String(20), nullable=False)
    sample_rate = Column(Integer, nullable=False)
    bit_depth = Column(String(50), nullable=False)
    processing_time = Column(Float, nullable=False)
    settings = Column(JSON, nullable=False)
    process_id = Column(String(100), nullable=True)
    is_remaster = Column(Integer, default=0) # 0 for new, 1 for remaster
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("Users", back_populates="mastered_music")
