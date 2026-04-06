from typing import List
import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from models.user import Users
from models.license import License
from models.music import Music
from models.coupans import Coupon
from schemas.coupon import CouponCreate, CouponResponse
from enums.couponenums import CouponScope
from utils.deps import get_db, admin_required
from stripe import stripe

router = APIRouter(tags=["coupons"])  


def format_license_name(license_type: str) -> str:
    type_map = {
        "leasing": "Leasing",
        "unlimited": "Unlimited",
        "exclusive": "Exclusive",
    }
    normalized = (license_type or "").strip().lower()
    return f"{type_map.get(normalized, normalized.title())} License"


@router.post("/admin/create/coupons", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
def create_coupon(request: CouponCreate, db: Session = Depends(get_db)):
    if db.query(Coupon).filter(Coupon.code == request.code).first():
        raise HTTPException(status_code=400, detail="Coupon code already exists.")
    if request.applies_to_entity == CouponScope.LICENSE and not request.applies_to_id:
        raise HTTPException(status_code=400, detail="applies_to_id (license_id) is required for a LICENSE-specific coupon.")
    try:
        stripe_coupon_params = {}
        if request.discount_type.value == "percent":
            stripe_coupon_params['percent_off'] = request.value
        elif request.discount_type.value == "fixed_amount":
            stripe_coupon_params['amount_off'] = int(request.value * 100)
            stripe_coupon_params['currency'] = 'eur'
        elif request.discount_type.value == "bulk_offer":
            # Stripe doesn't support B1G1, we use a 0% coupon as a placeholder
            stripe_coupon_params['percent_off'] = 0
        if request.max_redemptions:
            stripe_coupon_params['max_redemptions'] = request.max_redemptions
        stripe_coupon = stripe.Coupon.create(**stripe_coupon_params)
        promo_code_params = {'coupon': stripe_coupon.id, 'code': request.code}
        if request.expires_at:
            promo_code_params['expires_at'] = int(request.expires_at.timestamp())
        if request.max_redemptions == 1:
            promo_code_params['max_redemptions'] = 1
        stripe_promo_code = stripe.PromotionCode.create(**promo_code_params)
        new_coupon = Coupon(
            stripe_coupon_id=stripe_coupon.id,
            stripe_promotion_code_id=stripe_promo_code.id,
            code=request.code,
            discount_type=request.discount_type,
            value=request.value,
            buy_count=request.buy_count,
            get_count=request.get_count,
            is_active=request.is_active,
            applies_to_entity=request.applies_to_entity,
            applies_to_id=request.applies_to_id,
            max_redemptions=request.max_redemptions,
            expires_at=request.expires_at,
        )
        db.add(new_coupon)
        db.commit()
        db.refresh(new_coupon)
        return new_coupon
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")


@router.get("/licenses-for-coupons")
def get_licenses_for_coupons(db: Session = Depends(get_db), admin_user: Users = Depends(admin_required)):
    if not admin_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin role required.")
    try:
        licenses = db.query(License).join(Music).all()
        return [
            {
                "id": lic.id,
                "label": f"{lic.music.name} ({format_license_name(lic.license_type.value)})",
                "license_type": lic.license_type.value,
            }
            for lic in licenses
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve licenses: {str(e)}")


@router.get("/admin/coupons", response_model=List[CouponResponse])
@router.get("/admin/coupons/", response_model=List[CouponResponse], include_in_schema=False)
def get_all_coupons(db: Session = Depends(get_db)):
    try:
        coupons = db.query(Coupon).options(joinedload(Coupon.license).joinedload(License.music)).order_by(Coupon.id.desc()).all()
        return coupons
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve coupons: {str(e)}")


@router.put("/admin/coupons/{coupon_id}/toggle-status", response_model=CouponResponse)
def toggle_coupon_status(coupon_id: int, db: Session = Depends(get_db)):
    db_coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not db_coupon:
        raise HTTPException(status_code=404, detail="Coupon not found.")
    new_status = not db_coupon.is_active
    try:
        stripe.PromotionCode.modify(db_coupon.stripe_promotion_code_id, active=new_status)
        db_coupon.is_active = new_status
        db.commit()
        db.refresh(db_coupon)
        return db_coupon
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
