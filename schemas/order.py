from pydantic import BaseModel
from typing import Optional, List
from enums import OrderStatusEnum, OrderOriginEnum
from datetime import datetime
from schemas.orderItem import OrderItemBase, OrderItemResponse


class OrderBase(BaseModel):
    """Base schema containing common order fields."""
    total_amount: float
    currency: str = "eur"
    status: OrderStatusEnum
    origin: OrderOriginEnum

class OrderResponse(OrderBase):
    """
    The main schema for returning order details to a user.
    This is what you'll use for "Get Order by ID" or "List My Orders" endpoints.
    """
    id: int
    created_at: datetime
    order_items: List[OrderItemResponse] 

    class Config:
        from_attributes = True

class OrderListResponse(OrderBase):
    """
    A simplified schema for listing multiple orders.
    It shows the most important info without the full item details to keep the list clean.
    """
    id: int
    created_at: datetime
    item_count: int 

    class Config:
        from_attributes = True


class OrderCreate(OrderBase):
    """
    Schema for creating an order internally after a payment intent is created.
    You would not typically have an endpoint where a user sends this directly.
    """
    user_id: int
    stripe_payment_intent_id: str
    order_items: List[OrderItemBase] 
