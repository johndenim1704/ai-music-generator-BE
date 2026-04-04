from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
from config.db import Base

class MarketingAd(Base):
    __tablename__ = "marketing_ads"

    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(255), nullable=False)
    category_description = Column(Text, nullable=True)
    item_name = Column(String(255), nullable=False)
    item_description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
