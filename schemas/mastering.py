from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


class MasteringRequest(BaseModel):
    """Request model for audio mastering"""
    genre: str = Field(..., description="Genre preset to use for mastering")
    quality_mode: str = Field(default="high", description="Quality mode: 'high' or 'normal'")


class MasteringResponse(BaseModel):
    """Response model for mastering operation"""
    mastered_url: str = Field(..., description="Presigned S3 URL to download mastered file")
    original_lufs: float = Field(..., description="Original loudness in LUFS")
    original_music_url: str = Field(..., description="Presigned S3 URL to download original music file")
    target_lufs: float = Field(..., description="Target loudness in LUFS")
    genre: str = Field(..., description="Genre preset used")
    profile: str = Field(..., description="Mastering profile applied (club/clean/speech/neutral)")
    quality_mode: str = Field(..., description="Quality mode used")
    sample_rate: int = Field(..., description="Output sample rate in Hz")
    bit_depth: str = Field(..., description="Output bit depth")
    processing_time: float = Field(..., description="Processing time in seconds")
    settings: Dict = Field(..., description="Detailed mastering settings applied")


class MasteredMusicRead(BaseModel):
    """Schema for reading mastered music details from DB"""
    id: int
    user_id: int
    name: str
    genre: str
    mastered_url: str
    original_music_url: str
    original_lufs: float
    target_lufs: float
    profile: str
    quality_mode: str
    sample_rate: int
    bit_depth: str
    processing_time: float
    settings: Dict
    created_at: datetime

    class Config:
        from_attributes = True


class GenrePreset(BaseModel):
    """Genre preset configuration"""
    name: str = Field(..., description="Genre name")
    lufs: int = Field(..., description="Target LUFS loudness")
    hp: int = Field(..., description="High-pass filter frequency in Hz")
    lp: int = Field(..., description="Low-pass filter frequency in Hz")
    threshold: int = Field(..., alias="th", description="Compression threshold in dB")
    ratio: float = Field(..., description="Compression ratio")


class GenreListResponse(BaseModel):
    """Response model for genre list"""
    genres: Dict[str, GenrePreset] = Field(..., description="Available genre presets")
    total_count: int = Field(..., description="Total number of genres")
