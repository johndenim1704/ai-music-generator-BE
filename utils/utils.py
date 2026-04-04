from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status
import requests
from sqlalchemy import func
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from sqlalchemy.orm import Session
from config.db import db_engine
from models.user import Users
from models.auth import AuthProvider
from enums.providerenum import ProviderEnum
from schemas.user import OAuthLoginSchema
import dotenv
import os
from urllib.parse import urlparse
from sqlalchemy.exc import IntegrityError
#  Load environment variables
dotenv.load_dotenv(override=True)


SECRET_KEY = os.getenv("SECRET_KEY")   
ALGORITHM = os.getenv("ALGORITHM","HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


# These would be stored in your .env file
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET") 
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")
FACEBOOK__DEBUG_TOEKN_URL = os.getenv('FACEBOOK_DEBUG_TOKEN_URL')
FACEBOOK_USER_INFO_URL= os.getenv('FACEBOOK_USER_INFO_URL')

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate a hash from a plain password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Checking user is admin or not
def is_user_admin(user: Users) -> bool:
    """
    Checks if a given user's email is in the admin email list
    defined in the environment variables.
    """
    if not user or not user.email:
        return False
        
    admin_email_str = os.getenv("EMAIL_LIST", "") 
    if not admin_email_str:
        return False 

    admin_email_list = {email.strip().lower() for email in admin_email_str.split(",")}
    
    return user.email.lower() in admin_email_list


def verify_token(token: str, expected_type: str = "access") -> dict:
    """Verify a JWT token and return its payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verify token type
        if payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {expected_type}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    

def verify_google_token(token: str, email: str) -> bool:
    """
    Verify a Google ID token.
    
    Args:
        token: The Google ID token to verify
        email: The email to validate against the token
        
    Returns:
        bool: True if the token is valid and matches the email
    """
    try:
        # Verify the token against Google's servers
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
        # Check if the token is for the right audience
        if idinfo['aud'] not in [GOOGLE_CLIENT_ID]:
            return {"valid": False}
            
        # Verify the email matches
        if idinfo['email'] != email:
            return {"valid": False}

        return {"valid": True, "picture": idinfo.get('picture'), "sub": idinfo.get('sub')}
        
    except Exception:
        return {"valid": False}

def verify_facebook_token(token: str, email: str):
    """
    Verify a Facebook access token.
    
    Args:
        token: The Facebook access token to verify
        email: The email to validate against the token
        
    Returns:
        tuple: (bool, picture_url, user_id)
    """
    try:
        # verify the token with Facebook
        response = requests.get(
            f"{FACEBOOK__DEBUG_TOEKN_URL}?input_token={token}&access_token={FACEBOOK_APP_ID}|{FACEBOOK_APP_SECRET}"
        )
        data = response.json()
        
        if not data.get('data', {}).get('is_valid', False):
            return False, None, None
            
        # verify email
        user_response = requests.get(
            f"{FACEBOOK_USER_INFO_URL}?fields=email,id&access_token={token}"
        )
        user_data = user_response.json()
        user_id = user_data.get('id')
        
        
        # Verify the email matches
        if user_data.get('email') != email:
            return False, None, None
        
        picture_response = requests.get(
            f"{FACEBOOK_USER_INFO_URL}?fields=picture&access_token={token}"
        )
        picture_data = picture_response.json()
        picture_url = picture_data.get('picture', {}).get('data', {}).get('url')
            
        return True, picture_url if picture_url else None, user_id
        
    except Exception:
        return False, None, None
    


async def handle_oauth_auth(oauth_data: OAuthLoginSchema, provider: ProviderEnum, db: Session,profile_picture: Optional[str] = None ):
    # Find user by email
    user = db.query(Users).filter(Users.email == oauth_data.email).first()
    
    if not user:
        # Create new user if doesn't exist
        user = Users(
            email=oauth_data.email,
            name=oauth_data.name,
            profile_piture=profile_picture,
            last_login=func.now()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
       
        user.last_login = func.now()
        if profile_picture and user.profile_piture != profile_picture:
            user.profile_piture = profile_picture
        db.commit()
    existing_user_provider  = db.query(AuthProvider).filter(
        AuthProvider.user_id == user.id,
        AuthProvider.provider == provider
    ).first()
    
    if existing_user_provider:
        
        existing_user_provider.provider_id = oauth_data.provider_id
        auth_provider = existing_user_provider
    else:
       
        auth_provider = AuthProvider(
            user_id=user.id,
            provider=provider,
            provider_id=oauth_data.provider_id
        )
        db.add(auth_provider)
    
    user.last_login = func.now()
    if profile_picture and user.profile_piture == None:
        user.profile_piture = profile_picture
        
    db.commit()

    # Check user is admin or not
    is_admin = is_user_admin(user)

    # Generate JWT tokens
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "profile_piture": user.profile_piture,
            "is_Admin": is_admin,
        }
    }