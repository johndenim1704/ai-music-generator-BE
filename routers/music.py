from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import asyncio
import re

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func

from models.music import Music
from models.music_comment import MusicComment
from models.user import Users
from models.userlikedmusic import UserLikedMusic
from schemas.music_comment import MusicCommentCreate
from utils.s3_manager import S3Manager
from utils.limiter import limiter
from utils.deps import get_db, get_current_user, get_current_user_optional, admin_required
from utils.utils import is_user_admin

router = APIRouter(tags=["music"])  # keeping paths identical

s3_manager = S3Manager()


@router.get("/music")
async def get_music(
    db: Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user_optional)
) -> List[Dict[str, Any]]:
    try:
        music_list = db.query(Music).order_by(Music.created_at.desc()).all()
        liked_music_ids = set()
        if current_user:
            music_ids = [music.id for music in music_list]
            if music_ids:
                liked_records = db.query(UserLikedMusic.music_id).filter(
                    UserLikedMusic.user_id == current_user.id,
                    UserLikedMusic.music_id.in_(music_ids)
                ).all()
                liked_music_ids = {record[0] for record in liked_records}
        response = []
        for music in music_list:
            music_dict = {c.key: getattr(music, c.key) for c in Music.__table__.columns if c.key not in ['mp3_url', 'wav_url']}
            if current_user:
                music_dict['is_liked_by_user'] = music.id in liked_music_ids
            response.append(music_dict)
        return response
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve music: {str(e)}")


@router.get("/music/{music_id}")
async def get_music_by_id(music_id: int, db: Session = Depends(get_db)):
    try:
        music = db.query(Music).filter(Music.id == music_id).first()
        if not music:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Music not found")
        return music
    except HTTPException as he:
        raise HTTPException(status_code=he.status_code, detail=he.detail)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve music: {str(e)}")


def serialize_comment(comment: MusicComment, include_replies: bool = True):
    user = comment.user
    data = {
        "id": comment.id,
        "music_id": comment.music_id,
        "user_id": comment.user_id,
        "content": comment.content,
        "parent_id": comment.parent_id,
        "created_at": comment.created_at,
        "user": {
            "id": user.id if user else None,
            "name": user.name if user else None,
            "profile_picture": user.profile_piture if user else None,
        },
        "replies": [],
    }
    if include_replies:
        data["replies"] = [serialize_comment(reply, include_replies=False) for reply in comment.replies]
    return data


@router.get("/music/{music_id}/comments")
async def get_music_comments(music_id: int, db: Session = Depends(get_db)):
    try:
        music = db.query(Music).filter(Music.id == music_id).first()
        if not music:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Music not found")

        comments = (
            db.query(MusicComment)
            .options(
                selectinload(MusicComment.user),
                selectinload(MusicComment.replies).selectinload(MusicComment.user),
            )
            .filter(MusicComment.music_id == music_id, MusicComment.parent_id.is_(None))
            .order_by(MusicComment.created_at.asc())
            .all()
        )
        return [serialize_comment(comment, include_replies=True) for comment in comments]
    except HTTPException as he:
        raise HTTPException(status_code=he.status_code, detail=he.detail)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve comments: {str(e)}")


