from pydantic import BaseModel
from typing import List,Optional


class CheckoutRequest(BaseModel):
    license_ids: List[int]
    coupon_code: Optional[str] = None

# Pydantic model for the response
class CheckoutResponse(BaseModel):
    checkout_url: str