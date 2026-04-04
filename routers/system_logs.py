from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict
from utils.logger import get_recent_logs
from utils.deps import get_current_user
from models.user import Users

router = APIRouter(tags=["logs"], prefix="/logs")

@router.get("/", response_model=List[Dict])
async def fetch_logs(limit: int = 100, current_user: Users = Depends(get_current_user)):
    """
    Get recent system logs for debugging in production.
    Only accessible by superusers.
    """
    if not current_user.is_Admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access system logs"
        )
    
    return get_recent_logs(limit)
