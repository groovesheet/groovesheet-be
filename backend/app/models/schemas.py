"""
Pydantic models for API request/response
"""
from typing import Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    """Processing status enum"""
    PENDING = "pending"
    SEPARATING = "separating"
    TRANSCRIBING = "transcribing"
    GENERATING_SHEET = "generating_sheet"
    COMPLETED = "completed"
    FAILED = "failed"


class TranscriptionJobCreate(BaseModel):
    """Request model for creating a transcription job"""
    filename: str = Field(..., description="Original filename of the audio file")


class TranscriptionJobResponse(BaseModel):
    """Response model for transcription job"""
    job_id: str = Field(..., description="Unique job identifier")
    status: ProcessingStatus = Field(..., description="Current processing status")
    filename: str = Field(..., description="Original filename")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    message: Optional[str] = Field(None, description="Status message or error details")
    progress: int = Field(0, description="Processing progress percentage (0-100)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "abc123-def456",
                "status": "completed",
                "filename": "my_song.mp3",
                "created_at": "2024-01-01T12:00:00",
                "updated_at": "2024-01-01T12:05:00",
                "message": "Processing completed successfully",
                "progress": 100
            }
        }


class TranscriptionJobStatus(BaseModel):
    """Model for job status check"""
    job_id: str
    status: ProcessingStatus
    progress: int
    message: Optional[str] = None
    result_url: Optional[str] = Field(None, description="URL to download the result PDF")
    midi_url: Optional[str] = Field(None, description="URL to download the MIDI file")
    drum_audio_url: Optional[str] = Field(None, description="URL to download the separated drum audio")


class TranscriptionResult(BaseModel):
    """Model for transcription result"""
    job_id: str
    musicxml_path: str = Field(..., description="Path to generated MusicXML file")
    midi_path: str = Field(..., description="Path to transcribed MIDI file")
    drum_audio_path: str = Field(..., description="Path to separated drum audio")
    processing_time: float = Field(..., description="Total processing time in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "abc123-def456",
                "musicxml_path": "/outputs/abc123-def456/drum_sheet.musicxml",
                "midi_path": "/outputs/abc123-def456/drums.mid",
                "drum_audio_path": "/outputs/abc123-def456/drums.wav",
                "processing_time": 45.67
            }
        }


class ErrorResponse(BaseModel):
    """Model for error responses"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "ProcessingError",
                "message": "Failed to process audio file",
                "details": {"step": "separation", "reason": "Invalid audio format"}
            }
        }


class HealthCheckResponse(BaseModel):
    """Model for health check response"""
    status: str
    version: str
    models_loaded: bool
    gpu_available: bool
    timestamp: datetime
