from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class AdItem(BaseModel):
    id: int
    name: str 
    description: Optional[str] = None
    image_url: Optional[str]


class AdCategory(BaseModel):
    id: int
    name: str
    description: Optional[str]
    items: List[AdItem]

class MarketingAdCreate(BaseModel):
    category_name: str
    category_description: Optional[str] = None
    item_name: str
    item_description: Optional[str] = None
    image_url: Optional[str] = None

class MarketingAdRead(MarketingAdCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
