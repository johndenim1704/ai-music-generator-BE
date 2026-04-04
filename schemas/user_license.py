from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserLicenseBase(BaseModel):
    pass

class UserLicenseUpdate(BaseModel):
    """
    Schema for submitting the License Completion Form.
    """
    # 1. Licensee Info
    licensee_name: str
    licensee_email: EmailStr
    project_title: str
    
    # 2. Signature
    is_signed: bool
    timezone_offset: str
    
    # 3. Artist/Author Logic
    is_artist_same_as_licensee: bool
    artist_stage_name: Optional[str] = None
    author_legal_name: Optional[str] = None
    
    # 4. PRO Info
    is_pro_registered: bool
    pro_name: Optional[str] = None
    pro_ipi_number: Optional[str] = None
    
    # 5. Optional Fields
    phone_number: Optional[str] = None
    address: Optional[str] = None
    isrc_iswc: Optional[str] = None
    
    # 6. Publisher Info
    has_publisher: bool
    publisher_name: Optional[str] = None
    publisher_pro: Optional[str] = None
    publisher_ipi_number: Optional[str] = None

class UserLicenseRead(BaseModel):
    id: int
    user_id: int
    license_id: int
    purchase_date: datetime
    expiration_date: Optional[datetime] = None
    
    # Form Status
    is_form_filled: bool
    
    # Form Data (Optional, only present if filled)
    licensee_name: Optional[str] = None
    licensee_email: Optional[EmailStr] = None
    project_title: Optional[str] = None
    is_signed: Optional[bool] = None
    signed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
