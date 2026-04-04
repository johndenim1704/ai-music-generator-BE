from sqlalchemy.orm import Session
from models.offer import Offer
from models.user import Users
from models.license import License
from utils.order_service import OrderService
from enums import offerstatus as OfferStatus
from utils import payment_service,email_service
import stripe
import os

FRONTEND_URL = os.getenv("FRONTEND_URL")  

class OfferService:
    def __init__(self, db: Session):
        self.db = db
        self.order_service = OrderService(db)
        self.email_service = email_service.EmailService()


    def create_offer(self, user: Users, license_id: int, amount: float, payment_method_id: str) -> Offer:
        # 1. Ensure the license is an Exclusive License that allows offers
        license = self.db.query(License).filter(License.id == license_id).first()
        if not license or license.license_type.value != 'exclusive': # Or whatever you call it
            raise ValueError("Offers can only be made on Exclusive Licenses.")

        # 2. Get or create a Stripe Customer
        customer_id = payment_service.PaymentService(self.db)._get_or_create_stripe_customer(user)

        # 3. Attach the payment method to the customer to save it for later
        stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
        print("offer is created")
        # 4. Create the offer record in the database
        new_offer = Offer(
            user_id=user.id,
            license_id=license_id,
            offered_amount=amount,
            currency='eur', # or from request
            stripe_customer_id=customer_id,
            stripe_payment_method_id=payment_method_id,
            status=OfferStatus.OfferStatus.PENDING,  
        )
        self.db.add(new_offer)
        self.db.commit()

        # TODO: Send email notification to Admin

        return new_offer
    
    def _fulfill_accepted_offer(self, offer, payment_intent):
        """Create order and fulfill the license after successful payment"""
        # print(payment_intent.keys() , payment_intent.values())
        try:
            # Create order through OrderService
            order_data = {
                'id': payment_intent.id,
                'amount_total': payment_intent.amount,
                'currency': payment_intent.currency,
                'payment_intent': payment_intent.id,
                'metadata': {
                    'app_user_id': str(offer.user_id),
                    'offer_id': str(offer.id)
                },
                'line_items': {
                    'data': [{
                        'description': f"Exclusive License - {offer.license.music.name}",
                        'price': {
                            'unit_amount': payment_intent.amount,
                            'product': {
                                'metadata': {
                                    'license_id': str(offer.license_id)
                                }
                            }
                        }
                    }]
                }
            }
            

            print(order_data , "order daya")
            # Create order
            order,email_data, user  = self.order_service.create_order_from_session(order_data)
            offer.order_id = order.id
            
            # logger.info(f"Order {order.id} created for accepted offer {offer.id}")
            
        except Exception as e:
            # logger.error(f"Error fulfilling offer {offer.id}: {str(e)}")
            raise ValueError(f"Error processing license fulfillment: {str(e)}")
        
    
    def _send_offer_accepted_email(self, offer: Offer):
        """Send confirmation email to user"""
        user = offer.user
        license = offer.license
        final_amount = offer.counter_offer_amount if offer.counter_offer_amount else offer.offered_amount
        
        print(f"Sending offer accepted email to {user.email} for offer {offer.id} with amount ${final_amount}")
        # logger.info(f"=== SENDING OFFER ACCEPTED EMAIL ===")
        # logger.info(f"To: {user.email}")
        # logger.info(f"Subject: Your Offer Has Been Accepted!")
        # logger.info(f"Hi {user.name},")
        # logger.info(f"Great news! Your offer of ${final_amount} for '{license.music.name}' has been accepted.")
        # logger.info(f"Payment has been processed and your Exclusive License is now available.")
        # logger.info(f"=== EMAIL SENT ===")


    def accept_offer(self, offer_id: int) -> Offer:
        """
        Admin accepts the offer and processes payment
        """
        print(f"Accepting offer with ID: {offer_id}")
        offer = self.db.query(Offer).get(offer_id)
        
        if not offer or offer.status != OfferStatus.OfferStatus.PENDING:
            raise ValueError("Offer not found or not in a pending state.")

        # Determine the final amount (original offer or counter offer)
        final_amount = offer.counter_offer_amount if offer.counter_offer_amount else offer.offered_amount
        payment_description = f"Payment for accepted offer #{offer.id}"

        print( offer.__dict__, "asdas" , offer.stripe_payment_method_id , offer.currency , offer.stripe_customer_id, final_amount, payment_description)

        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=int(final_amount * 100),
                currency=offer.currency,
                customer=offer.stripe_customer_id,
                payment_method=offer.stripe_payment_method_id,
                description=payment_description,
                confirm=True,
                off_session=True,  
                automatic_payment_methods={
                    "enabled": True,
                    "allow_redirects": "never"
                },
                
                metadata={
                    "offer_id": str(offer.id),
                    "user_id": str(offer.user_id),
                    "license_id": str(offer.license_id),
                    "type": "offer_acceptance"
                },
                shipping= {
                    # "name": offer.user.name if offer.user.name else "Anonymous",
                    # "address": {
                        
                    #     "line1": offer.user.address if offer.user.address else "N/A", 
                    #     "postal_code": offer.user.zipcode if offer.user.zipcode else "N/A",
                    #     "city": offer.user.city if offer.user.city else "N/A",
                    #     "state": offer.user.state if offer.user.state else "N/A",
                    #     "country": offer.user.country if offer.user.country else "N/A",

                    # }
                    "name": "User",
                    "address": {
                        
                        "line1": "N/A", 
                        "postal_code": "44444",
                        "city": "Mumbai",
                        "state": "Maharashtra",
                        "country": "IN",

                    }
                },
            
            )

            # Handle different payment intent statuses
            if payment_intent.status == 'succeeded':
                offer.status = OfferStatus.OfferStatus.ACCEPTED
                offer.stripe_payment_intent_id = payment_intent.id
                
                self._fulfill_accepted_offer(offer, payment_intent)
                
                self.db.commit()
                print(f"Offer {offer_id} accepted and payment processed successfully")
                
                # Send success email to user
                # self._send_offer_accepted_email(offer)
                # email_service.EmailService(self.db).send_offer_accepted(offer)
                # self.email_service.send_counter_offer
                self.email_service.send_offer_accepted(offer)
                return offer
            elif payment_intent.status == 'requires_action':
                # Payment needs additional authentication
                offer.status = OfferStatus.OfferStatus.REQUIRES_ACTION
                offer.stripe_payment_intent_id = payment_intent.id
                self.db.commit()
                raise ValueError("Payment requires additional authentication from customer") 
            else:
                # Payment failed for other reasons
                offer.status = OfferStatus.OfferStatus.PAYMENT_FAILED
                self.db.commit()
                raise ValueError(f"Payment failed with status: {payment_intent.status}")
        except stripe.error.CardError as e:
            # Card declined, insufficient funds, etc.
            offer.status = OfferStatus.OfferStatus.PAYMENT_FAILED
            self.db.commit()
            print(f"Card error: {e.user_message}")
            raise ValueError(f"Payment declined: {e.user_message}")
            
        except stripe.error.AuthenticationError as e:
            # Stripe API authentication issues
            print(f"Stripe authentication error: {str(e)}")
            raise ValueError("Payment processing service error")
            
        except stripe.error.APIConnectionError as e:
            # Network issues with Stripe
            print(f"Stripe connection error: {str(e)}")
            raise ValueError("Payment processing temporarily unavailable")
            
        except stripe.error.StripeError as e:
            # Other Stripe errors
            offer.status = OfferStatus.OfferStatus.PAYMENT_FAILED
            self.db.commit()
            print(f"Stripe error: {str(e)}")
            raise ValueError(f"Payment processing error: {str(e)}")

    def reject_offer(self, offer_id: int) -> Offer:
        offer = self.db.query(Offer).get(offer_id)
        if not offer or offer.status != OfferStatus.OfferStatus.PENDING:
            raise ValueError("Offer not found or not in a pending state.")
            
        offer.status = OfferStatus.OfferStatus.REJECTED
        self.db.commit()
        
        # TODO: Send "Offer Rejected" email to the user
        self.email_service.send_offer_rejected(offer)
        return offer

    def counter_offer(self, offer_id: int, counter_amount: float) -> Offer:
        offer = self.db.query(Offer).get(offer_id)
        if not offer or offer.status != OfferStatus.OfferStatus.PENDING:
            raise ValueError("Offer not found or not in a pending state.")

        # Create a one-time payment link for the counter-offer
        checkout_session = stripe.checkout.Session.create(
            customer=offer.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': offer.currency,
                    'product_data': {
                        'name': f"Counter-offer for {offer.license.music.name} - Exclusive License",
                        'metadata': { 
                            'license_id': str(offer.license_id)
                        }
                    },
                    'unit_amount': int(counter_amount * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{FRONTEND_URL}/payment/success",
            cancel_url=f"{FRONTEND_URL}/payment/canceled",
             metadata={
                'offer_id': offer.id,
                'app_user_id': offer.user_id 
            }
            
        )
        
        offer.status = OfferStatus.OfferStatus.COUNTER_OFFERED
        offer.counter_offer_amount = counter_amount
        self.db.commit()
        self.email_service.send_counter_offer(offer, checkout_session.url)

        
        # TODO: Send "Counter-offer" email to the user with the checkout_session.url
        print(f"Send this link to the user: {checkout_session.url}")
        
        return offer
