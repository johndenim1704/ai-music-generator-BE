from typing import Optional
import os

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.user import Users
from models.auth import AuthProvider
from utils.s3_manager import S3Manager
from utils.utils import get_password_hash
from enums.providerenum import ProviderEnum
from utils.marketing_service import MarketingService
from utils.deps import get_db, admin_required, get_current_user
from schemas.user import UserRegisterSchema

router = APIRouter(tags=["users"])  # paths kept identical to main

s3_manager = S3Manager()
marketing_client = MarketingService()


@router.get("/users/")
async def get_users(
    db: Session = Depends(get_db),
    admin_user: Users = Depends(admin_required),
):
    try:
        if not admin_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized. Admin role required.",
            )
        users = db.query(Users).all()
        return users
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users: {str(e)}",
        )


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    name: str = Form(None),
    profile_picture: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    admin_user: Users = Depends(admin_required),
    response: Response = None,
):
    try:
        if not admin_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        if user_id != admin_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to update this user",
            )
        user = db.query(Users).filter(Users.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to update this user",
            )
        if name and user.name != name:
            user.name = name
        if profile_picture:
            s3_key = f"user_profiles/user_{user.id}/{profile_picture.filename.lower().replace(' ', '-')}"
            s3_url = await s3_manager.upload_file_from_uploadfile(profile_picture, s3_key)
            user.profile_piture = s3_url
        db.commit()
        db.refresh(user)
        return {"message": "User updated successfully", "user": user}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Update failed: {str(e)}",
        )


@router.post("/update/user/info/{user_id}")
async def update_user_information(
    user_id: int,
    name: str = Form(None),
    profile_picture: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        if user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to update this user",
            )
        user = db.query(Users).filter(Users.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if name and user.name != name:
            user.name = name
        if profile_picture:
            s3_key = f"user_profiles/user_{user.id}/{profile_picture.filename.lower().replace(' ', '-')}"
            s3_url = await s3_manager.upload_file_from_uploadfile(profile_picture, s3_key)
            user.profile_piture = s3_url
        db.commit()
        db.refresh(user)
        return {"message": "User updated successfully", "user": user}
    except HTTPException as he:
        # mimic original behavior: returning dict is not proper; raise as in main
        raise HTTPException(status_code=he.status_code, detail=he.detail)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: Users = Depends(admin_required),
):
    try:
        if not admin_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized. Admin role required.",
            )
        user = db.query(Users).filter(Users.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to delete this user",
            )
        if user.profile_piture:
            folder_path = f"user_profiles/user_{user.id}/"
            s3_manager.delete_folder(folder_path)
        db.query(AuthProvider).filter(AuthProvider.user_id == user_id).delete()
        db.delete(user)
        db.commit()
        return {"message": "User deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}",
        )


@router.post("/admin/create-user", status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserRegisterSchema,
    db: Session = Depends(get_db),
    admin_user: Users = Depends(admin_required),
):
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Admin role required.",
        )
    try:
        existing_user = db.query(Users).filter(Users.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists",
            )
        new_user = Users(email=user_data.email, name=user_data.name)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        auth_provider = AuthProvider(
            user_id=new_user.id,
            provider=ProviderEnum.local,
            password_hash=get_password_hash(user_data.password),
        )
        db.add(auth_provider)
        db.commit()
        marketing_client.add_new_contact_to_list(
            email=new_user.email,
            list_id=int(os.getenv("BREVO_MAIN_LIST_ID", "2")),
            first_name=new_user.name,
        )
        return {"message": "User created successfully", "user": new_user}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )
