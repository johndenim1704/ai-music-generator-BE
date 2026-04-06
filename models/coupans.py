from config.db import Base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Enum,ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enums import couponenums

class Coupon(Base):
    __tablename__ = 'coupons'

    id = Column(Integer, primary_key=True, autoincrement=True)
    stripe_coupon_id = Column(String(255), unique=True, nullable=False, index=True)
    stripe_promotion_code_id = Column(String(255), unique=True, nullable=False, index=True)
    code = Column(String(255), unique=True, nullable=False, index=True)
    
    discount_type = Column(Enum(couponenums.DiscountType), nullable=False)
    value = Column(Float, nullable=True) 
    buy_count = Column(Integer, nullable=True)
    get_count = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    applies_to_entity = Column(Enum(couponenums.CouponScope), default=couponenums.CouponScope.GLOBAL)
    applies_to_id = Column(Integer, ForeignKey('licenses.id', ondelete="SET NULL"), nullable=True)
    max_redemptions = Column(Integer, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # relationships
    license = relationship("License", back_populates="coupons")