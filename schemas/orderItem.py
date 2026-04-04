from pydantic import BaseModel, Field
from datetime import datetime

class OrderItemBase(BaseModel):
    """Base schema for an order item, capturing the snapshot."""
    item_description: str
    price_at_purchase: float = Field(..., gt=0) 

class OrderItemResponse(OrderItemBase):
    """Schema for displaying a single item within a detailed order response."""
    id: int
    
    class Config:
        from_attributes = True