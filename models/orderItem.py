from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from config.db import Base

class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete="CASCADE"), nullable=False)
    license_id = Column(Integer, ForeignKey('licenses.id', ondelete="SET NULL"), nullable=True)
    item_description = Column(String(255), nullable=False) 
    price_at_purchase = Column(Float, nullable=False)
    
    # --- Relationships ---
    order = relationship("Order", back_populates="order_items")
    license = relationship("License")