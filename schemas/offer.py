from pydantic import BaseModel
from typing import Optional, List


class Offer(BaseModel):
    id: Optional[int] = None
    user_id: int
    product_id: int
    offered_amount: float
    currency: str
    stripe_customer_id: Optional[str] = None
    stripe_payment_method_id: Optional[str] = None
    status: str  # This should ideally be an Enum for better validation
    order_id: Optional[int] = None  # Reference to the order created from this offer
    created_at: Optional[str] = None  # ISO format datetime string
    updated_at: Optional[str] = None  # ISO format datetime string

    class Config:
        orm_mode = True  # Allows Pydantic to work with SQLAlchemy models directly


class CreateOfferRequest(BaseModel):
    license_id: int
    amount: float
    payment_method_id: str

class AdminOfferActionRequest(BaseModel):
    offer_id: int
    action: str  # 'accept' or 'reject'
    counter_amount: Optional[float] = None  # Only required for counter offers
    

class CounterOfferRequest(BaseModel):
    counter_amount: float

    class Config:
        orm_mode = True  # Allows Pydantic to work with SQLAlchemy models directly