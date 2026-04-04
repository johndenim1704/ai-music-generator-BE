from pydantic import BaseModel, Field
from typing import Dict


class AlbumCoverRequest(BaseModel):
    """Request model for album cover generation"""
    track_name: str = Field(..., description="Name of the music track", min_length=1, max_length=100)
    genre: str = Field(..., description="Music genre (e.g., hiphop, lofi, edm, jazz, rock)", min_length=1, max_length=50)
    quality: str = Field(default="balanced", description="Quality preset: 'fast' (15 steps), 'balanced' (25 steps), or 'high' (35 steps)")
    add_text: bool = Field(default=True, description="Whether to add track name overlay to the cover")

    class Config:
        json_schema_extra = {
            "example": {
                "track_name": "Midnight Vibes",
                "genre": "lofi",
                "quality": "balanced",
                "add_text": True
            }
        }


class AlbumCoverResponse(BaseModel):
    """Response model for album cover generation"""
    cover_url: str = Field(..., description="S3 URL of the generated album cover")
    image_prompt: str = Field(..., description="The AI-generated image prompt used for Stable Diffusion")
    text_style: Dict = Field(..., description="Text styling information (font, color, effects)")

    class Config:
        json_schema_extra = {
            "example": {
                "cover_url": "https://ai-music-generator-1.s3.amazonaws.com/album-covers/Midnight_Vibes_a1b2c3d4.png",
                "image_prompt": "A dreamy lo-fi scene with soft pastel purples and pinks, featuring abstract floating geometric shapes against a hazy city skyline at dusk, minimalist and calming atmosphere",
                "text_style": {
                    "font_family": "DejaVu Serif",
                    "color": "white",
                    "position": "center",
                    "effects": "shadow"
                }
            }
        }
