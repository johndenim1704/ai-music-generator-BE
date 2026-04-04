"""
Audio Mastering Router
Provides API endpoints for professional audio mastering
"""
import os
import tempfile
import uuid
import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from utils.limiter import limiter
from sqlalchemy.orm import Session
import logging

from starlette.concurrency import run_in_threadpool
from models.user import Users
from utils.logger import log_event
from utils.deps import get_db, get_current_user
from utils.s3_manager import S3Manager
from utils.mastering_service import MasteringService
from schemas.mastering import MasteringResponse, GenreListResponse, GenrePreset, MasteredMusicRead
from models.mastered_music import MasteredMusic
from urllib.parse import urlparse
from utils.cache import redis_client  # shared Redis connection

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s:     %(message)s')

router = APIRouter(tags=["mastering"], prefix="/mastering")
s3_manager = S3Manager()
mastering_service = MasteringService()

# Log TTL: keep logs in Redis for 2 hours after last write
LOG_TTL_SECONDS = 7200


def _redis_log_key(process_id: str) -> str:
    return f"mastering:logs:{process_id}"


def _push_log(process_id: str, message: str) -> None:
    """Append a log entry to the Redis list for this process_id."""
    if not redis_client:
        return
    entry = json.dumps({"message": message, "timestamp": datetime.now().isoformat()})
    key = _redis_log_key(process_id)
    redis_client.rpush(key, entry)
    redis_client.expire(key, LOG_TTL_SECONDS)


def _fetch_logs(process_id: str) -> List[Dict[str, str]]:
    """Fetch all log entries from Redis for this process_id."""
    if not redis_client:
        return []
    key = _redis_log_key(process_id)
    raw = redis_client.lrange(key, 0, -1)
    return [json.loads(entry) for entry in raw]


def _init_logs(process_id: str) -> None:
    """Clear any stale logs for this process_id and reset TTL."""
    if not redis_client:
        return
    key = _redis_log_key(process_id)
    redis_client.delete(key)
    redis_client.expire(key, LOG_TTL_SECONDS)

@router.get("/logs/{process_id}")
async def get_processing_logs(process_id: str):
    """
    Get real-time processing logs for a specific mastering job.
    Logs are stored in Redis so all gunicorn workers share the same view.
    """
    logs = _fetch_logs(process_id)
    return {"process_id": process_id, "logs": logs}


@router.get("/genres", response_model=GenreListResponse)
async def get_available_genres():
    """
    Get list of all available genre presets for mastering
    
    Returns a dictionary of all 50+ genre presets with their mastering parameters.
    No authentication required.
    """
    try:
        genres = mastering_service.get_available_genres()
        
        # Convert to GenrePreset format
        genre_presets = {}
        for name, params in genres.items():
            genre_presets[name] = GenrePreset(
                name=name,
                lufs=params["lufs"],
                hp=params["hp"],
                lp=params["lp"],
                th=params["th"],
                ratio=params["ratio"]
            )
        
        return GenreListResponse(
            genres=genre_presets,
            total_count=len(genre_presets)
        )
    except Exception as e:
        logger.error(f"Error fetching genres: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch genre presets: {str(e)}"
        )





# @router.post("/master", response_model=MasteringResponse, status_code=status.HTTP_200_OK)
# # @limiter.limit("5/minute")
# async def master_audio_file(
#     # request: Request,
#     audio_file: UploadFile = File(..., description="Audio file to master (WAV or MP3)"),
#     genre: str = Form(..., description="Genre preset to use"),
#     quality_mode: str = Form(default="high", description="Quality mode: 'high' or 'normal'"),
#     process_id: str = Form(default=None, description="Unique ID for tracking progress logs"),
#     db: Session = Depends(get_db),
#     current_user: Users = Depends(get_current_user)
# ):
#     """
#     Master an audio file with professional processing
    
