"""
AnNOTEator transcription API endpoints
"""
import os
import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse

from app.models.transcription_models import TranscriptionResponse
from app.services.annoteator_service import AnNOTEatorService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/annoteator", tags=["AnNOTEator"])

# Initialize service
annoteator_service = AnNOTEatorService(output_dir=settings.OUTPUT_DIR)


@router.post("/upload", response_model=TranscriptionResponse)
async def transcribe_upload(
    file: UploadFile = File(..., description="Audio file (mp3, wav, flac, etc.)"),
    song_title: str = Form(default="Drum Transcription", description="Title for the sheet music"),
    background_tasks: BackgroundTasks = None
):
    """
    Transcribe uploaded audio file using AnNOTEator
    
    This endpoint accepts an audio file and transcribes it to drum sheet music (MusicXML format).
    
    **Parameters:**
    - **file**: Audio file (mp3, wav, flac, ogg, m4a)
    - **song_title**: Title for the generated sheet music
    
    **Returns:**
    - MusicXML file path and metadata about the transcription
    
    **Example:**
    ```python
    import requests
    
    with open("drums.mp3", "rb") as f:
        files = {"file": f}
        data = {"song_title": "My Song"}
        response = requests.post("http://localhost:8000/api/annoteator/upload", files=files, data=data)
    ```
    """
    session_id = str(uuid.uuid4())[:8]
    
    # Validate file type
    allowed_extensions = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac'}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file_ext}'. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Save uploaded file
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    temp_audio = upload_dir / f"upload_{session_id}{file_ext}"
    
    try:
        logger.info(f"[{session_id}] Receiving file: {file.filename}")
        
        # Save file
        with open(temp_audio, "wb") as f:
            content = await file.read()
            f.write(content)
        
        file_size_mb = len(content) / (1024 * 1024)
        logger.info(f"[{session_id}] File saved: {temp_audio} ({file_size_mb:.2f} MB)")
        
        # Transcribe with AnNOTEator
        logger.info(f"[{session_id}] Starting AnNOTEator transcription...")
        musicxml_path, metadata = annoteator_service.transcribe_audio(
            audio_path=str(temp_audio),
            output_name=f"transcription_{session_id}",
            song_title=song_title
        )
        
        # Schedule cleanup of uploaded file
        if background_tasks:
            background_tasks.add_task(os.unlink, temp_audio)
        
        logger.info(f"[{session_id}] Transcription completed successfully")
        
        return TranscriptionResponse(
            success=True,
            message="Transcription completed successfully",
            session_id=session_id,
            musicxml_path=musicxml_path,
            metadata=metadata,
            download_url=f"/api/annoteator/download/{session_id}"
        )
        
    except Exception as e:
        logger.error(f"[{session_id}] Transcription failed: {e}", exc_info=True)
        
        # Cleanup on error
        if temp_audio.exists():
            os.unlink(temp_audio)
        
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


@router.get("/download/{session_id}")
async def download_musicxml(session_id: str):
    """
    Download transcribed MusicXML file by session ID
    
    **Parameters:**
    - **session_id**: Session ID returned from the transcription endpoint
    
    **Returns:**
    - MusicXML file for download
    """
    output_dir = Path(settings.OUTPUT_DIR)
    file_path = output_dir / f"transcription_{session_id}.musicxml"
    
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        raise HTTPException(
            status_code=404,
            detail=f"Transcription file not found. Session ID: {session_id}"
        )
    
    logger.info(f"Serving file: {file_path}")
    
    return FileResponse(
        path=str(file_path),
        media_type="application/vnd.recordare.musicxml+xml",
        filename=f"transcription_{session_id}.musicxml",
        headers={
            "Content-Disposition": f'attachment; filename="drum_transcription_{session_id}.musicxml"'
        }
    )


@router.post("/cleanup")
async def cleanup_temp_files(max_age_hours: int = 24):
    """
    Clean up old temporary files
    
    **Parameters:**
    - **max_age_hours**: Maximum age of files to keep (default: 24 hours)
    
    **Returns:**
    - Number of files cleaned up
    """
    try:
        cleaned_count = annoteator_service.cleanup_old_files(max_age_hours=max_age_hours)
        return {
            "success": True,
            "message": f"Cleaned up {cleaned_count} old files",
            "cleaned_count": cleaned_count
        }
    except Exception as e:
        logger.error(f"Cleanup failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Check if AnNOTEator service is healthy"""
    try:
        model_exists = annoteator_service.model_path.exists()
        return {
            "status": "healthy" if model_exists else "unhealthy",
            "model_path": str(annoteator_service.model_path),
            "model_exists": model_exists,
            "output_dir": str(annoteator_service.output_dir)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
