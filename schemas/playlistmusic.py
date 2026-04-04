from pydantic import BaseModel
from typing import List, Optional

class PlaylistMusicSchema(BaseModel):
    playlist_id: int
    music_id: int
    order_index: Optional[int] = None  # Optional: order of music in the playlist
    added_at: Optional[str] = None  # ISO format date-time string
    class Config:
        orm_mode = True

class PlaylistMusicCreate(PlaylistMusicSchema):
    pass

class PlaylistMusicRead(PlaylistMusicSchema):
    pass

class PlaylistMusicUpdate(BaseModel):
    playlist_id: int
    music_id: int
    order_index: Optional[int] = None  # Update order of music in the playlist
    added_at: Optional[str] = None  # Update added date-time

    class Config:
        orm_mode = True  # allows reading from ORM models

class PlaylistMusicDelete(BaseModel):
    playlist_id: int
    music_id: int
    class Config:
        orm_mode = True  # allows reading from ORM models
