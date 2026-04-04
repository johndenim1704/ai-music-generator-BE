from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.user import Users
from models.music import Music
from models.history import ListeningHistory
from utils.deps import get_db, get_current_user

router = APIRouter(tags=["history"])  


@router.get("/users/{user_id}/history")
async def get_history(user_id: int, db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    try:
        if not current_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID is required")
        history_list = db.query(ListeningHistory).filter(ListeningHistory.user_id == user_id).all()
        if not history_list:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No history found for this user")
        history_music_list = []
        for history in history_list:
            music = db.query(Music).filter(Music.id == history.music_id).first()
            if music:
                history_music_list.append(music)
        return history_music_list
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve history: {str(e)}")


@router.delete("/users/{user_id}/history/{music_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_history(user_id: int, music_id: int, db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    try:
        if not current_user and user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID is required and must match the current user ID")
        history = db.query(ListeningHistory).filter(ListeningHistory.user_id == user_id, ListeningHistory.music_id == music_id).first()
        if not history:
            raise HTTPException(status_code=404, detail="History not found")
        db.delete(history)
        db.commit()
        return {"message": "History deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete history: {str(e)}")