#     Upload an audio file and receive a professionally mastered version with:
#     - Genre-specific EQ and compression
#     - LUFS normalization
#     - Stereo enhancement
#     - Harmonic saturation
#     - High-quality 48kHz/24-bit output
    
#     **Supported Formats:** WAV (recommended), MP3
    
#     **Quality Modes:**
#     - `high`: 2x upsampling for superior quality (slower)
#     - `normal`: Standard processing (faster)
    
#     **Genre Presets:** Use GET /mastering/genres to see all available options
#     """
#     print("=" * 80)
#     print(f"🎵 MASTERING REQUEST RECEIVED")
#     print(f"📁 File: {audio_file.filename}")
#     print(f"🎸 Genre: {genre}")
#     print(f"⚡ Quality Mode: {quality_mode}")
#     print("=" * 80)
    
#     if not current_user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Authentication required to use mastering service"
#         )

    
    
#     # Validate genre
#     print("🔍 Validating genre preset...")
#     available_genres = mastering_service.get_available_genres()
#     if genre.lower() not in available_genres:
#         print(f"❌ Invalid genre: {genre}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Invalid genre '{genre}'. Use GET /mastering/genres to see available options."
#         )
#     print(f"✅ Genre '{genre}' validated")
    
#     # Validate quality mode
#     if quality_mode not in ["high", "normal"]:
#         print(f"❌ Invalid quality mode: {quality_mode}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Quality mode must be 'high' or 'normal'"
#         )
    
#     # Validate file type
#     file_extension = os.path.splitext(audio_file.filename)[1].lower()
#     print(f"🔍 Validating file type: {file_extension}")
#     if file_extension not in [".wav", ".mp3"]:
#         print(f"❌ Unsupported file type: {file_extension}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Only WAV and MP3 files are supported"
#         )
#     print(f"✅ File type validated")
    
#     # Create temporary files for processing
#     temp_input_path = None
#     temp_output_path = None
    
#     try:
#         # Initialize logs if process_id provided
#         if process_id:
#             processing_logs[process_id] = []
            
#         def log_step(msg: str):
#             print(f"[LOG] {msg}")
#             # Also log to centralized system
#             log_event("info", f"Mastering [{process_id or 'NO_ID'}]: {msg}")
            
#             if process_id:
#                 timestamp = datetime.now().isoformat()
#                 if process_id not in processing_logs:
#                     processing_logs[process_id] = []
#                 processing_logs[process_id].append({
#                     "message": msg,
#                     "timestamp": timestamp
#                 })
#                 print(f"DEBUG: Appended log to {process_id}, current count: {len(processing_logs[process_id])}")

#         # Create temp directory
#         print("📂 Creating temporary directory...")
#         temp_dir = tempfile.mkdtemp()
#         print(f"✅ Temp directory created: {temp_dir}")
        
#         # Save uploaded file
#         temp_input_path = os.path.join(temp_dir, f"input_{uuid.uuid4()}{file_extension}")
#         print(f"💾 Saving uploaded file to: {temp_input_path}")
#         with open(temp_input_path, "wb") as f:
#             content = await audio_file.read()
#             f.write(content)
        
#         file_size_mb = os.path.getsize(temp_input_path) / (1024 * 1024)
#         print(f"✅ File saved successfully ({file_size_mb:.2f} MB)")
        
#         # Create output path
#         temp_output_path = os.path.join(temp_dir, f"mastered_{uuid.uuid4()}.wav")
#         print(f"📝 Output path: {temp_output_path}")
        
#         # Process the audio
#         print("🎚️ Starting mastering process...")
#         print(f"   Genre: {genre}")
#         print(f"   Quality: {quality_mode}")
        
#         processing_result = await run_in_threadpool(
#             mastering_service.master_audio,
#             input_path=temp_input_path,
#             output_path=temp_output_path,
#             genre=genre,
#             quality_mode=quality_mode,
#             log_callback=log_step
#         )
        
