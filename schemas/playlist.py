from pydantic import BaseModel
from typing import List, Optional

class PlaylistSchema(BaseModel):
    name: str
    user_id: int
    description: Optional[str] = None
    music_ids: List[int] = []
    is_public: bool = True  # Default to public
    cover_image: Optional[str] = None  # URL to the cover image
    created_at: Optional[str] = None  # ISO format date-time string
    updated_at: Optional[str] = None  # ISO format date-time string

    class Config:
        orm_mode = True

class PlaylistCreate(PlaylistSchema):
    pass

class PlaylistRead(PlaylistSchema):
    id: int  # Unique identifier for the playlist

    class Config:
        from_attributes = True  # enables .from_orm()
        orm_mode = True  # allows reading from ORM models
        
class PlaylistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    music_ids: Optional[List[int]] = None  # List of music IDs to add/remove
    is_public: Optional[bool] = None  # Update visibility
    cover_image: Optional[str] = None  # URL to the cover image

    class Config:
        orm_mode = True  # allows reading from ORM models

class PlaylistDelete(BaseModel):
    id: int
    user_id: int  # User ID to verify ownership
    class Config:
        orm_mode = True  # allows reading from ORM models
