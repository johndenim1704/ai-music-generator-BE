from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.db import Base
from enums.orderenum import OrderStatus , OrderOrigin


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="SET NULL"), nullable=True)
    stripe_payment_intent_id = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PROCESSING)
    origin = Column(Enum(OrderOrigin), nullable=False)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default='eur')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # --- Relationships ---
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    # The user who made the purchase.
    user = relationship("Users", back_populates="orders")