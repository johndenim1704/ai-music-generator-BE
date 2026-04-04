import logging
from fastapi import APIRouter, HTTPException, Request, Form, UploadFile, File
from utils.limiter import limiter
from schemas.album_cover import AlbumCoverRequest, AlbumCoverResponse
from utils.album_cover_service import AlbumCoverService

router = APIRouter(tags=["album-covers"], prefix="/album-covers")
service = AlbumCoverService()
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=AlbumCoverResponse)
@limiter.limit("3/minute")  # Album cover generation is expensive
async def generate_album_cover(
    request: Request,
    album_request: AlbumCoverRequest
):
    """
    Generate an AI-powered album cover using Llama 3.2 and Stable Diffusion 1.5.
    
    This endpoint:
    1. Uses Llama 3.2 (via Ollama) to generate an image prompt based on track name and genre
    2. Generates a unique album cover image using Stable Diffusion 1.5
    3. Adds styled text overlay with the track name
    4. Uploads the final image to S3
    5. Returns the S3 URL and generation details
    
    **Quality Presets:**
    - `fast`: 15 inference steps (~10-30 seconds)
    - `balanced`: 25 inference steps (~30-60 seconds) - recommended
    - `high`: 35 inference steps (~60-120 seconds)
    
    **Note:** First request may take longer as the Stable Diffusion model is loaded into memory.
    """
    logger.info(f"[ALBUM_COVER_API] Request received - Track: {album_request.track_name}, Genre: {album_request.genre}")
    logger.info(f"[ALBUM_COVER_API] Quality: {album_request.quality}, Add text: {album_request.add_text}")
    
    # Validate quality preset
    valid_qualities = ["fast", "balanced", "high"]
    if album_request.quality.lower() not in valid_qualities:
        logger.error(f"[ALBUM_COVER_API] Invalid quality preset: {album_request.quality}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid quality preset. Must be one of: {', '.join(valid_qualities)}"
        )
    
    try:
        logger.info("[ALBUM_COVER_API] Starting album cover generation...")
        
        # Generate album cover
        cover_url, image_prompt, text_style = service.generate_album_cover(
            track_name=album_request.track_name,
            genre=album_request.genre,
            quality=album_request.quality,
            add_text=album_request.add_text,
        )
        
        logger.info(f"[ALBUM_COVER_API] Generation successful!")
        logger.info(f"[ALBUM_COVER_API] Cover URL: {cover_url}")
        logger.debug(f"[ALBUM_COVER_API] Image prompt: {image_prompt}")
        logger.debug(f"[ALBUM_COVER_API] Text style: {text_style}")
        
        return AlbumCoverResponse(
            cover_url=cover_url,
            image_prompt=image_prompt,
            text_style=text_style
        )
    
    except ConnectionError as e:
        logger.error(f"[ALBUM_COVER_API] Ollama connection error: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Failed to connect to Ollama. Please ensure Ollama is running and accessible."
        )
    
    except ValueError as e:
        logger.error(f"[ALBUM_COVER_API] Validation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(f"[ALBUM_COVER_API] Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Album cover generation failed: {str(e)}"
        )
