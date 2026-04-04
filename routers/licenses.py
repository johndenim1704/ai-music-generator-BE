from typing import Optional, List
import json
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from models.user import Users
from models.music import Music
from models.license import License
from models.userlicense import UserLicense
from models.order import Order
from schemas.license import LicenseResponse
from schemas.user_license import UserLicenseUpdate, UserLicenseRead
from utils.s3_manager import S3Manager
from utils.license_service import LicenseService
from utils.deps import get_db, get_current_user, admin_required

router = APIRouter(tags=["licenses"])  

s3_manager = S3Manager()


@router.get("/licenses/{music_id}", response_model=List[LicenseResponse])
async def get_licenses(music_id: int, db: Session = Depends(get_db)):
    try:
        licenses = db.query(License).filter(License.music_id == music_id).all()
        if not licenses:
            raise HTTPException(status_code=404, detail="No licenses found for this music track")
        return licenses
    except HTTPException as he:
        raise HTTPException(status_code=he.status_code, detail=he.detail)


@router.post("/music/{music_id}/licenses/bulk", response_model=List[LicenseResponse], status_code=status.HTTP_201_CREATED)
async def create_bulk_licenses(
    music_id: int,
    licenses_json: str = Form(...),
    zip_files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_admin_user: Users = Depends(admin_required),
):
    if not current_admin_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin role required.")
    try:
        music = db.query(Music).get(music_id)
        if not music:
            raise HTTPException(status_code=404, detail="Music not found")
        try:
            licenses_data = json.loads(licenses_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format for licenses.")

        file_map = {file.filename: file for file in zip_files} if zip_files else {}
        created_licenses = []
        for license_info in licenses_data:
            license_type = license_info.get("license_type")
            new_license = License(
                music_id=music_id,
                license_type=license_type,
                price=license_info.get("price"),
                terms=license_info.get("terms"),
            )
            db.add(new_license)
            db.flush()
            expected_filename = license_info.get("zip_filename")
            if expected_filename and expected_filename in file_map:
                zip_file = file_map[expected_filename]
                s3_key = s3_manager.build_license_zip_key(
                    license_id=new_license.id,
                    music_name=music.name,
                    license_type_value=license_type,
                )
                await s3_manager.upload_file_from_uploadfile(
                    upload_file=zip_file,
                    s3_key=s3_key,
                    extra_args={"ContentType": "application/zip", "ServerSideEncryption": "AES256"},
                )
                new_license.zip_s3_key = s3_key
            created_licenses.append(new_license)
        db.commit()
        for lic in created_licenses:
            db.refresh(lic)
        return created_licenses
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create licenses: {str(e)}")


@router.put("/licenses/{license_id}", response_model=LicenseResponse, status_code=status.HTTP_200_OK)
async def update_license(
    license_id: int,
    price: Optional[float] = Form(None),
    terms: Optional[str] = Form(None),
    zip_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_admin_user: Users = Depends(admin_required),
):
    if not current_admin_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin role required.")

    license_to_update = db.query(License).filter(License.id == license_id).first()
    if not license_to_update:
        raise HTTPException(status_code=404, detail="License not found")

    try:
        if price is not None:
            license_to_update.price = price
        if terms is not None:
            license_to_update.terms = terms
        if zip_file:
            music = license_to_update.music
            if not music:
                raise HTTPException(status_code=500, detail="Data integrity error: License is not associated with any music.")
            if license_to_update.zip_s3_key:
                s3_manager.delete_file(license_to_update.zip_s3_key)
            new_s3_key = s3_manager.build_license_zip_key(
                license_id=license_to_update.id,
                music_name=music.name,
                license_type_value=license_to_update.license_type.value,
            )
            await s3_manager.upload_file_from_uploadfile(
                upload_file=zip_file,
                s3_key=new_s3_key,
                extra_args={"ContentType": "application/zip", "ServerSideEncryption": "AES256"},
            )
            license_to_update.zip_s3_key = new_s3_key
        db.commit()
        db.refresh(license_to_update)
        return license_to_update
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update license: {str(e)}")


@router.delete("/licenses/{license_id}")
async def delete_license(
    license_id: int,
    db: Session = Depends(get_db),
    current_admin_user: Users = Depends(admin_required),
):
    try:
        if not current_admin_user:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin role required.")
        license_to_delete = db.query(License).filter(License.id == license_id).first()
        if not license_to_delete:
            raise HTTPException(status_code=404, detail="License not found")
        db.delete(license_to_delete)
        db.commit()
        return {"status": "success", "message": "License deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete license: {str(e)}")


@router.get("/licenses/zip/downloads")
async def list_all_downloads(db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    user_licenses = db.query(UserLicense).filter(UserLicense.user_id == current_user.id).all()
    items = []
    for ul in user_licenses:
        lic = ul.license
        music = lic.music
        zip_url = None
        
        # Only generate download link if form is filled
        if ul.is_form_filled and lic.zip_s3_key:
            desired_filename = f"{music.name}.zip"
            zip_url = s3_manager.generate_presigned_zip_download(
                s3_key=lic.zip_s3_key, download_filename=desired_filename, expiration=24 * 3600
            )
            
        items.append({
            "user_license_id": ul.id, # Added ID for frontend to link to form
            "license_id": lic.id,
            "music_id": music.id,
            "music_name": music.name,
            "music_image": music.cover_image_url,
            "music_artist_name": music.artist,
            "license_type": lic.license_type.value,
            "zip_download_url": zip_url,
            "is_form_filled": ul.is_form_filled, # Return status
        })
    return {"items": items}


@router.get("/licenses/{order_id}/zip/downloads")
def list_downloads_for_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    order = db.query(Order).get(order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    items = []
    for item in order.order_items:
        lic = item.license
        music = lic.music
        
        # Find the specific UserLicense for this item (assuming 1:1 for simplicity in this context, 
        # but strictly we should query UserLicense by user_id and license_id)
        # However, since we don't have a direct link from OrderItem to UserLicense easily without query,
        # let's fetch it.
        user_license = db.query(UserLicense).filter(
            UserLicense.user_id == current_user.id,
            UserLicense.license_id == lic.id
        ).first()
        
        is_form_filled = user_license.is_form_filled if user_license else False
        user_license_id = user_license.id if user_license else None

        zip_url = None
        if is_form_filled and lic.zip_s3_key:
            desired_filename = f"{music.name}.zip"
            zip_url = s3_manager.generate_presigned_zip_download(
                s3_key=lic.zip_s3_key, download_filename=desired_filename, expiration=24 * 3600
            )
            
        items.append({
            "order_item_id": item.id,
            "user_license_id": user_license_id,
            "license_id": lic.id,
            "music_id": music.id,
            "music_name": music.name,
            "license_type": lic.license_type.value,
            "zip_download_url": zip_url,
            "is_form_filled": is_form_filled,
        })
    return {"order_id": order.id, "items": items}


@router.put("/user-licenses/{user_license_id}/submit-form", response_model=UserLicenseRead)
async def submit_license_form(
    user_license_id: int,
    form_data: UserLicenseUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Submits the mandatory License Completion Form.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    user_license = db.query(UserLicense).filter(UserLicense.id == user_license_id).first()
    if not user_license:
        raise HTTPException(status_code=404, detail="User License not found")
        
    if user_license.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this license")

    # Update fields
    user_license.licensee_name = form_data.licensee_name
    user_license.licensee_email = form_data.licensee_email
    user_license.project_title = form_data.project_title
    
    user_license.is_signed = form_data.is_signed
    # In a real app, we might want to set signed_at server-side, but user provided timezone info is useful
    user_license.signed_at = func.now() 
    user_license.timezone_offset = form_data.timezone_offset
    
    user_license.is_artist_same_as_licensee = form_data.is_artist_same_as_licensee
    user_license.artist_stage_name = form_data.artist_stage_name
    user_license.author_legal_name = form_data.author_legal_name
    
    user_license.is_pro_registered = form_data.is_pro_registered
    user_license.pro_name = form_data.pro_name
    user_license.pro_ipi_number = form_data.pro_ipi_number
    
    user_license.phone_number = form_data.phone_number
    user_license.address = form_data.address
    user_license.isrc_iswc = form_data.isrc_iswc
    
    user_license.has_publisher = form_data.has_publisher
    user_license.publisher_name = form_data.publisher_name
    user_license.publisher_pro = form_data.publisher_pro
    user_license.publisher_ipi_number = form_data.publisher_ipi_number
    
    user_license.is_form_filled = True
    
    db.commit()
    db.refresh(user_license)
    
    # Automatically generate PDF after form submission
    try:
        license_service = LicenseService(db)
        # We don't have request object here for IP/User Agent, but they might have been captured during payment
        # or we could add them to the form submission if needed. 
        # For now, we rely on what's already in the DB or pass None.
        license_service.generate_and_store_license(user_license.id)
    except Exception as e:
        print(f"Error generating PDF after form submission: {e}")
        # We don't fail the request, but log the error. 
        # The user can retry generation via the separate endpoint.

    return user_license


@router.post("/user-licenses/{user_license_id}/generate-pdf")
async def generate_license_pdf_endpoint(
    user_license_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Triggers generation of the license PDF.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    print(user_license_id , "------" )
        
    user_license = db.query(UserLicense).filter(UserLicense.id == user_license_id).first()
    if not user_license:
        raise HTTPException(status_code=404, detail="User License not found")
        
    if user_license.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        license_service = LicenseService(db)
        
        # Capture IP and User Agent from this request if not already present
        buyer_ip = request.headers.get("x-forwarded-for", request.client.host)
        user_agent = request.headers.get("user-agent", "Unknown")
        
        pdf_url = license_service.generate_and_store_license(
            user_license_id=user_license.id,
            buyer_ip=buyer_ip,
            user_agent=user_agent
        )
        
        return {"status": "success", "pdf_url": pdf_url}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


@router.post("/licenses/{license_id}/generate-pdf")
async def generate_license_pdf_by_license_id(
    license_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Alias endpoint to trigger license PDF generation using license_id for the current user.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Find the user's UserLicense for this license
    user_license = db.query(UserLicense).filter(
        UserLicense.user_id == current_user.id,
        UserLicense.license_id == license_id,
    ).order_by(UserLicense.id.desc()).first()

    if not user_license:
        raise HTTPException(status_code=404, detail="No license record found for this user")

    try:
        license_service = LicenseService(db)
        buyer_ip = request.headers.get("x-forwarded-for", request.client.host)
        user_agent = request.headers.get("user-agent", "Unknown")

        pdf_url = license_service.generate_and_store_license(
            user_license_id=user_license.id,
            buyer_ip=buyer_ip,
            user_agent=user_agent,
        )
        return {"status": "success", "pdf_url": pdf_url}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
