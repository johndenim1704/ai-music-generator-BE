
from pydantic import BaseModel, computed_field
from datetime import datetime

class MusicInCart(BaseModel):
    id: int
    name: str
    artist: str
    cover_image_url: str | None = None

    class Config:
        from_attributes = True

class LicenseInCart(BaseModel):
    id: int
    license_type: str
    price: float
    music: MusicInCart  # Nested schema to include music details

    class Config:
        from_attributes = True

# --- Main Cart Schemas ---

# Schema for adding an item to the cart (Request Body)
class CartItemCreate(BaseModel):
    license_id: int
    quantity: int

# Schema for displaying a single item in the cart (Response)
class CartItemResponse(BaseModel):
    id: int
    added_at: datetime
    
    # ADD THIS LINE: To show the quantity of the item
    quantity: int
    
    license: LicenseInCart

    # ADD THIS FUNCTION: To calculate the price for this item
    @computed_field
    @property
    def total_price(self) -> float:
        return self.quantity * self.license.price

    class Config:
        from_attributes = True

# Schema for the entire cart view (Response)
class CartView(BaseModel):
    items: list[CartItemResponse]
    total_price: float