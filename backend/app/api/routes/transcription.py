"""
Transcription endpoints
"""
import os
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse

from app.models.schemas import (
    TranscriptionJobResponse,
    TranscriptionJobStatus,
    ProcessingStatus,
    ErrorResponse
)
from app.services.processing_service import ProcessingService
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


# Global processing service (will be initialized per request from app state)
def get_processing_service(request: Request) -> ProcessingService:
    """Get or create processing service"""
    if not hasattr(request.app.state, 'processing_service'):
        request.app.state.processing_service = ProcessingService(
            request.app.state.model_manager
        )
    return request.app.state.processing_service


@router.post("/transcribe", response_model=TranscriptionJobResponse)
async def upload_and_transcribe(
    background_tasks: BackgroundTasks,
    request: Request,
    audio_file: UploadFile = File(..., description="Audio file (MP3, WAV)")
):
    """
    Upload an audio file and start drum transcription
    
    This endpoint accepts an audio file (MP3 or WAV), validates it,
    and creates a background job to:
    1. Separate drum track using Demucs
    2. Transcribe drums to MIDI using Omnizart
    3. Generate PDF sheet music
    
    Returns:
        Job information with job_id for status tracking
    """
    try:
        # Validate file
        if not audio_file.content_type in settings.ALLOWED_AUDIO_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file format. Allowed formats: {settings.ALLOWED_AUDIO_FORMATS}"
            )
        
        # Check file size
        file_size = 0
        chunk_size = 1024 * 1024  # 1MB chunks
        temp_chunks = []
        
        while True:
            chunk = await audio_file.read(chunk_size)
            if not chunk:
                break
            file_size += len(chunk)
            temp_chunks.append(chunk)
            
            if file_size > settings.MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / (1024*1024)}MB"
                )
        
        # Save file
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(audio_file.filename)[1]
        saved_filename = f"{file_id}{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, saved_filename)
        
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        with open(file_path, 'wb') as f:
            for chunk in temp_chunks:
                f.write(chunk)
        
        logger.info(f"Saved uploaded file: {file_path} ({file_size} bytes)")
        
        # Get processing service
        processing_service = get_processing_service(request)
        
        # Start workers if not already started
        if not processing_service._workers_started:
            await processing_service.start_workers()
        
        # Create processing job
        job_id = await processing_service.create_job(
            filename=audio_file.filename,
            file_path=file_path
        )
        
        job = processing_service.get_job_status(job_id)
        
        return TranscriptionJobResponse(
            job_id=job.job_id,
            status=job.status,
            filename=job.filename,
            created_at=job.created_at,
            updated_at=job.updated_at,
            message=job.message,
            progress=job.progress
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload_and_transcribe: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/status/{job_id}", response_model=TranscriptionJobStatus)
async def get_job_status(job_id: str, request: Request):
    """
    Get the status of a transcription job
    
    Args:
        job_id: The unique job identifier
        
    Returns:
        Current job status and progress
    """
    try:
        processing_service = get_processing_service(request)
        job = processing_service.get_job_status(job_id)
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        # Build response
        response = TranscriptionJobStatus(
            job_id=job.job_id,
            status=job.status,
            progress=job.progress,
            message=job.message
        )
        
        # Add result URLs if completed
        if job.status == ProcessingStatus.COMPLETED and job.result:
            base_url = f"/api/v1/download/{job_id}"
            response.result_url = f"{base_url}/pdf"
            response.midi_url = f"{base_url}/midi"
            response.drum_audio_url = f"{base_url}/audio"
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/download/{job_id}/pdf")
async def download_pdf(job_id: str, request: Request):
    """
    Download the generated PDF sheet music
    
    Args:
        job_id: The unique job identifier
        
    Returns:
        PDF file
    """
    try:
        processing_service = get_processing_service(request)
        job = processing_service.get_job_status(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status != ProcessingStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Job not completed. Current status: {job.status}"
            )
        
        if not job.result or not os.path.exists(job.result.pdf_path):
            raise HTTPException(status_code=404, detail="PDF file not found")
        
        return FileResponse(
            job.result.pdf_path,
            media_type="application/pdf",
            filename=f"drum_sheet_{job_id}.pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{job_id}/midi")
async def download_midi(job_id: str, request: Request):
    """
    Download the generated MIDI file
    
    Args:
        job_id: The unique job identifier
        
    Returns:
        MIDI file
    """
    try:
        processing_service = get_processing_service(request)
        job = processing_service.get_job_status(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status != ProcessingStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Job not completed. Current status: {job.status}"
            )
        
        if not job.result or not os.path.exists(job.result.midi_path):
            raise HTTPException(status_code=404, detail="MIDI file not found")
        
        return FileResponse(
            job.result.midi_path,
            media_type="audio/midi",
            filename=f"drums_{job_id}.mid"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading MIDI: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{job_id}/audio")
async def download_drum_audio(job_id: str, request: Request):
    """
    Download the separated drum audio
    
    Args:
        job_id: The unique job identifier
        
    Returns:
        WAV audio file
    """
    try:
        processing_service = get_processing_service(request)
        job = processing_service.get_job_status(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status != ProcessingStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Job not completed. Current status: {job.status}"
            )
        
        if not job.result or not os.path.exists(job.result.drum_audio_path):
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        return FileResponse(
            job.result.drum_audio_path,
            media_type="audio/wav",
            filename=f"drums_{job_id}.wav"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading audio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
