from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from models.user import Users
from models.offer import Offer
from models.license import License
from schemas.offer import CreateOfferRequest, CounterOfferRequest
from utils.offer_service import OfferService
from utils.deps import get_db, get_current_user, admin_required
from utils import payment_service
from stripe import stripe
from enums import offerstatus

router = APIRouter(tags=["offers"])  


@router.post("/offers/setup-intent")
def create_setup_intent_endpoint(db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    customer_id = payment_service.PaymentService(db)._get_or_create_stripe_customer(current_user)
    setup_intent = stripe.SetupIntent.create(customer=customer_id, usage='off_session')
    return {"client_secret": setup_intent.client_secret}


@router.post("/offers", status_code=201)
def create_offer_endpoint(request: CreateOfferRequest, db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    try:
        offer_service_instance = OfferService(db)
        offer = offer_service_instance.create_offer(
            user=current_user,
            license_id=request.license_id,
            amount=request.amount,
            payment_method_id=request.payment_method_id,
        )
        return {"status": "success", "message": "Offer submitted for review.", "offer_id": offer.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/offers/{offer_id}/accept")
def admin_accept_offer(offer_id: int, db: Session = Depends(get_db), current_admin_user: Users = Depends(admin_required)):
    if not current_admin_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin role required.")
    offer_service_instance = OfferService(db)
    try:
        offer = offer_service_instance.accept_offer(offer_id)
        return {
            "status": "success",
            "message": "Offer accepted and payment processed INSTANTLY.",
            "offer_id": offer.id,
            "offer_status": offer.status.value,
            "payment_intent_id": offer.stripe_payment_intent_id,
            "final_amount": offer.counter_offer_amount if offer.counter_offer_amount else offer.offered_amount,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except stripe.error.CardError as e:
        raise HTTPException(status_code=402, detail=f"Payment Declined: {e.user_message}")
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=402, detail=f"Payment Processing Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.post("/admin/offers/{offer_id}/reject")
def admin_reject_offer(offer_id: int, db: Session = Depends(get_db)):
    offer_service_instance = OfferService(db)
    try:
        offer = offer_service_instance.reject_offer(offer_id)
        return {"status": "success", "message": "Offer rejected.", "offer_status": offer.status.value}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/admin/offers/{offer_id}/counter")
def admin_counter_offer(offer_id: int, request: CounterOfferRequest, db: Session = Depends(get_db)):
    offer_service_instance = OfferService(db)
    try:
        offer = offer_service_instance.counter_offer(offer_id, request.counter_amount)
        return {"status": "success", "message": "Counter-offer sent to user.", "offer_status": offer.status.value}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/admin/offers")
def get_all_offers(db: Session = Depends(get_db), current_admin_user: Users = Depends(admin_required)):
    if not current_admin_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin role required.")
    try:
        offers = db.query(Offer).options(joinedload(Offer.user), joinedload(Offer.license).joinedload(License.music)).all()
        if not offers:
            raise HTTPException(status_code=404, detail="No offers found")
        offers_with_details = []
        for offer in offers:
            offer_data = {k: v for k, v in offer.__dict__.items() if k not in ['_sa_instance_state', 'stripe_payment_method_id', 'stripe_customer_id']}
            if offer.user:
                offer_data["user"] = {"id": offer.user.id, "name": offer.user.name, "email": offer.user.email, "created_at": offer.user.created_at}
            if offer.license and offer.license.music:
                music = offer.license.music
                offer_data["music"] = {"id": music.id, "name": music.name, "artist": music.artist, "image_url": music.cover_image_url, "license_type": offer.license.license_type.value, "license_price": offer.license.price}
            offers_with_details.append(offer_data)
        return offers_with_details
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve offers: {str(e)}")


@router.get("/admin/offers/pending")
async def get_all_pending_offers(db: Session = Depends(get_db), current_admin_user: Users = Depends(admin_required)):
    try:
        if not current_admin_user:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin role required.")
        offers = (
            db.query(Offer)
            .options(joinedload(Offer.user), joinedload(Offer.license).joinedload(License.music))
            .filter(Offer.status == offerstatus.OfferStatus.PENDING)
            .all()
        )
        if not offers:
            raise HTTPException(status_code=404, detail="No pending offers found")
        offers_with_details = []
        for offer in offers:
            offer_data = {k: v for k, v in offer.__dict__.items() if k not in ['_sa_instance_state', 'stripe_payment_method_id', 'stripe_customer_id']}
            if offer.user:
                offer_data["user"] = {"id": offer.user.id, "name": offer.user.name, "email": offer.user.email, "created_at": offer.user.created_at}
            if offer.license and offer.license.music:
                music = offer.license.music
                offer_data["music"] = {"id": music.id, "name": music.name, "artist": music.artist, "image_url": music.cover_image_url, "license_type": offer.license.license_type.value, "license_price": offer.license.price}
            offers_with_details.append(offer_data)
        return offers_with_details
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve pending offers: {str(e)}")
