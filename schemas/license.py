from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enums.licensetypesenum import LicenseTypesEnum

class LicenseSchema(BaseModel):
    music_id: int
    license_type: LicenseTypesEnum  # "leasing", "unlimited", "exclusive"
    price: float
    terms: Optional[str] = None

class LicenseResponse(LicenseSchema):
    id: int
    music_id: int
    license_type: LicenseTypesEnum
    price: float
    terms: Optional[str] = None
    created_at: datetime

class LicenseCreate(LicenseSchema):
    music_id: int
    license_type: LicenseTypesEnum  # "leasing", "unlimited", "exclusive"
    price: float
    terms: Optional[str] = None

class LicenseUpdate(LicenseSchema):
    music_id: Optional[int] = None
    license_type: Optional[LicenseTypesEnum] = None  # "leasing", "unlimited", "exclusive"
    price: Optional[float] = None
    terms: Optional[str] = None

class LicenseRead(LicenseSchema):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # enables .from_orm()
