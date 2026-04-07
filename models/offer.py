from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.db import Base
from enums import offerstatus 
from models.user import Users
from models.license import License
from models.order import Order



class Offer(Base):
    __tablename__ = 'offers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    license_id = Column(Integer, ForeignKey('licenses.id', ondelete="CASCADE"), nullable=False)
    
    status = Column(Enum(offerstatus.OfferStatus), nullable=False, default=offerstatus.OfferStatus.PENDING)  # PENDING, ACCEPTED, REJECTED, COUNTER_OFFERED
    
    offered_amount = Column(Float, nullable=False)
    counter_offer_amount = Column(Float, nullable=True)
    currency = Column(String(10), nullable=False, default='eur') # Or 'usd'
    
    # Stripe-related fields for charging the user later
    stripe_customer_id = Column(String(255), nullable=False)
    stripe_payment_method_id = Column(String(255), nullable=False)
    
    # To link to the final order if the offer is successful
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- Relationships ---
    user = relationship("Users")
    license = relationship("License")
    order = relationship("Order")