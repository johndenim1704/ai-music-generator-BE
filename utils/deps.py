from typing import Optional, Tuple

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import func
from sqlalchemy.orm import Session, sessionmaker

from config.db import db_engine
from models.user import Users
from utils.utils import verify_token, is_user_admin


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def get_db():
    """
    Database session dependency
    Uses shared SessionLocal from config for connection pooling
    """
    from config.db import SessionLocal
    
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Users:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Enforce 'access' token type for normal protected routes
        payload = verify_token(token, expected_type="access")
        email: str = payload.get("sub")
        if not email:
            raise credentials_exception
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )

    user = db.query(Users).filter(func.lower(Users.email) == func.lower(email)).first()
    if not user:
        raise credentials_exception
    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> Optional[Users]:
    if token is None:
        return None
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials from token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Enforce 'access' token type
        payload = verify_token(token, expected_type="access")
        email: str = payload.get("sub")
        if not email:
            raise credentials_exception
        user = db.query(Users).filter(func.lower(Users.email) == func.lower(email)).first()
        if not user:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception
    except Exception:
        raise credentials_exception


async def get_current_user_with_role(
    user_data: Users = Depends(get_current_user),
) -> Tuple[Users, bool]:
    user = user_data
    from os import getenv

    user_email_str = getenv("EMAIL_LIST", "")
    user_email_list = [email.strip() for email in user_email_str.split(",") if email.strip()]
    is_admin = user.email in user_email_list
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user, is_admin


async def admin_required(current_user: Users = Depends(get_current_user)) -> Users:
    if not is_user_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Admin role required.",
        )
    return current_user