@router.post("/music/{music_id}/comments", status_code=status.HTTP_201_CREATED)
async def create_music_comment(
    music_id: int,
    payload: MusicCommentCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated. Please log in to comment.")
    try:
        music = db.query(Music).filter(Music.id == music_id).first()
        if not music:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Music not found")

        parent_id = payload.parent_id
        if parent_id and not is_user_admin(current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can reply to comments.")
        if parent_id:
            parent_comment = db.query(MusicComment).filter(MusicComment.id == parent_id).first()
            if not parent_comment or parent_comment.music_id != music_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parent comment")

        new_comment = MusicComment(
            music_id=music_id,
            user_id=current_user.id,
            parent_id=parent_id,
            content=payload.content,
        )
        db.add(new_comment)
        db.commit()
        db.refresh(new_comment)
        db.refresh(current_user)
        new_comment.user = current_user
        return serialize_comment(new_comment, include_replies=False)
    except HTTPException as he:
        db.rollback()
        raise HTTPException(status_code=he.status_code, detail=he.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create comment: {str(e)}")

@router.post("/upload-music", status_code=status.HTTP_201_CREATED)
async def upload_music(
    mp3_file: Optional[UploadFile] = File(None),
    wav_file: Optional[UploadFile] = File(None),
    cover_image: Optional[UploadFile] = File(None),
    name: str = Form(...),
    artist: str = Form(...),
    album: str = Form(...),
    genre: str = Form(...),
    track_type: str = Form(...),
    mood: str = Form(...),
    instruments: str = Form(...),
    bpm: float = Form(...),
    duration: float = Form(...),
    is_ai_generated: bool = Form(...),
    is_free: bool = Form(...),
    price: float = Form(...),
    db: Session = Depends(get_db),
    current_admin_user: Users = Depends(admin_required)
):
    user_id = current_admin_user.id
    if not current_admin_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin role required.")

    upload_tasks: Dict[str, asyncio.Task] = {}
    if mp3_file:
        upload_tasks["mp3"] = s3_manager.handle_music_file_upload(mp3_file, artist, name, "mp3")
    if wav_file:
        upload_tasks["wav"] = s3_manager.handle_music_file_upload(wav_file, artist, name, "wav")
    if cover_image:
        upload_tasks["cover"] = s3_manager.handle_music_file_upload(cover_image, artist, name, "image")

    if not upload_tasks:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one file (mp3, wav, or cover image) must be provided.")

    task_results = await asyncio.gather(*upload_tasks.values(), return_exceptions=True)

    result_urls: Dict[str, Optional[str]] = {}
    for key, result in zip(upload_tasks.keys(), task_results):
        if isinstance(result, Exception):
            db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to upload {key} file: {result}")
        result_urls[key] = result

    mp3_url = result_urls.get("mp3")
    wav_url = result_urls.get("wav")
    cover_url = result_urls.get("cover")

    if not mp3_url and not wav_url:
        raise HTTPException(status_code=400, detail="At least one of MP3 or WAV file must be uploaded.")

    try:
        new_music = Music(
            name=name,
            artist=artist,
            album=album,
            genre=genre,
            track_type=track_type,
            mood=mood,
            instruments=instruments,
            bpm=bpm,
            duration=duration,
            mp3_url=mp3_url,
            wav_url=wav_url,
            cover_image_url=cover_url,
            is_ai_generated=is_ai_generated,
            is_free=is_free,
            price=price,
            user_id=user_id
        )
        db.add(new_music)
        db.commit()
        db.refresh(new_music)
        return {"message": "Music uploaded successfully", "music_data": new_music}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save music data to the database: {str(e)}")


def add_to_listening_history(db: Session, user_id: int, music_id: int, device_info: str = None):
    recent_play = db.query(ListeningHistory).filter(
        ListeningHistory.user_id == user_id,
        ListeningHistory.music_id == music_id
    ).first()

    if recent_play:
        recent_play.played_at = func.now()
        db.commit()
        return

    history_entry = ListeningHistory(
        user_id=user_id,
        music_id=music_id,
        played_at=func.now(),
        completed=False,
        play_duration=0,
        device_info=device_info
    )
    db.add(history_entry)
    db.commit()


from models.history import ListeningHistory  # after function to avoid circular import hints


@router.api_route("/music/{music_id}/stream", methods=["GET", "HEAD"], operation_id="stream_music")
async def get_music_stream_url(
    music_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user_optional)
):
    try:
        music = db.query(Music).filter(Music.id == music_id).first()
        if not music:
            raise HTTPException(status_code=404, detail="Music not found")

        if current_user:
            background_tasks.add_task(
                add_to_listening_history,
                db,
                current_user.id,
                music_id,
            )

        source_url = music.mp3_url or music.wav_url
        if not source_url:
            raise HTTPException(status_code=404, detail="No audio source available for this track")

        parsed = urlparse(source_url)
        s3_key = parsed.path.lstrip('/')
        bucket_name = s3_manager.get_s3_bucket_from_url(source_url)

        try:
            file_size = s3_manager.get_file_size(s3_key, bucket_name)
        except Exception as e:
            print(f"Could not get file size: {e}")
            file_size = None

        range_header = request.headers.get('Range')
        if range_header and file_size:
            range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
                end = min(end, file_size - 1)
                return s3_manager.stream_file_range_from_s3(s3_key, bucket_name, start, end, file_size)

        headers = {
            'Accept-Ranges': 'bytes',
            'Content-Type': 'audio/mpeg',
            'Content-Length': str(file_size) if file_size else '',
            'Cache-Control': 'no-cache'
        }

        return StreamingResponse(
            s3_manager.stream_file_from_s3(s3_key, bucket_name),
            media_type="audio/mpeg",
            headers=headers
        )
    except HTTPException as he:
        raise HTTPException(status_code=he.status_code, detail=he.detail)
    except Exception as e:
        print(f"Error generating stream: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/music/{music_id}/download")
# @limiter.limit("10/minute")
async def download_music(request: Request, music_id: int, db: Session = Depends(get_db)):
    try:
        music = db.query(Music).filter(Music.id == music_id).first()
        if not music:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Music not found")
        if not music.is_free:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Music is not free to download")
        s3_key = urlparse(music.mp3_url).path.lstrip('/')
        presigned_url = s3_manager.generate_presigned_url_for_download(s3_key)
        return {"download_url": presigned_url}
    except HTTPException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error generating download link: {str(e)}")


@router.put("/music/{music_id}", status_code=status.HTTP_200_OK)
async def update_music(
    music_id: int,
    mp3_file: Optional[UploadFile] = File(None),
    wav_file: Optional[UploadFile] = File(None),
    cover_image: Optional[UploadFile] = File(None),
    name: Optional[str] = Form(None),
    artist: Optional[str] = Form(None),
    album: Optional[str] = Form(None),
    genre: Optional[str] = Form(None),
    track_type: Optional[str] = Form(None),
    mood: Optional[str] = Form(None),
    instruments: Optional[str] = Form(None),
    bpm: Optional[float] = Form(None),
    duration: Optional[float] = Form(None),
    is_ai_generated: Optional[bool] = Form(None),
    is_free: Optional[bool] = Form(None),
    price: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_admin_user: Users = Depends(admin_required)
):
    try:
        if not current_admin_user:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin role required.")

        music = db.query(Music).filter(Music.id == music_id).first()
        if not music:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Music not found")

        name_changed = name is not None and name != music.name
        artist_changed = artist is not None and artist != music.artist

        if name_changed or artist_changed:
            old_name, old_artist = music.name, music.artist
            if name:
                music.name = name
            if artist:
                music.artist = artist

            relocation_tasks = []
            for attr, file_type in [("mp3_url", "mp3"), ("wav_url", "wav"), ("cover_image_url", "image")]:
                url = getattr(music, attr)
                if url:
                    filename = url.split("/")[-1]
                    old_key = s3_manager.generate_s3_key(old_artist, old_name, file_type, filename)
                    new_key = s3_manager.generate_s3_key(music.artist, music.name, file_type, filename)
                    relocation_tasks.append((old_key, new_key, attr))

            async def relocate_file(old_key, new_key, attr):
                new_url = s3_manager.move_s3_object(old_key, new_key)
                setattr(music, attr, new_url)

            try:
                await asyncio.gather(*[relocate_file(old_key, new_key, attr) for old_key, new_key, attr in relocation_tasks])
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail=f"Relocation failed: {str(e)}")

        upload_tasks = []
        file_upload_map = []
        files_to_process = [
            (mp3_file, "mp3", "mp3_url"),
            (wav_file, "wav", "wav_url"),
            (cover_image, "image", "cover_image_url"),
        ]
        for file_obj, file_type, attr in files_to_process:
            if file_obj:
                make_unique = file_type in ["mp3", "wav"]
                upload_tasks.append(
                    s3_manager.handle_music_file_upload(
                        file=file_obj,
                        artist=artist or music.artist,
                        track_name=name or music.name,
                        file_type=file_type,
                        unique=make_unique,
                    )
                )
                file_upload_map.append({'attr': attr, 'filename': file_obj.filename})

        if upload_tasks:
            new_urls = await asyncio.gather(*upload_tasks)
            for i, url in enumerate(new_urls):
                if url is None:
                    failed_file_info = file_upload_map[i]
                    raise Exception(f"Upload failed for file: {failed_file_info['filename']}. No changes have been saved.")
            for i, url in enumerate(new_urls):
                attr_to_update = file_upload_map[i]['attr']
                setattr(music, attr_to_update, url)

        update_fields = {
            "name": name,
            "artist": artist,
            "album": album,
            "genre": genre,
            "track_type": track_type,
            "mood": mood,
            "instruments": instruments,
            "bpm": bpm,
            "duration": duration,
            "is_ai_generated": is_ai_generated,
            "is_free": is_free,
            "price": price,
        }
        for field, value in update_fields.items():
            if value is not None:
                setattr(music, field, value)

        db.commit()
        db.refresh(music)
        return music
    except HTTPException as he:
        db.rollback()
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update music: {str(e)}")


@router.delete("/music/{music_id}")
async def delete_music(
    music_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_admin_user: Users = Depends(admin_required)
):
    try:
        if not current_admin_user:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin role required.")
        music = db.query(Music).filter(Music.id == music_id).first()
        if not music:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Music not found")
        folder_path = f"music/{music.artist.lower().replace(' ', '-')}/{music.name.lower().replace(' ', '-')}/"
        background_tasks.add_task(s3_manager.delete_folder, folder_path)
        db.delete(music)
        db.commit()
        return {"message": "Music deleted successfully"}
    except HTTPException as he:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete music: {str(e)}")


@router.post("/music/{music_id}/like")
# @limiter.limit("20/minute")
async def like_and_unlike_music(
    request: Request,
    music_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated. Please log in to like music.")
    try:
        music = db.query(Music).filter(Music.id == music_id).first()
        if not music:
            raise HTTPException(status_code=404, detail="Music not found")
        existing_like = db.query(UserLikedMusic).filter_by(user_id=current_user.id, music_id=music_id).first()
        if existing_like:
            db.delete(existing_like)
            music.likes_count = max(0, (music.likes_count or 0) - 1)
            liked_now = False
            message = "Music unliked successfully"
        else:
            new_like = UserLikedMusic(user_id=current_user.id, music_id=music_id)
            db.add(new_like)
            music.likes_count = (music.likes_count or 0) + 1
            liked_now = True
            message = "Music liked successfully"
        db.commit()
        return {"message": message, "liked": liked_now, "likes_count": music.likes_count}
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to like music: {str(e)}")


@router.get("/music/{music_id}/likes")
async def get_music_likes(music_id: int, db: Session = Depends(get_db)):
    try:
        music = db.query(Music).filter(Music.id == music_id).first()
        if not music:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Music not found")
        likes = db.query(UserLikedMusic).filter(UserLikedMusic.music_id == music_id).all()
        return len(likes)
    except HTTPException as he:
        raise HTTPException(status_code=he.status_code, detail=he.detail)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve likes: {str(e)}")


@router.get("/users/{user_id}/liked-music")
async def get_liked_music_list(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    try:
        if not current_user and user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to view this user's liked music")
        liked_music = db.query(UserLikedMusic).filter(UserLikedMusic.user_id == user_id).all()
        if not liked_music:
            return {"message": "No liked music found for this user"}
        music_ids = [lm.music_id for lm in liked_music]
        if not music_ids:
            return {"message": "No liked music found for this user"}
        music_list = db.query(Music).filter(Music.id.in_(music_ids)).all()
        music_data = [{k: v for k, v in m.__dict__.items() if k != '_sa_instance_state'} for m in music_list]
        return music_data
    except HTTPException as he:
        raise HTTPException(status_code=he.status_code, detail=f"Failed to retrieve liked music: {str(he.detail)}")
