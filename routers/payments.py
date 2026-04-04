from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
import os
from sqlalchemy.orm import Session

from models.user import Users
from schemas.payment import CheckoutRequest, CheckoutResponse
from utils import payment_service
from utils.order_service import OrderService
from utils.deps import get_db, get_current_user
import stripe

router = APIRouter(tags=["payments"])  


@router.post("/create-checkout-session", response_model=CheckoutResponse)
def create_checkout_session_endpoint(
    request_data: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    if not request_data.license_ids:
        raise HTTPException(status_code=400, detail="license_ids list cannot be empty.")
    paymentService = payment_service.PaymentService(db)
    try:
        session = paymentService.create_checkout_session(user=current_user, license_ids=request_data.license_ids, coupon_code=request_data.coupon_code)
        return CheckoutResponse(checkout_url=session.url)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception:
        raise HTTPException(status_code=500, detail="An internal error occurred while creating the payment session.")


@router.post("/webhook")
async def stripe_webhook_endpoint(
    request: Request,
    stripe_signature: str = Header(None),
    db: Session = Depends(get_db),
):
    payload = await request.body()
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    try:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=stripe_signature, secret=STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        return {"status": "error", "message": "Invalid signature"}

    try:
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            # Capture buyer metadata
            buyer_ip = request.headers.get("x-forwarded-for", request.client.host)
            user_agent = request.headers.get("user-agent", "Unknown")
            
            orderService = OrderService(db)
            orderService.process_order_and_send_email(session, buyer_ip, user_agent)
            db.commit()
        elif event['type'] == 'payment_intent.succeeded':
            pass
        elif event['type'] == 'charge.succeeded':
            pass
        else:
            pass
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": f"Webhook processing failed: {str(e)}"}
