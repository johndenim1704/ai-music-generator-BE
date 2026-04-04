from pydantic import BaseModel
from typing import List, Optional

class UserLikedMusicSchema(BaseModel):
    user_id: int
    music_id: int
    liked_at: Optional[str] = None  # ISO format date-time string

    class Config:
        orm_mode = True

class UserLikedMusicCreate(UserLikedMusicSchema):
    pass

class UserLikedMusicRead(UserLikedMusicSchema):
    id: int  # Unique identifier for the liked music record

    class Config:
        from_attributes = True  # enables .from_orm()
        orm_mode = True  # allows reading from ORM models

class UserLikedMusicUpdate(BaseModel):
    user_id: Optional[int] = None
    music_id: Optional[int] = None
    liked_at: Optional[str] = None  # Update liked date-time

    class Config:
        orm_mode = True  # allows reading from ORM models

