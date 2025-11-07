"""
Processing service - Orchestrates the complete transcription pipeline
"""
import os
import uuid
import time
import logging
import asyncio
from typing import Dict, Optional
from datetime import datetime

from app.models.schemas import ProcessingStatus, TranscriptionResult
from app.services.model_manager import ModelManager
from app.services.job_storage import JobStorage
from app.core.config import settings

logger = logging.getLogger(__name__)


class ProcessingJob:
    """Represents a single processing job"""
    
    def __init__(self, job_id: str, filename: str, file_path: str):
        self.job_id = job_id
        self.filename = filename
        self.file_path = file_path
        self.status = ProcessingStatus.PENDING
        self.progress = 0
        self.message = "Job created"
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.result: Optional[TranscriptionResult] = None
        self.error: Optional[str] = None
    
    def to_dict(self):
        """Convert job to dictionary for storage"""
        return {
            'job_id': self.job_id,
            'filename': self.filename,
            'file_path': self.file_path,
            'status': self.status.value if hasattr(self.status, 'value') else str(self.status),
            'progress': self.progress,
            'message': self.message,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else str(self.updated_at),
            'result': self.result.dict() if self.result else None,
            'error': self.error
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create job from dictionary"""
        job = cls(
            job_id=data['job_id'],
            filename=data['filename'],
            file_path=data['file_path']
        )
        job.status = ProcessingStatus(data['status']) if isinstance(data['status'], str) else data['status']
        job.progress = data['progress']
        job.message = data['message']
        job.created_at = datetime.fromisoformat(data['created_at']) if isinstance(data['created_at'], str) else data['created_at']
        job.updated_at = datetime.fromisoformat(data['updated_at']) if isinstance(data['updated_at'], str) else data['updated_at']
        job.error = data.get('error')
        if data.get('result'):
            job.result = TranscriptionResult(**data['result'])
        return job


class ProcessingService:
    """Service for managing transcription processing jobs"""
    
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.jobs: Dict[str, ProcessingJob] = {}  # In-memory cache
        self.job_storage = JobStorage(
            use_cloud_storage=settings.USE_CLOUD_STORAGE,
            bucket_name=settings.GCS_BUCKET_NAME,
            storage_dir=settings.JOB_STORAGE_DIR
        )
        self.processing_queue: asyncio.Queue = asyncio.Queue(
            maxsize=settings.MAX_CONCURRENT_JOBS
        )
        self._workers_started = False
        logger.info("ProcessingService initialized with persistent storage")
    
    async def start_workers(self):
        """Start background workers for processing jobs"""
        if not self._workers_started:
            self._workers_started = True
            # Start worker tasks
            for i in range(settings.MAX_CONCURRENT_JOBS):
                asyncio.create_task(self._worker(i))
            logger.info(f"Started {settings.MAX_CONCURRENT_JOBS} processing workers")
    
    async def _worker(self, worker_id: int):
        """Background worker for processing jobs"""
        logger.info(f"Worker {worker_id} started")
        
        while True:
            try:
                # Get job from queue
                job_id = await self.processing_queue.get()
                
                if job_id not in self.jobs:
                    logger.warning(f"Job {job_id} not found in jobs dict")
                    continue
                
                job = self.jobs[job_id]
                
                logger.info(f"Worker {worker_id} processing job {job_id}")
                
                # Process the job
                await self._process_job(job)
                
                # Mark task as done
                self.processing_queue.task_done()
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {str(e)}")
                await asyncio.sleep(1)
    
    async def create_job(self, filename: str, file_path: str) -> str:
        """
        Create a new processing job
        
        Args:
            filename: Original filename
            file_path: Path to uploaded file
            
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        
        job = ProcessingJob(
            job_id=job_id,
            filename=filename,
            file_path=file_path
        )
        
        # Save to both memory and persistent storage
        self.jobs[job_id] = job
        self.job_storage.save_job(job_id, job.to_dict())
        
        # Add to processing queue
        await self.processing_queue.put(job_id)
        
        logger.info(f"Created job {job_id} for file {filename}")
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[ProcessingJob]:
        """Get job status - checks memory cache first, then persistent storage"""
        # Check memory cache first
        if job_id in self.jobs:
            return self.jobs[job_id]
        
        # Try loading from persistent storage
        job_data = self.job_storage.load_job(job_id)
        if job_data:
            job = ProcessingJob.from_dict(job_data)
            # Cache it in memory
            self.jobs[job_id] = job
            return job
        
        return None
    
    def _save_job_state(self, job: ProcessingJob):
        """Save job state to persistent storage"""
        job.updated_at = datetime.now()
        self.job_storage.save_job(job.job_id, job.to_dict())
    
    async def _process_job(self, job: ProcessingJob):
        """
        Process a transcription job through the complete pipeline
        
        Args:
            job: ProcessingJob instance
        """
        start_time = time.time()
        
        try:
            # Check if models are ready
            if not self.model_manager.is_ready():
                raise RuntimeError("Models not initialized")
            
            # Create job output directory
            job_output_dir = os.path.join(settings.OUTPUT_DIR, job.job_id)
            os.makedirs(job_output_dir, exist_ok=True)
            
            # Step 1: Separate drum track
            job.status = ProcessingStatus.SEPARATING
            job.progress = 10
            job.message = "Separating drum track from audio..."
            job.updated_at = datetime.now()
            self._save_job_state(job)  # Save state
            logger.info(f"Job {job.job_id}: Starting drum separation")
            
            drum_audio_path = await self.model_manager.demucs_service.separate_drums(
                input_audio_path=job.file_path,
                output_dir=job_output_dir
            )
            
            job.progress = 40
            job.message = "Drum track separated successfully"
            job.updated_at = datetime.now()
            self._save_job_state(job)  # Save state
            logger.info(f"Job {job.job_id}: Drum separation complete")
            
            # Step 2: Transcribe drums to MIDI
            job.status = ProcessingStatus.TRANSCRIBING
            job.progress = 50
            job.message = "Transcribing drum notation..."
            job.updated_at = datetime.now()
            self._save_job_state(job)  # Save state
            logger.info(f"Job {job.job_id}: Starting drum transcription")
            
            midi_path = await self.model_manager.omnizart_service.transcribe_drums(
                drum_audio_path=drum_audio_path,
                output_dir=job_output_dir
            )
            
            job.progress = 70
            job.message = "Drum transcription complete"
            job.updated_at = datetime.now()
            self._save_job_state(job)  # Save state
            logger.info(f"Job {job.job_id}: Drum transcription complete")
            
            # Step 3: Generate MusicXML notation
            job.status = ProcessingStatus.GENERATING_SHEET
            job.progress = 80
            job.message = "Generating MusicXML notation..."
            job.updated_at = datetime.now()
            self._save_job_state(job)  # Save state
            logger.info(f"Job {job.job_id}: Starting MusicXML generation")
            
            musicxml_path = await self.model_manager.sheet_music_service.midi_to_musicxml(
                midi_path=midi_path,
                output_dir=job_output_dir,
                filename="drum_sheet"
            )
            
            job.progress = 95
            job.message = "MusicXML notation generated"
            job.updated_at = datetime.now()
            self._save_job_state(job)  # Save state
            logger.info(f"Job {job.job_id}: MusicXML generation complete")
            
            # Complete
            processing_time = time.time() - start_time
            
            job.status = ProcessingStatus.COMPLETED
            job.progress = 100
            job.message = f"Processing completed in {processing_time:.2f}s"
            job.updated_at = datetime.now()
            
            job.result = TranscriptionResult(
                job_id=job.job_id,
                musicxml_path=musicxml_path,
                midi_path=midi_path,
                drum_audio_path=drum_audio_path,
                processing_time=processing_time
            )
            
            self._save_job_state(job)  # Save final state
            
            logger.info(
                f"Job {job.job_id} completed successfully in {processing_time:.2f}s"
            )
            
            # Cleanup original file if configured
            if settings.CLEANUP_AFTER_PROCESSING:
                try:
                    if os.path.exists(job.file_path):
                        os.remove(job.file_path)
                        logger.info(f"Cleaned up uploaded file: {job.file_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup uploaded file: {str(e)}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Job {job.job_id} failed: {error_msg}")
            
            job.status = ProcessingStatus.FAILED
            job.message = f"Processing failed: {error_msg}"
            job.error = error_msg
            job.updated_at = datetime.now()
            self._save_job_state(job)  # Save error state
            
            # Cleanup on failure
            try:
                if os.path.exists(job.file_path):
                    os.remove(job.file_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup on error: {str(cleanup_error)}")