#         print("✅ Mastering complete!")
#         print(f"   Original LUFS: {processing_result['original_lufs']:.1f}")
#         print(f"   Target LUFS: {processing_result['target_lufs']}")
#         print(f"   Processing time: {processing_result['processing_time']:.2f}s")
        
#         # Prepare upload paths
#         original_name = os.path.splitext(audio_file.filename)[0]
#         s3_filename = f"{original_name}_mastered_{genre}_{uuid.uuid4().hex[:8]}.wav"
#         s3_key = f"mastered/{s3_filename}"

#         print("☁️  Starting parallel uploads to S3...")
#         # We don't log S3 uploads to the frontend as per user request
        
#         mastered_task = run_in_threadpool(
#             s3_manager.upload_file,
#             file_path=temp_output_path,
#             s3_key=s3_key
#         )
        
#         original_name_base = os.path.splitext(audio_file.filename)[0]
#         original_s3_filename = f"{original_name_base}_original_{uuid.uuid4().hex[:8]}{file_extension}"
#         original_s3_key = f"mastered/{original_s3_filename}"
        
#         original_task = run_in_threadpool(
#             s3_manager.upload_file,
#             file_path=temp_input_path,
#             s3_key=original_s3_key
#         )
        
#         # Run uploads in parallel
#         mastered_url, original_music_url = await asyncio.gather(mastered_task, original_task)
        
#         if not mastered_url or not original_music_url:
#             raise Exception("Failed to upload files to S3")
        
#         print(f"✅ Parallel uploads complete: {s3_key} and {original_s3_key}")
#         # We don't log S3 uploads to the frontend as per user request

#         # Generate presigned URL for download (valid for 1 hour)
#         presigned_url = s3_manager.generate_presigned_url_for_download(s3_key, expiration=3600)
#         original_presigned_url = s3_manager.generate_presigned_url_for_download(original_s3_key, expiration=3600)
#         print(f"🔗 Download URLs generated (valid for 1 hour)")
        
#         # Store in database
#         print("🗄️  Storing mastered music details in database...")
#         try:
#             new_mastered = MasteredMusic(
#                 user_id=current_user.id,
#                 name=audio_file.filename,
#                 genre=processing_result["genre"],
#                 mastered_url=mastered_url,  # Store the actual S3 URL
#                 original_music_url=original_music_url,
#                 original_lufs=processing_result["original_lufs"],
#                 target_lufs=processing_result["target_lufs"],
#                 profile=processing_result["profile"],
#                 quality_mode=processing_result["quality_mode"],
#                 sample_rate=processing_result["sample_rate"],
#                 bit_depth=processing_result["bit_depth"],
#                 processing_time=processing_result["processing_time"],
#                 settings=processing_result["settings"]
#             )
#             db.add(new_mastered)
#             db.commit()
#             db.refresh(new_mastered)
#             print(f"✅ Stored in DB with ID: {new_mastered.id}")
#         except Exception as db_error:
#             db.rollback()
#             print(f"⚠️ Failed to store in DB: {db_error}")
#             # We don't raise an exception here because the mastering was successful
#             # and the user should still get their file.
        
#         # Return response
#         print("📦 Generating response...")
#         response = MasteringResponse(
#             mastered_url=presigned_url,
#             original_music_url=original_presigned_url,
#             original_lufs=processing_result["original_lufs"],
#             target_lufs=processing_result["target_lufs"],
#             genre=processing_result["genre"],
#             profile=processing_result["profile"],
#             quality_mode=processing_result["quality_mode"],
#             sample_rate=processing_result["sample_rate"],
#             bit_depth=processing_result["bit_depth"],
#             processing_time=processing_result["processing_time"],
#             settings=processing_result["settings"]
#         )
#         print("=" * 80)
#         print("🎉 MASTERING REQUEST COMPLETED SUCCESSFULLY")
#         print("=" * 80)
#         return response
        
