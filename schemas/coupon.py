from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enums import couponenums

class CouponBase(BaseModel):
    code: str = Field(..., description="The user-facing coupon code (e.g., 'SUMMER20').")
    discount_type: couponenums.DiscountType
    value: Optional[float] = Field(None, description="The discount value. 20.0 for percent, 10.00 for fixed amount.")
    buy_count: Optional[int] = None
    get_count: Optional[int] = None
    is_active: bool = True

class CouponCreate(CouponBase):
    applies_to_entity: Optional[couponenums.CouponScope] = couponenums.CouponScope.GLOBAL
    applies_to_id: Optional[int] = None
    max_redemptions: Optional[int] = None
    expires_at: Optional[datetime] = None

class MusicInfo(BaseModel):
    name: str
    artist: str
    class Config:
        orm_mode = True
        
class LicenseInfo(BaseModel):
    id: int
    license_type: str
    price: float
    music: Optional[MusicInfo] = None
    class Config:
        orm_mode = True

class CouponResponse(CouponBase):
    id: int
    stripe_coupon_id: str
    stripe_promotion_code_id: str
    applies_to_entity: Optional[couponenums.CouponScope]
    applies_to_id: Optional[int]
    max_redemptions: Optional[int]
    expires_at: Optional[datetime]
    license: Optional[LicenseInfo] = None
    created_at: datetime

    class Config:
        orm_mode = True