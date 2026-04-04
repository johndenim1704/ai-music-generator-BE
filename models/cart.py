from sqlalchemy import Column, Integer, ForeignKey, DateTime, func, Float
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint
from config.db import Base

class CartItem(Base):
    __tablename__ = 'cart_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False, index=True)
    license_id = Column(Integer, ForeignKey('licenses.id', ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)  # Number of licenses in the cart
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    # --- Relationships
    user = relationship("Users", back_populates="cart_items")
    license = relationship("License", back_populates="cart_items")

    __table_args__ = (
        UniqueConstraint('user_id', 'license_id', name='uq_user_license_in_cart'),
    )