from typing import Optional, List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.user import Users
from models.music import Music
from models.playlist import Playlist
from models.playlistmusic import PlaylistMusic
from models.userlikedplaylist import UserLikedPlaylist
from utils.s3_manager import S3Manager
from utils.deps import get_db, get_current_user

router = APIRouter(tags=["playlists"])  

s3_manager = S3Manager()


@router.post("/music/playlists", status_code=status.HTTP_201_CREATED)
async def create_playlist(
    db: Session = Depends(get_db),
    playlist_name: str = Form(...),
    playlist_description: Optional[str] = Form(None),
    playlist_is_public: bool = Form(False),
    cover_image_file: Optional[UploadFile] = File(None),
    current_user: Users = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        temp_cover_url = None
        if cover_image_file:
            temp_key = f"temp/{current_user.id}/{uuid.uuid4()}"
            temp_cover_url = await s3_manager.upload_file_from_uploadfile(
                cover_image_file,
                temp_key,
            )

        new_playlist = Playlist(
            user_id=current_user.id,
            name=playlist_name,
            description=playlist_description,
            is_public=playlist_is_public,
            cover_image_url=temp_cover_url,
        )
        db.add(new_playlist)
        db.commit()
        db.refresh(new_playlist)

        if temp_cover_url:
            filename = s3_manager.get_file_name_from_url(temp_cover_url)
            ext = filename.split('.')[-1]
            perm_key = (
                f"users/{current_user.id}/"
                f"playlists/{new_playlist.id}/cover.{ext}"
            )
            perm_url = s3_manager.move_s3_object(old_key=temp_key, new_key=perm_key)
            new_playlist.cover_image_url = perm_url
            db.commit()
            db.refresh(new_playlist)

        return new_playlist
    except Exception as e:
        db.rollback()
        if 'temp_key' in locals():
            s3_manager.delete_file(temp_key)
        raise HTTPException(500, detail=f"Playlist creation failed: {str(e)}")


@router.get("/users/{user_id}/playlists")
async def get_user_playlists(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    try:
        if not current_user:
            raise Exception(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Please log in to view playlists.",
            )
        if current_user.id != user_id:
            raise Exception(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to view this user's playlists",
            )

        playlists = db.query(Playlist).filter(Playlist.user_id == user_id).all()

        response = []
        for playlist in playlists:
            total_songs = (
                db.query(func.count(PlaylistMusic.id))
                .filter(PlaylistMusic.playlist_id == playlist.id)
                .scalar()
            )
            response.append(
                {
                    "playlist_id": playlist.id,
                    "playlist_name": playlist.name,
                    "playlist_description": playlist.description,
                    "is_public": playlist.is_public,
                    "cover_image_url": playlist.cover_image_url,
                    "created_at": playlist.created_at,
                    "updated_at": playlist.updated_at,
                    "likes_count": playlist.likes_count,
                    "total_songs": total_songs,
                }
            )

        return response
    except HTTPException as he:
        raise HTTPException(
            status_code=he.status_code, detail=f"Failed to retrieve playlists: {str(he.detail)}"
        )


@router.delete("/music/{playlist_id}/playlist/{music_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_music_from_playlist(
    playlist_id: int,
    music_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Please log in to delete music from playlist.",
            )
        playlist_music = (
            db.query(PlaylistMusic)
            .filter(PlaylistMusic.playlist_id == playlist_id, PlaylistMusic.music_id == music_id)
            .first()
        )
        if not playlist_music:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Music not found in the playlist")

        db.delete(playlist_music)
        db.commit()
        return {"message": "Music deleted from playlist successfully"}
    except HTTPException as he:
        raise HTTPException(
            status_code=he.status_code,
            detail=f"Failed to delete music from playlist: {str(he.detail)}",
        )


@router.get("/music/{playlist_id}/playlist")
def get_songs_in_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Please log in to view playlist.",
            )

        playlist = db.query(PlaylistMusic).filter(PlaylistMusic.playlist_id == playlist_id).all()
        if not playlist:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")

        songs_in_playlist = []
        for song in playlist:
            music = db.query(Music).filter(Music.id == song.music_id).first()
            if music:
                songs_in_playlist.append(music)
            if not songs_in_playlist:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist is empty")

        return songs_in_playlist
    except HTTPException as he:
        raise HTTPException(status_code=he.status_code, detail=f"Failed to retrieve songs in playlist: {str(he.detail)}")


@router.get("/playlists/{playlist_id}")
async def get_playlist_details(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Please log in to view playlist details.",
            )
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")

        user = db.query(Users).filter(Users.id == playlist.user_id).first()
        playlist_details = {
            "playlist_id": playlist.id,
            "playlist_name": playlist.name,
            "playlist_description": playlist.description,
            "is_public": playlist.is_public,
            "cover_image_url": playlist.cover_image_url,
            "created_at": playlist.created_at,
            "user_id": user.id,
            "user_name": user.name,
            "user_profile_picture": user.profile_piture,
        }
        return playlist_details
    except HTTPException as he:
        raise HTTPException(status_code=he.status_code, detail=f"Failed to retrieve playlist details: {str(he.detail)}")


@router.post("/playlists/{playlist_id}/music/{music_id}", status_code=status.HTTP_201_CREATED)
async def add_music_to_playlist(
    playlist_id: int,
    music_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in to add music to playlist.",
        )

    playlist = db.query(Playlist).filter(Playlist.id == playlist_id, Playlist.user_id == current_user.id).first()
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playlist with id {playlist_id} not found or you don't have permission.",
        )

    music = db.query(Music).filter(Music.id == music_id).first()
    if not music:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Music with id {music_id} not found.")

    existing_entry = db.query(PlaylistMusic).filter(PlaylistMusic.playlist_id == playlist_id, PlaylistMusic.music_id == music_id).first()
    if existing_entry:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"message": "This music is already in the playlist.", "isPresent": True})

    playlist_music = PlaylistMusic(playlist_id=playlist_id, music_id=music_id)
    try:
        db.add(playlist_music)
        db.commit()
        db.refresh(playlist_music)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to add music to playlist: {str(e)}")
    return {"message": "Music added to playlist successfully", "data": playlist_music}


