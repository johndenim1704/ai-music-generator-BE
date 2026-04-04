from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import os
import shutil

from models.user import Users
from utils.deps import get_db, get_current_user, admin_required
from stripe import stripe
from enums.licensetypesenum import LicenseTypesEnum
from models.userlicense import UserLicense
from models.license import License
from models.music import Music
from models.order import Order
from schemas.admin import AdminPurchaseRead

router = APIRouter(tags=["admin"])  


@router.get("/admin/total-sales")
def get_total_sales(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    admin_user: Users = Depends(admin_required),
):
    if not admin_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin role required.")
    try:
        charges = stripe.Charge.list(limit=100)
        successful_charges = [c for c in charges.data if c['status'] == 'succeeded']
        total_amount_cents = sum(c['amount'] for c in successful_charges)
        total_amount = total_amount_cents / 100
        return {"total_sales": total_amount}
    except Exception as e:
        return {"error": str(e)}


@router.put("/admin/license-templates")
async def update_license_template(
    license_type: LicenseTypesEnum = Form(...),
    file: UploadFile = File(...),
    current_user: Users = Depends(admin_required),
):
    """
    Update the PDF template for a specific license type.
    Overwrites the existing file in backend/pdf_templates/.
    """
    if not current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin role required.")

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF allowed.")

    # Determine filename based on license type
    # Must match filenames expected by PDFGenerator._get_template_path
    filename_map = {
        LicenseTypesEnum.leasing: "leasing_license_2025.pdf",
        LicenseTypesEnum.exclusive: "exclusive_license_2025.pdf",
        LicenseTypesEnum.unlimited: "unlimited_license_2025.pdf",
    }
    
    target_filename = filename_map.get(license_type)
    if not target_filename:
        raise HTTPException(status_code=400, detail="Invalid license type")

    # Path to pdf_templates directory
    # Assuming routers/admin.py is in backend/routers/, so templates are in backend/pdf_templates/
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base_dir, "pdf_templates")
    
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
        
    file_path = os.path.join(templates_dir, target_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {
            "status": "success",
            "message": f"Template for {license_type.value} updated successfully.",
            "filename": target_filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")


@router.get("/admin/purchases", response_model=list[AdminPurchaseRead])
def get_all_purchases(
    db: Session = Depends(get_db),
    admin_user: Users = Depends(admin_required),
):
    """
    Get all purchases with detailed information for admin.
    """
    try:
        # Join UserLicense with Users, License, Music, and Order to get all required info
        purchases = (
            db.query(
                Users.name.label("user_name"),
                Users.email.label("user_email"),
                Music.name.label("song_name"),
                UserLicense.amount_paid,
                UserLicense.currency,
                UserLicense.purchase_date,
                License.license_type,
                UserLicense.order_id,
                UserLicense.transaction_id,
                Order.status.label("order_status")
            )
            .join(Users, UserLicense.user_id == Users.id)
            .join(License, UserLicense.license_id == License.id)
            .join(Music, License.music_id == Music.id)
            .outerjoin(Order, UserLicense.order_id == Order.id)
            .order_by(UserLicense.purchase_date.desc())
            .all()
        )

        # Convert to list of dicts for Pydantic validation
        result = []
        for p in purchases:
            result.append({
                "user_name": p.user_name,
                "user_email": p.user_email,
                "song_name": p.song_name,
                "amount_paid": p.amount_paid or 0.0,
                "currency": p.currency,
                "purchase_date": p.purchase_date,
                "license_type": p.license_type.value if hasattr(p.license_type, 'value') else str(p.license_type),
                "order_id": p.order_id,
                "transaction_id": p.transaction_id,
                "status": p.order_status.value if hasattr(p.order_status, 'value') else str(p.order_status) if p.order_status else "N/A"
            })

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch purchases: {str(e)}")
