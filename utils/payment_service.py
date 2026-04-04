import stripe
from typing import List, Optional
from sqlalchemy.orm import Session
import os
import traceback
from models.user import Users
from models.license import License
from models.coupans import Coupon
from enums.couponenums import CouponScope


stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL")


class PaymentService:
    """
    Handles Stripe Checkout session creation
    """
    def __init__(self, db: Session):
        self.db = db

    def _get_or_create_stripe_customer(self, user: Users) -> str:
        """
        Creates or retrieves a Stripe customer for the given user.
        Handles cases: new users, existing valid customers, and invalid/deleted customers.
        """
        # If user has a stripe_customer_id, verify it exists in Stripe
        if user.stripe_customer_id:
            try:
                # Try to retrieve the customer from Stripe to verify it exists
                customer = stripe.Customer.retrieve(user.stripe_customer_id)
                print(f"Using existing Stripe customer: {customer.id}")
                return user.stripe_customer_id
            except stripe.error.InvalidRequestError as e:
                # Customer doesn't exist in Stripe (deleted or invalid)
                print(f"Stripe customer {user.stripe_customer_id} not found: {str(e)}. Creating new customer.")
                # Clear the invalid customer ID so we create a new one
                user.stripe_customer_id = None
            except Exception as e:
                # Any other Stripe error - log it and create new customer
                print(f"Error retrieving Stripe customer {user.stripe_customer_id}: {str(e)}. Creating new customer.")
                user.stripe_customer_id = None

        # Validate required fields for customer creation
        if not user.email:
            raise ValueError("User email is required for Stripe customer creation")
        
        # Use name if available, otherwise use email as fallback
        customer_name = user.name if user.name else user.email.split('@')[0]

        # Create customer with minimal required data
        # Note: Address fields don't exist in Users model, so we only use email and name
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=customer_name,
                metadata={
                    'app_user_id': str(user.id),
                    'created_from': 'checkout_session'
                }
            )
            print(f"Created new Stripe customer: {customer.id} for user {user.id}")
            
            # Save the customer ID to the database
            user.stripe_customer_id = customer.id
            self.db.commit()
            self.db.refresh(user)
            
            return customer.id
            
        except stripe.error.StripeError as e:
            # Handle any Stripe-specific errors
            print(f"Stripe error creating customer: {str(e)}")
            raise ValueError(f"Failed to create Stripe customer: {str(e)}")
        except Exception as e:
            # Handle any other unexpected errors
            print(f"Unexpected error creating Stripe customer: {str(e)}")
            raise ValueError(f"Failed to create Stripe customer: {str(e)}")

    def create_checkout_session(self, user: Users, license_ids: List[int], coupon_code: Optional[str] = None):
        """
        Creates a Stripe checkout session for the user to purchase licenses.
        """
        try:
            # Get or create Stripe customer
            customer_id = self._get_or_create_stripe_customer(user)
            
            # Fetch the licenses from the database
            db_licenses = self.db.query(License).filter(License.id.in_(license_ids)).all()

            if not db_licenses or len(db_licenses) != len(license_ids):
                raise ValueError("One or more license IDs are invalid.")
            
            # Build session parameters
            session_params = {
                'customer': customer_id,
                'payment_method_types': ['card'],
                'line_items': [],   
                'mode': 'payment',
                'success_url': f"{FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
                'cancel_url': f"{FRONTEND_URL}/payment/canceled",
                'metadata': {'app_user_id': str(user.id)},
                'payment_method_options': {
                    'card': {
                        'request_three_d_secure': 'automatic'
                    }
                }
            }

            # Handle coupon codes
            if coupon_code:
                db_coupon = self.db.query(Coupon).filter(
                    Coupon.code == coupon_code, 
                    Coupon.is_active == True
                ).first()
                
                if not db_coupon:
                    raise ValueError("Invalid or inactive coupon code.")
                
                # Validate if the coupon is license-specific
                if db_coupon.applies_to_entity == CouponScope.LICENSE:
                    license_id_for_coupon = db_coupon.applies_to_id
                    
                    if license_id_for_coupon not in license_ids:
                        raise ValueError(f"Coupon '{coupon_code}' is not valid for the licenses in your cart.")
                
                session_params['discounts'] = [{'promotion_code': db_coupon.stripe_promotion_code_id}]
            else:
                # Allow users to enter promotion codes at checkout
                session_params['allow_promotion_codes'] = True

            # Add line items for each license
            for lic in db_licenses:
                session_params['line_items'].append({
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {
                            'name': f"{lic.music.name} - {lic.license_type.value.title()} License",
                            'metadata': {
                                'license_id': str(lic.id),
                                'music_id': str(lic.music_id)
                            }
                        },
                        'unit_amount': int(lic.price * 100),
                    },
                    'quantity': 1,
                })
            
            # Create the checkout session
            checkout_session = stripe.checkout.Session.create(**session_params)
            print(f"Created checkout session: {checkout_session.id} for user {user.id}")
            return checkout_session

        except ValueError as ve:
            # Re-raise ValueError as-is (these are expected user errors)
            print(f"PaymentService ValueError: {str(ve)}")
            raise
        except stripe.error.StripeError as se:
            # Handle Stripe-specific errors
            print(f"PaymentService Stripe Error: {str(se)}")
            raise ValueError(f"Payment processing error: {str(se)}")
        except Exception as e:
            # Handle any other unexpected errors
            print(f"PaymentService Unexpected Error: {str(e)}")
            traceback.print_exc()
            raise ValueError(f"An unexpected error occurred: {str(e)}")