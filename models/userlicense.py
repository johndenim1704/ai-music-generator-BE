from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Boolean, Float
from sqlalchemy.sql import func
from config.db import Base
from sqlalchemy.orm import relationship

class UserLicense(Base):
    __tablename__ = 'user_licenses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    license_id = Column(Integer, ForeignKey('licenses.id'), nullable=False)
    purchase_date = Column(DateTime(timezone=True), server_default=func.now())
    expiration_date = Column(DateTime(timezone=True), nullable=True)
    license_pdf_path = Column(String(512), nullable=True)

    user = relationship("Users", back_populates="licenses")
    license = relationship("License", back_populates="user_licenses")

    # --- License Completion Form Fields ---
    is_form_filled = Column(Boolean, default=False)
    
    # 1. Licensee Info
    licensee_name = Column(String(255), nullable=True)
    licensee_email = Column(String(255), nullable=True)
    project_title = Column(String(255), nullable=True)
    
    # 2. Signature (Checkbox + Typed Name)
    is_signed = Column(Boolean, default=False)
    signed_at = Column(DateTime(timezone=True), nullable=True)
    timezone_offset = Column(String(50), nullable=True) # e.g., "+05:30"
    
    # 3. Artist/Author Logic
    is_artist_same_as_licensee = Column(Boolean, default=False)
    artist_stage_name = Column(String(255), nullable=True)
    author_legal_name = Column(String(255), nullable=True)
    
    # 4. PRO Info
    is_pro_registered = Column(Boolean, default=False)
    pro_name = Column(String(255), nullable=True)
    pro_ipi_number = Column(String(255), nullable=True)
    
    # 5. Optional Fields
    phone_number = Column(String(50), nullable=True)
    address = Column(String(500), nullable=True)
    isrc_iswc = Column(String(255), nullable=True)
    
    # 6. Publisher Info
    has_publisher = Column(Boolean, default=False)
    publisher_name = Column(String(255), nullable=True)
    publisher_pro = Column(String(255), nullable=True)
    publisher_ipi_number = Column(String(255), nullable=True)

    # --- PDF Generation & License Certificate Fields ---
    # License Certificate Data
    license_id_formatted = Column(String(50), unique=True, nullable=True, index=True)  # e.g., BB-U-2025-00123
    pdf_generated_at = Column(DateTime(timezone=True), nullable=True)
    pdf_checksum = Column(String(64), nullable=True)  # SHA-256 hash of the PDF
    
    # Transaction/Payment Data (from Stripe session)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)
    transaction_id = Column(String(255), nullable=True)  # Stripe payment intent ID
    buyer_ip = Column(String(50), nullable=True)
    buyer_user_agent = Column(String(500), nullable=True)
    amount_paid = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True)
    discount_applied = Column(Float, nullable=True, default=0.0)
    payment_method = Column(String(100), nullable=True)
    
    # Add relationship to Order
    order = relationship("Order", backref="user_licenses")