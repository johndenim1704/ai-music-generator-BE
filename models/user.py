from sqlalchemy import Column, Integer,Boolean, String, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from config.db import Base
from sqlalchemy.orm import relationship

class Users(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    profile_piture = Column(String(255), nullable=True)  # URL to the profile picture
    is_Admin = Column(Boolean, default=False)  # For admin users
    stripe_customer_id = Column(String(255), unique=True, nullable=True, index=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    auth_providers = relationship("AuthProvider", back_populates="user")
    licenses = relationship("UserLicense", back_populates="user")
    liked_music = relationship("UserLikedMusic", back_populates="user")
    playlists = relationship("Playlist", back_populates="user")
    listening_history = relationship("ListeningHistory", back_populates="user")
    music = relationship("Music", back_populates="user")
    cart_items = relationship("CartItem", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    mastered_music = relationship("MasteredMusic", back_populates="user", cascade="all, delete-orphan")
    music_comments = relationship("MusicComment", back_populates="user", cascade="all, delete-orphan")


    
