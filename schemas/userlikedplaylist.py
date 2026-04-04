from pydantic import BaseModel
from typing import List, Optional

class UserLikedPlaylistSchema(BaseModel):
    user_id: int
    playlist_id: int
    liked_at: Optional[str] = None  # ISO format date-time string

    class Config:
        orm_mode = True

class UserLikedPlaylistCreate(UserLikedPlaylistSchema):
    pass

class UserLikedPlaylistRead(UserLikedPlaylistSchema):
    id: int  # Unique identifier for the liked playlist record

    class Config:
        from_attributes = True  # enables .from_orm()
        orm_mode = True  # allows reading from ORM models


class UserLikedPlaylistUpdate(BaseModel):
    liked_at: Optional[str] = None  # Update liked date-time

    class Config:
        orm_mode = True  # allows reading from ORM models

class UserLikedPlaylistDelete(BaseModel):
    id: int

    class Config:
        orm_mode = True