from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class AdminPurchaseRead(BaseModel):
    user_name: Optional[str]
    user_email: EmailStr
    song_name: str
    amount_paid: float
    currency: Optional[str]
    purchase_date: datetime
    license_type: str
    order_id: Optional[int]
    transaction_id: Optional[str]
    status: Optional[str]

    class Config:
        from_attributes = True
