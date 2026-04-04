from datetime import datetime
import os
from fastapi import APIRouter, Depends, HTTPException, status, Request
from utils.limiter import limiter
from sqlalchemy.orm import Session
from jose import JWTError
from sqlalchemy import func

from enums.providerenum import ProviderEnum
from models.auth import AuthProvider
from models.user import Users
from schemas.user import UserRegisterSchema, UserLoginSchema, OAuthLoginSchema
from utils.marketing_service import MarketingService
from utils.utils import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_google_token,
    verify_facebook_token,
    handle_oauth_auth,
    verify_token,
    is_user_admin,
)
from utils.deps import get_db, get_current_user, oauth2_scheme

router = APIRouter(tags=["auth"])  # paths kept identical to main

marketing_client = MarketingService()
BREVO_ALL_USERS_LIST_ID = int(os.getenv("BREVO_MAIN_LIST_ID", "2"))


@router.get("/verify-session")
async def verify_session(
    token: str = Depends(oauth2_scheme),
    user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    try:
        token_data = verify_token(token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )

    exp_datetime = datetime.utcfromtimestamp(token_data.get("exp"))
    if datetime.utcnow() > exp_datetime:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )

    user_is_admin = is_user_admin(user)
    return {
        "valid": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "profile_piture": user.profile_piture,
            "is_Admin": user_is_admin,
        },
        "expires_in": token_data.get("exp"),
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register_user(request: Request, user_data: UserRegisterSchema, db: Session = Depends(get_db)):
    existing_user = db.query(Users).filter(Users.email == user_data.email).first()
    if existing_user:
        existing_provider = (
            db.query(AuthProvider)
            .filter(
                AuthProvider.user_id == existing_user.id,
                AuthProvider.provider == ProviderEnum.local,
            )
            .first()
        )
        if existing_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists",
            )
        new_provider = AuthProvider(
            user_id=existing_user.id,
            provider=ProviderEnum.local,
            password_hash=get_password_hash(user_data.password),
        )
        db.add(new_provider)
        db.commit()
        return {"message": "Local authentication added to existing account"}

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
        email=new_user.email, list_id=BREVO_ALL_USERS_LIST_ID, first_name=new_user.name
    )

    access_token = create_access_token(data={"sub": user_data.email})
    refresh_token = create_refresh_token(data={"sub": user_data.email})

    return {
        "message": "User registered successfully",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "email": new_user.email,
            "name": new_user.name,
            "id": new_user.id,
            "profile_piture": new_user.profile_piture,
        },
    }


@router.post("/login")
@limiter.limit("5/minute")
async def login_user(request: Request, user_data: UserLoginSchema, db: Session = Depends(get_db)):
    user = db.query(Users).filter(Users.email == user_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    auth_provider = (
        db.query(AuthProvider)
        .filter(
            AuthProvider.user_id == user.id, AuthProvider.provider == ProviderEnum.local
        )
        .first()
    )

    if not auth_provider or not verify_password(
        user_data.password, auth_provider.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    user.last_login = func.now()  # type: ignore  # func imported in main; reimport locally
    db.commit()

    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    user_is_admin = is_user_admin(user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "profile_piture": user.profile_piture,
            "is_Admin": user_is_admin,
        },
    }


@router.post("/oauth/google")
@limiter.limit("10/minute")
async def google_auth(request: Request, oauth_data: OAuthLoginSchema, db: Session = Depends(get_db)):
    response = verify_google_token(oauth_data.provider_id, oauth_data.email)
    valid = response.get("valid", False)
    profile_picture = response.get("picture", None)
    sub = response.get("sub", None)
    if not valid or not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google authentication",
        )
    
    # Use the stable sub as provider_id
    oauth_data.provider_id = sub
    
    return await handle_oauth_auth(
        oauth_data, ProviderEnum.google.value, db, profile_picture
    )


@router.post("/oauth/facebook")
@limiter.limit("10/minute")
async def facebook_auth(request: Request, oauth_data: OAuthLoginSchema, db: Session = Depends(get_db)):
    valid, profile_picture, user_id = verify_facebook_token(
        oauth_data.provider_id, oauth_data.email
    )
    if not valid or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Facebook authentication",
        )

    # Use the stable user_id as provider_id
    oauth_data.provider_id = user_id

    return await handle_oauth_auth(
        oauth_data, ProviderEnum.facebook.value, db, profile_picture
    )


@router.post("/refresh")
async def refresh_token(request: Request, db: Session = Depends(get_db)):
    """
    Get a new access token using a refresh token
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid token"
        )
    
    token = auth_header.split(" ")[1]
    
    try:
        # Verify the refresh token
        payload = verify_token(token, expected_type="refresh")
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if user exists
        user = db.query(Users).filter(func.lower(Users.email) == func.lower(email)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
            
        # Generate new access token
        access_token = create_access_token(data={"sub": user.email})
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}"
        )
