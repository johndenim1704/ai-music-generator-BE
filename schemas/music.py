from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MusicSchema(BaseModel):
    name: str
    artist: str
    album: str
    genre: str
    track_type: str
    mood: str
    instruments: str
    bpm: Optional[int]
    duration: Optional[int]
    mp3_url: str
    wav_url: Optional[str] = None
    cover_image_url: Optional[str]
    is_ai_generated: bool
    is_free: bool
    price: float
    user_id: int
    likes_count: int 
    release_date: Optional[datetime]


class MusicCreate(MusicSchema):
    pass


class MusicRead(MusicSchema):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