@router.get("/users/{user_id}/liked-playlists")
async def get_liked_playlist_list(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    try:
        if not current_user and user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Please log in to view liked playlist.",
            )
        liked_playlist = db.query(UserLikedPlaylist).filter(UserLikedPlaylist.user_id == user_id).all()
        return liked_playlist
    except HTTPException as he:
        raise HTTPException(status_code=he.status_code, detail=f"Failed to retrieve liked playlist: {str(he.detail)}")


@router.post("/playlists/{playlist_id}/like")
async def like_and_unlike_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    try:
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")

        existing = db.query(UserLikedPlaylist).filter_by(user_id=current_user.id, playlist_id=playlist_id).first()
        if existing:
            db.delete(existing)
            playlist.likes_count = (playlist.likes_count or 0) - 1
            playlist.likes_count = max(playlist.likes_count, 0)
            message = "Playlist unliked"
        else:
            db.add(UserLikedPlaylist(user_id=current_user.id, playlist_id=playlist_id))
            playlist.likes_count = (playlist.likes_count or 0) + 1
            message = "Playlist liked"

        db.commit()
        return {"message": message, "likes": playlist.likes_count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to like playlist: {str(e)}")


@router.put("/playlists/{playlist_id}", status_code=status.HTTP_200_OK)
async def update_playlist(
    playlist_id: int,
    playlist_name: Optional[str] = Form(None),
    playlist_description: Optional[str] = Form(None),
    playlist_is_public: Optional[bool] = Form(None),
    cover_image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    try:
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")
        if playlist.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this playlist")

        old_cover_url = playlist.cover_image_url
        new_cover_url = None

        if cover_image_file:
            ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"]
            MAX_SIZE = 5 * 1024 * 1024
            if cover_image_file.content_type not in ALLOWED_TYPES:
                raise HTTPException(status_code=415, detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_TYPES)}")
            file_size = cover_image_file.size
            if file_size > MAX_SIZE:
                raise HTTPException(status_code=413, detail=f"File too large. Max size: {MAX_SIZE//1024//1024}MB")
            ext = cover_image_file.filename.split('.')[-1].lower()
            new_key = f"users/{current_user.id}/playlists/{playlist_id}/cover.{ext}"
            new_cover_url = await s3_manager.upload_file_from_uploadfile(cover_image_file, new_key, extra_args={'ContentType': cover_image_file.content_type})
            playlist.cover_image_url = new_cover_url

        if playlist_name is not None:
            playlist.name = playlist_name
        if playlist_description is not None:
            playlist.description = playlist_description
        if playlist_is_public is not None:
            playlist.is_public = playlist_is_public

        db.commit()
        db.refresh(playlist)

        if new_cover_url and old_cover_url:
            try:
                old_key = s3_manager.get_key_from_url(old_cover_url)
                s3_manager.delete_file(old_key)
            except Exception as e:
                print(f"Warning: Failed to delete old cover image: {str(e)}")

        return {"message": "Playlist updated successfully", "playlist": playlist}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating playlist: {str(e)}")


@router.delete("/playlists/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    try:
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")
        if playlist.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this playlist")

        folder_path = f"users/{current_user.id}/playlists/{playlist_id}/"
        try:
            s3_manager.delete_folder(folder_path)
        except Exception as e:
            print(f"Warning: Failed to delete S3 folder: {str(e)}")
        db.delete(playlist)
        db.commit()
        return {"message": "Playlist deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete playlist: {str(e)}")
