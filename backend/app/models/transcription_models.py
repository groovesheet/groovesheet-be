"""
Pydantic models for AnNOTEator transcription API
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict
from enum import Enum


class TranscriptionMethod(str, Enum):
    """Transcription method options"""
    ANNOTEATOR = "annoteator"


class TranscriptionRequest(BaseModel):
    """Request model for audio file transcription"""
    method: TranscriptionMethod = Field(
        default=TranscriptionMethod.ANNOTEATOR,
        description="Transcription method to use"
    )
    song_title: str = Field(
        default="Drum Transcription",
        description="Title for the sheet music"
    )


class YouTubeTranscriptionRequest(BaseModel):
    """Request model for YouTube URL transcription"""
    url: HttpUrl = Field(..., description="YouTube video URL")
    method: TranscriptionMethod = Field(
        default=TranscriptionMethod.ANNOTEATOR,
        description="Transcription method to use"
    )
    song_title: Optional[str] = Field(
        default=None,
        description="Title for the sheet music (uses video title if not provided)"
    )


class TranscriptionResponse(BaseModel):
    """Response model for transcription"""
    success: bool
    message: str
    session_id: Optional[str] = None
    musicxml_path: Optional[str] = None
    metadata: Optional[Dict] = None
    download_url: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Transcription completed successfully",
                "session_id": "abc123",
                "musicxml_path": "/path/to/output.musicxml",
                "metadata": {
                    "total_notes": 450,
                    "bpm": 120.5,
                    "duration_seconds": 180.0,
                    "instruments_detected": {
                        "Kick Drum": 120,
                        "Snare Drum": 100,
                        "Hi-Hat": 200
                    }
                },
                "download_url": "/api/annoteator/download/abc123"
            }
        }
