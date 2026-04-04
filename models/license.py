from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from config.db import Base
from enums.licensetypesenum import LicenseTypesEnum 


class License(Base):
    __tablename__ = 'licenses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    music_id = Column(Integer, ForeignKey('music.id' , ondelete="CASCADE"), nullable=False)
    license_type = Column(Enum(LicenseTypesEnum))  # leasing, unlimited, exclusive
    price = Column(Float, nullable=False)
    terms = Column(String(500))  # optional: usage rights or notes
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    zip_s3_key = Column(String(500), nullable=True)
    # Relationship back to music
    music = relationship("Music", back_populates="licenses")
    user_licenses = relationship("UserLicense", back_populates="license")
    cart_items = relationship("CartItem", back_populates="license")
    coupons = relationship("Coupon", back_populates="license", cascade="all, delete-orphan")


