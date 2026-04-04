from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.order import Order, OrderStatus, OrderOrigin
from models.orderItem import OrderItem
from models.order import Order
from models.user import Users
from models.license import License
from models.userlicense import UserLicense
import stripe
import os
from utils.s3_manager import S3Manager

s3 = S3Manager()


def send_purchase_confirmation_email(user_email: str, user_name: str, order_id: int, purchased_items: list):
    """
    Sends a confirmation email with download links to the user.
    """
    print("--- Sending Purchase Confirmation Email ---")
    print(f"To: {user_email} (Name: {user_name})")
    print(f"Subject: Your Bujaa Beats Order Confirmation (#{order_id})")
    print("Hi! Thank you for your purchase. You can download your files using the links below:")
    
    for item in purchased_items:
        print(f"\n- Item: {item['name']}")
        if item.get('mp3_url'): print(f"  MP3 Download: {item['mp3_url']}")
        if item.get('wav_url'): print(f"  WAV Download: {item['wav_url']}")
        if item.get('stems_zip_url'): print(f"  Stems (ZIP) Download: {item['stems_zip_url']}")
        
    print("\nThank you for choosing Bujaa Beats!")
    print("--- Email Sent ---")


class OrderService:
    """
    Handles order fulfillment after payment
    """
    def __init__(self, db: Session):
        self.db = db
    # 
    # ------------- Below are the temperary function created for handleing the order confirmation email ---------
    # NOTE: Below funcions are not completed written only for testing
    def _send_confirmation_email(self, user_email: str, user_name: str, order_id: int, items: list):
        """Mock email sender - replace with your actual implementation"""
        print(f"\n=== SENDING EMAIL TO {user_email} ===")
        print(f"Subject: Order #{order_id} Confirmation")
        print(f"Hi {user_name}, thanks for your purchase!")
        for item in items:
            print(f"\n- {item['name']}")
            print(f"  MP3: {item.get('mp3_url', 'N/A')}")
            print(f"  WAV: {item.get('wav_url', 'N/A')}")
            print(f"  Stems: {item.get('stems_zip_url', 'N/A')}")
        print("\n=== EMAIL SENT ===\n")

    def _prepare_email_data(self, order: Order):
      
        email_items = []
        for item in order.order_items:
            music = item.license.music
            zip_url = None
            
            # Logic: If form not filled, do NOT send zip_url.
            # Initially, form is never filled.
            
            email_items.append({
                'name': item.item_description,
                'zip_download_url': None, # Explicitly None to force user to go to dashboard
                'requires_form': True 
            })
        return email_items 

    def _extract_payment_method(self, session_data: dict) -> str:
        """Extract payment method string from session data"""
        try:
            if 'payment_method_types' in session_data and session_data['payment_method_types']:
                return session_data['payment_method_types'][0].title()
            return 'Card'
        except:
            return 'Card'
  
    def create_order_from_session(self, session_data: dict, buyer_ip: str = None, user_agent: str = None):
        """
        Create an order from a Stripe checkout session with proper transaction handling.
        
        Args:
            session_data: Dictionary containing Stripe session data
            buyer_ip: IP address of the buyer
            user_agent: User agent string of the buyer
            
        Returns:
            Order: The created order object
            
        Raises:
            ValueError: If required data is missing or invalid
            StripeError: If there's an issue with Stripe API
            SQLAlchemyError: If there's a database operation failure
        """
        try:
                # Enrich session data if needed
                if 'line_items' not in session_data or 'data' not in session_data['line_items']:
                    session_data = stripe.checkout.Session.retrieve(
                        session_data['id'],
                        expand=['line_items.data.price.product']
                    ).to_dict()
                
                # Validate required metadata
                if 'metadata' not in session_data or 'app_user_id' not in session_data['metadata']:
                    raise ValueError("Missing user ID in session metadata")
                    
                user_id = int(session_data['metadata']['app_user_id'])
                user = self.db.query(Users).get(user_id)
                if not user:
                    raise ValueError(f"User {user_id} not found")

                # Create order
                new_order = Order(
                    user_id=user_id,
                    stripe_payment_intent_id=session_data.get('payment_intent'),
                    status=OrderStatus.COMPLETED,
                    origin=OrderOrigin.DIRECT_PURCHASE,
                    total_amount=session_data['amount_total'] / 100.0,
                    currency=session_data['currency']
                )
                self.db.add(new_order)
                self.db.flush()

                # Process line items
                for item in session_data['line_items']['data']:
                    product_meta = item['price']['product']['metadata']
                    license_id = int(product_meta['license_id'])
                    
                    license = self.db.query(License).get(license_id)
                    if not license:
                        raise ValueError(f"License {license_id} not found")
                    
                    # Create order item
                    self.db.add(OrderItem(
                        order_id=new_order.id,
                        license_id=license_id,
                        item_description=item['description'],
                        price_at_purchase=item['price']['unit_amount'] / 100.0
                    ))
                    
                    # Assign license to user with transaction data
                    user_license = UserLicense(
                        user_id=user_id,
                        license_id=license_id,
                        order_id=new_order.id,
                        transaction_id=session_data.get('payment_intent'),
                        buyer_ip=buyer_ip,
                        buyer_user_agent=user_agent,
                        amount_paid=item['price']['unit_amount'] / 100.0,
                        currency=session_data['currency'],
                        payment_method=self._extract_payment_method(session_data)
                    )
                    self.db.add(user_license)

                # Prepare email data (inside transaction to ensure order is available)
                email_data = self._prepare_email_data(new_order)
                
                # Return both order and email data
                return new_order, email_data, user

        except ValueError as e:
            # logging.error(f"Validation error in OrderService: {str(e)}")
            raise
        except stripe.error.StripeError as e:
            # logging.error(f"Stripe API error in OrderService: {str(e)}")
            raise
        except SQLAlchemyError as e:
            # logging.error(f"Database error in OrderService: {str(e)}")
            self.db.rollback()
            raise
        except Exception as e:
            # logging.error(f"Unexpected error in OrderService: {str(e)}")
            self.db.rollback()
            raise

    def process_order_and_send_email(self, session_data: dict, buyer_ip: str = None, user_agent: str = None):
        """
        Process an order from session data and send confirmation email.
        
        Args:
            session_data: Dictionary containing Stripe session data
            buyer_ip: IP address of the buyer
            user_agent: User agent string of the buyer
            
        Returns:
            Order: The created order object
        """
        try:
            # Create order and get related data
            order, email_data, user = self.create_order_from_session(session_data, buyer_ip, user_agent)
            
            # Send confirmation email (outside transaction)
            self._send_confirmation_email(
                user_email=user.email,
                user_name=user.name,
                order_id=order.id,
                items=email_data
            )
            
            # logging.info(f"Order {order.id} created successfully and email sent!")
            return order
            
        except Exception as e:
            # logging.error(f"Failed to process order and send email: {str(e)}")
            raise