from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from config.db import Base


class MusicComment(Base):
    __tablename__ = 'music_comments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    music_id = Column(Integer, ForeignKey('music.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    parent_id = Column(Integer, ForeignKey('music_comments.id', ondelete='CASCADE'), nullable=True)
    content = Column(String(1000), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship('Users', back_populates='music_comments')
    music = relationship('Music', back_populates='comments')
    parent = relationship('MusicComment', remote_side=[id], back_populates='replies')
    replies = relationship(
        'MusicComment',
        back_populates='parent',
        cascade='all, delete-orphan',
        order_by='MusicComment.created_at',
    )