#     except ValueError as ve:
#         logger.error("=" * 80)
#         logger.error(f"❌ VALIDATION ERROR: {ve}")
#         logger.error("=" * 80)
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=str(ve)
#         )
#     except Exception as e:
#         logger.error("=" * 80)
#         logger.error(f"❌ MASTERING ERROR: {e}")
#         logger.error("=" * 80)
#         logger.error(f"Error during mastering process: {e}", exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to master audio file: {str(e)}"
#         )
#     finally:
#         # Clean up temporary files
#         print("🧹 Cleaning up temporary files...")
#         try:
#             if temp_input_path and os.path.exists(temp_input_path):
#                 os.remove(temp_input_path)
#                 print(f"   Removed input: {os.path.basename(temp_input_path)}")
#             if temp_output_path and os.path.exists(temp_output_path):
#                 os.remove(temp_output_path)
#                 print(f"   Removed output: {os.path.basename(temp_output_path)}")
#             if temp_dir and os.path.exists(temp_dir):
#                 os.rmdir(temp_dir)
#                 print(f"   Removed directory")
#             print("✅ Cleanup complete")
#         except Exception as cleanup_error:
#             print(f"⚠️ Error cleaning up temporary files: {cleanup_error}")
            
#         # Clean up logs after a delay (handled by frontend polling stop or TLL)

#     #     # For simple implementation, we can leave them or clear after some time.
#     #     # Here we won't clear immediately so the frontend can fetch the last logs.


