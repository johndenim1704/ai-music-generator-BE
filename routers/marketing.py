import os
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session

from models.user import Users
from models.marketing import MarketingAd
from schemas.campaignrequest import CampaignRequest
from schemas.marketing import MarketingAdRead, AdCategory, AdItem
from utils.marketing_service import MarketingService
from utils.deps import admin_required, get_db
from utils.s3_manager import S3Manager
from typing import List
import uuid

router = APIRouter(tags=["marketing"])  

marketing_client = MarketingService()
s3_manager = S3Manager()
BREVO_ALL_USERS_LIST_ID = int(os.getenv("BREVO_MAIN_LIST_ID", "2"))


@router.post("/admin/marketing/send-campaign", status_code=status.HTTP_200_OK)
def send_marketing_campaign(
    campaign_data: CampaignRequest,
    current_admin_user: Users = Depends(admin_required),
):
    if not current_admin_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin role required.")
    try:
        marketing_client.send_marketing_campaign(
            campaign_name=campaign_data.campaign_name,
            subject=campaign_data.subject,
            html_content=campaign_data.html_content,
            list_id=BREVO_ALL_USERS_LIST_ID,
        )
        return {
            "status": "success",
            "message": f"Campaign '{campaign_data.campaign_name}' has been successfully queued for sending.",
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/admin/marketing/sync-users", status_code=status.HTTP_200_OK)
def sync_users_to_brevo_list(
    db: Session = Depends(get_db),
    current_admin_user: Users = Depends(admin_required),
):
    if not current_admin_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin role required.")
    try:
        users = db.query(Users).all()
        if not users:
            return {"status": "success", "message": "No users found in the database to sync."}
        success_count = 0
        failure_count = 0
        for user in users:
            try:
                marketing_client.add_contact_to_list(
                    email=user.email,
                    list_id=BREVO_ALL_USERS_LIST_ID,
                    first_name=user.name,
                )
                success_count += 1
            except Exception:
                failure_count += 1
        return {
            "status": "success",
            "message": f"Sync complete. Added: {success_count}, Failed: {failure_count}.",
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/marketing/ads", response_model=List[MarketingAdRead])
def get_dashboard_ads(db: Session = Depends(get_db)):
    """
    Get all dashboard advertisements as a flat list
    """
    try:
        ads = db.query(MarketingAd).all()
        return ads
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/admin/marketing/ads", response_model=MarketingAdRead, status_code=status.HTTP_201_CREATED)
async def create_marketing_ad(
    category_name: str = Form(...),
    category_description: str = Form(None),
    item_name: str = Form(...),
    item_description: str = Form(None),
    image_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin_user: Users = Depends(admin_required),
):
    if not current_admin_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin role required.")
    try:
        # Upload image to S3
        file_extension = os.path.splitext(image_file.filename)[1]
        s3_filename = f"ads/{uuid.uuid4().hex}{file_extension}"
        # Use upload_file_from_uploadfile for FastAPI UploadFile objects
        image_url = await s3_manager.upload_file_from_uploadfile(image_file, s3_key=s3_filename)
            
        if not image_url:
            raise Exception("Failed to upload image to S3")

        new_ad = MarketingAd(
            category_name=category_name,
            category_description=category_description,
            item_name=item_name,
            item_description=item_description,
            image_url=image_url
        )
        db.add(new_ad)
        db.commit()
        db.refresh(new_ad)
        return new_ad
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/admin/marketing/ads/{ad_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_marketing_ad(
    ad_id: int,
    db: Session = Depends(get_db),
    current_admin_user: Users = Depends(admin_required),
):
    if not current_admin_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin role required.")
    try:
        ad = db.query(MarketingAd).filter(MarketingAd.id == ad_id).first()
        if not ad:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ad not found")
        
        # Clean up S3 image
        if ad.image_url:
            try:
                s3_key = s3_manager.get_key_from_url(ad.image_url)
                s3_manager.delete_file(s3_key)
            except Exception as e:
                print(f"⚠️ Failed to delete S3 image: {e}")

        db.delete(ad)
        db.commit()
        return None
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
