from pydantic import BaseModel, Field
from typing import Optional, Literal

class ThumbnailRequest(BaseModel):
    """Request model for thumbnail generation"""
    track_name: str = Field(..., description="Name of the music track")
    genre: str = Field(..., description="Genre of the track (e.g., 'lofi', 'hiphop')")
    mood: str = Field(..., description="Mood of the track (e.g., 'chill', 'energetic')")
    size: str = Field(default="square", description="Size preset: 'square', 'youtube', 'youtube_max', 'spotify', 'soundcloud'")
    quality: str = Field(default="hd", description="Quality hint: 'hd' or 'standard'")

# class ThumbnailResponse(BaseModel):
#     """Response model for thumbnail generation"""
#     image_url: str = Field(..., description="Presigned S3 URL to download the thumbnail")
#     track_name: str = Field(..., description="Track name used")
#     genre: str = Field(..., description="Genre used")
#     mood: str = Field(..., description="Mood used")
#     size: str = Field(..., description="Size preset used")
#     width: int = Field(..., description="Image width in pixels")
#     height: int = Field(..., description="Image height in pixels")
#     prompt: Optional[str] = Field(None, description="Prompt used for generation (debug info)")
class ThumbnailRequest(BaseModel):
    track_name: str
    genre: str
    mood: str
    font_style: Literal["bold", "regular", "serif", "serif_bold", "mono", "mono_bold"] = Field(
        default="bold",
        description="Font style for frontend text overlay (not used in image generation)"
    )

class ThumbnailResponse(BaseModel):
    image_url: str
    track_name: str
    genre: str
    mood: str
    font_style: str  # Return font_style for frontend to use
    width: int
    height: int
    prompt: str | None = None