@router.post("/master")
@limiter.limit("20/hour")  # Mastering is CPU-intensive
async def master_audio(
    request: Request,
    genre: str = Form(...),
    quality_mode: str = Form(...),
    process_id: str = Form(None),

    # 🔥 KEY CHANGE
    audio_file: UploadFile | None = File(None),
    track_id: int | None = Form(None),

    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    - New master → audio_file required
    - Remaster → track_id required
    """


    # -----------------------------
    # 1️⃣ VALIDATION & LOGGING SETUP
    # -----------------------------
    
    # Auto-generate process_id if not provided
    if not process_id:
        process_id = str(uuid.uuid4())
    
    if not audio_file and not track_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either audio_file or track_id must be provided"
        )

    is_remaster = audio_file is None and track_id is not None
    
    # Initialize logs in Redis (clears any stale data from a previous run with same ID)
    if process_id:
        _init_logs(process_id)

    def log_step(msg: str):
        print(f"[LOG] {msg}")
        log_event("info", f"Mastering [{process_id or 'NO_ID'}]: {msg}")
        if process_id:
            _push_log(process_id, msg)

    # -----------------------------
    # 2️⃣ PREPARE INPUT AUDIO
    # -----------------------------
    temp_dir = tempfile.mkdtemp()
    temp_input_path = None
    input_filename = ""
    file_ext = ""

    try:
        if is_remaster:
            log_step("Fetching original track for remastering...")
            # 🔁 RE-MASTER FLOW
            mastered_track = db.query(MasteredMusic).filter(
                MasteredMusic.id == track_id,
                MasteredMusic.user_id == current_user.id
            ).first()

            if not mastered_track:
                raise HTTPException(404, "Track not found")

            # Extract S3 key from stored URL
            parsed_url = urlparse(mastered_track.original_music_url)
            original_s3_key = parsed_url.path.lstrip("/")
            
            # If the path starts with bucket name (happens with some S3 URL formats)
            if original_s3_key.startswith(s3_manager.bucket_name):
                original_s3_key = original_s3_key[len(s3_manager.bucket_name):].lstrip("/")

            input_filename = mastered_track.name
            file_ext = os.path.splitext(original_s3_key)[1].lower()

            if file_ext not in [".mp3", ".wav"]:
                file_ext = ".wav" # Default if unknown

            # Download original audio from S3
            temp_input_path = os.path.join(temp_dir, f"input_{uuid.uuid4().hex}{file_ext}")
            await run_in_threadpool(
                s3_manager.download_file,
                key=original_s3_key,
                destination_path=temp_input_path
            )
        else:
            # 🆕 NEW MASTER FLOW
            input_filename = audio_file.filename
            file_ext = os.path.splitext(input_filename)[1].lower()

            if file_ext not in [".mp3", ".wav"]:
                raise HTTPException(400, "Unsupported audio format")

            temp_input_path = os.path.join(temp_dir, f"input_{uuid.uuid4().hex}{file_ext}")
            with open(temp_input_path, "wb") as f:
                content = await audio_file.read()
                f.write(content)
            log_step(f"Uploaded: {input_filename}")

        # -----------------------------
        # 3️⃣ MASTERING PROCESS
        # -----------------------------
        temp_output_path = os.path.join(temp_dir, f"mastered_{uuid.uuid4().hex}.wav")
        log_step("Starting mastering process...")
        
        processing_result = await run_in_threadpool(
            mastering_service.master_audio,
            input_path=temp_input_path,
            output_path=temp_output_path,
            genre=genre,
            quality_mode=quality_mode,
            log_callback=log_step
        )
        
        log_step("Mastering complete!")

        # -----------------------------
        # 4️⃣ S3 UPLOAD (PARALLEL)
        # -----------------------------
        base_name = os.path.splitext(input_filename)[0]
        mastered_s3_filename = f"{base_name}_mastered_{genre}_{uuid.uuid4().hex[:8]}.wav"
        mastered_s3_key = f"mastered/{mastered_s3_filename}"
        
        orig_s3_key = None
        if not is_remaster:
            orig_s3_filename = f"{base_name}_original_{uuid.uuid4().hex[:8]}{file_ext}"
            orig_s3_key = f"mastered/{orig_s3_filename}"

        log_step("Saving mastered track...")
        
        # Prepare tasks
        mastered_task = run_in_threadpool(
            s3_manager.upload_file,
            file_path=temp_output_path,
            s3_key=mastered_s3_key
        )
        
        tasks = [mastered_task]
        if not is_remaster:
            original_task = run_in_threadpool(
                s3_manager.upload_file,
                file_path=temp_input_path,
                s3_key=orig_s3_key
            )
            tasks.append(original_task)
        
        # Run in parallel
        results = await asyncio.gather(*tasks)
        mastered_url = results[0]
        original_url = results[1] if not is_remaster else mastered_track.original_music_url

        if not mastered_url or (not is_remaster and not original_url):
            raise Exception("Failed to upload files to S3")

        # -----------------------------
        # 5️⃣ DB INSERT
        # -----------------------------
        new_record = MasteredMusic(
            user_id=current_user.id,
            name=base_name,
            genre=genre,
            mastered_url=mastered_url,
            original_music_url=original_url,
            original_lufs=processing_result["original_lufs"],
            target_lufs=processing_result["target_lufs"],
            profile=processing_result["profile"],
            quality_mode=quality_mode,
            sample_rate=processing_result["sample_rate"],
            bit_depth=processing_result["bit_depth"],
            processing_time=processing_result["processing_time"],
            settings=processing_result["settings"],
            process_id=process_id,
            is_remaster=1 if is_remaster else 0
        )

        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        log_step("Saved to library!")

        # Generate presigned URLs for response
        presigned_mastered = s3_manager.generate_presigned_url_for_download(mastered_s3_key)
        presigned_original = s3_manager.generate_presigned_url_for_download(
            orig_s3_key if not is_remaster else urlparse(original_url).path.lstrip("/")
        )

        return MasteringResponse(
            mastered_url=presigned_mastered,
            original_music_url=presigned_original,
            original_lufs=processing_result["original_lufs"],
            target_lufs=processing_result["target_lufs"],
            genre=processing_result["genre"],
            profile=processing_result["profile"],
            quality_mode=processing_result["quality_mode"],
            sample_rate=processing_result["sample_rate"],
            bit_depth=processing_result["bit_depth"],
            processing_time=processing_result["processing_time"],
            settings=processing_result["settings"]
        )

    except Exception as e:
        log_event("error", f"Mastering failed: {str(e)}")
        logger.error(f"Mastering error: {e}", exc_info=True)
        raise HTTPException(500, detail=str(e))
    finally:
        # Cleanup
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except:
                pass


@router.get("/mastered", response_model=List[MasteredMusicRead])
async def get_user_mastered_music(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """
    Get all mastered music records for the authenticated user
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    mastered_list = db.query(MasteredMusic).filter(MasteredMusic.user_id == current_user.id).order_by(MasteredMusic.created_at.desc()).all()
    
    # Generate presigned URLs for each record
    for item in mastered_list:
        try:
            
            if any(provider in item.mastered_url for provider in ["s3.amazonaws.com"]):
                
                url_parts = item.mastered_url.split('/')
                if len(url_parts) > 3:
                    s3_key = '/'.join(url_parts[3:])

                    s3_key = s3_key.split('?')[0]
                    item.mastered_url = s3_manager.generate_presigned_url_for_download(s3_key, expiration=3600)
            if hasattr(item, 'original_music_url') and item.original_music_url and any(provider in item.original_music_url for provider in ["s3.amazonaws.com"]):
                url_parts = item.original_music_url.split('/')
                if len(url_parts) > 3:
                    s3_key = '/'.join(url_parts[3:])
                    s3_key = s3_key.split('?')[0]
                    item.original_music_url = s3_manager.generate_presigned_url_for_download(s3_key, expiration=3600)

        except Exception as e:
            logger.error(f"Error generating presigned URL for item {item.id}: {e}")
            print(f"Error generating presigned URL for item {item.id}: {e}")
                
    return mastered_list




# delete mastering
@router.delete("/{track_id}")
async def delete_mastered_track(
    track_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """
    Delete a mastered track and its associated files from S3
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Find the mastered track
    mastered_track = db.query(MasteredMusic).filter(
        MasteredMusic.id == track_id,
        MasteredMusic.user_id == current_user.id
    ).first()
    
    if not mastered_track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mastered track not found"
        )
    
    # Delete from S3
    try:
        # Delete mastered file
        if mastered_track.mastered_url:
            parsed_url = urlparse(mastered_track.mastered_url)
            mastered_s3_key = parsed_url.path.lstrip("/")
            
            # Handle cases where URL includes bucket name
            if mastered_s3_key.startswith(s3_manager.bucket_name):
                mastered_s3_key = mastered_s3_key[len(s3_manager.bucket_name):].lstrip("/")
            
            # Delete from S3
            s3_manager.delete_file(mastered_s3_key)
            logger.info(f"Deleted mastered file from S3: {mastered_s3_key}")
            
        # Delete original file if it was uploaded
        if hasattr(mastered_track, 'original_music_url') and mastered_track.original_music_url:
            parsed_url = urlparse(mastered_track.original_music_url)
            original_s3_key = parsed_url.path.lstrip("/")
            
            # Handle cases where URL includes bucket name
            if original_s3_key.startswith(s3_manager.bucket_name):
                original_s3_key = original_s3_key[len(s3_manager.bucket_name):].lstrip("/")
            
            # Delete from S3
            s3_manager.delete_file(original_s3_key)
            logger.info(f"Deleted original file from S3: {original_s3_key}")
            
    except Exception as e:
        logger.error(f"Error deleting files from S3 for track {track_id}: {e}")
        # Don't fail the whole deletion if S3 deletion fails
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete mastered track from S3: {str(e)}"
        )
    
    # Delete from database
    try:
        db.delete(mastered_track)
        db.commit()
        logger.info(f"Deleted mastered track from database: {track_id}")
        
        return {
            "message": "Mastered track deleted successfully",
            "track_id": track_id
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting mastered track from database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete mastered track: {str(e)}"
        )
