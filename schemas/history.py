from pydantic import BaseModel
from typing import Optional

class HistorySchema(BaseModel):
    music_id: int
    user_id: int
    played_at: str  # ISO format date-time string
    play_duration: Optional[int] = None  # Duration in seconds
    completed: Optional[bool] = None  # Whether the song was played completely
    device_info: Optional[str] = None  # Optional: track device used
    

    class Config:
        orm_mode = True

class HistoryCreate(HistorySchema):
    pass

class HistoryRead(HistorySchema):
    id: int  # Unique identifier for the history record

    class Config:
        orm_mode = True


class HistoryUpdate(BaseModel):
    play_duration: Optional[int] = None  # Duration in seconds
    completed: Optional[bool] = None  # Whether the song was played completely
    device_info: Optional[str] = None  # Optional: track device used
    
    class Config:
        orm_mode = True  # allows reading from ORM models

