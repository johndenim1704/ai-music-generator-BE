import tempfile, requests, os
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from utils.limiter import limiter
from utils.track_title_service import TrackTitleService
from schemas.track_title import TitleResponse

router = APIRouter(tags=["titles"], prefix="/titles")
service = TrackTitleService()
logger = logging.getLogger(__name__)

@router.post("/generate", response_model=TitleResponse)
@limiter.limit("10/minute")  # Allow 10 requests per minute
async def generate_titles(
    request: Request,
    genre: str = Form(...),
    num_titles: int = Form(1),
    audio_file: UploadFile = File(None),
    audio_url: str = Form(None)
):
    """
    User can either upload an audio file OR provide an audio URL.
    """
    logger.info(f"[TRACK_TITLE] Request received - Genre: {genre}, Num Titles: {num_titles}")
    logger.info(f"[TRACK_TITLE] Audio file provided: {audio_file is not None}, Audio URL provided: {audio_url is not None}")
    
    if not audio_file and not audio_url:
        logger.error("[TRACK_TITLE] No audio source provided")
        raise HTTPException(status_code=400, detail="Provide audio_file or audio_url")

    tmp_path = None

    try:
        # If user uploads a file
        if audio_file:
            logger.info(f"[TRACK_TITLE] Processing uploaded file: {audio_file.filename}")
            fd, tmp_path = tempfile.mkstemp(suffix=os.path.splitext(audio_file.filename)[1])
            with os.fdopen(fd, "wb") as f:
                f.write(await audio_file.read())
            logger.info(f"[TRACK_TITLE] File saved to temporary path: {tmp_path}")

        # If user provides URL
        elif audio_url:
            logger.info(f"[TRACK_TITLE] Downloading audio from URL: {audio_url}")
            resp = requests.get(audio_url)
            if resp.status_code != 200:
                logger.error(f"[TRACK_TITLE] Audio download failed with status: {resp.status_code}")
                raise Exception("Audio download failed")
            fd, tmp_path = tempfile.mkstemp(suffix=".wav")
            os.write(fd, resp.content)
            os.close(fd)
            logger.info(f"[TRACK_TITLE] Audio downloaded to: {tmp_path}")

        logger.info(f"[TRACK_TITLE] Starting title generation service...")
        titles = service.generate_titles(tmp_path, genre=genre, num_titles=num_titles)
        logger.info(f"[TRACK_TITLE] Title generation completed successfully")
        logger.debug(f"[TRACK_TITLE] Generated titles: {titles}")
        return TitleResponse(titles=titles)

    except Exception as e:
        logger.error(f"[TRACK_TITLE] Error occurred: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if tmp_path and os.path.exists(tmp_path):
            logger.info(f"[TRACK_TITLE] Cleaning up temporary file: {tmp_path}")
            os.remove(tmp_path)
