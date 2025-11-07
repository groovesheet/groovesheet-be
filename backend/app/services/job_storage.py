"""
Job storage service - Handles persistent storage of job data
Supports both local file storage and Google Cloud Storage
"""
import json
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class JobStorage:
    """
    Simple job storage that works both locally and on Cloud Run
    - Local: Uses JSON files in a directory
    - Cloud: Uses Google Cloud Storage
    """
    
    def __init__(self, use_cloud_storage: bool = False, bucket_name: str = "", storage_dir: str = "./jobs"):
        self.use_cloud_storage = use_cloud_storage
        self.bucket_name = bucket_name
        self.storage_dir = storage_dir
        self.gcs_client = None
        self.bucket = None
        
        if use_cloud_storage:
            try:
                from google.cloud import storage
                self.gcs_client = storage.Client()
                self.bucket = self.gcs_client.bucket(bucket_name)
                logger.info(f"Using Google Cloud Storage bucket: {bucket_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize GCS, falling back to local storage: {e}")
                self.use_cloud_storage = False
        
        if not self.use_cloud_storage:
            # Use local file storage
            os.makedirs(storage_dir, exist_ok=True)
            logger.info(f"Using local file storage: {storage_dir}")
    
    def _get_job_key(self, job_id: str) -> str:
        """Get the storage key/path for a job"""
        return f"jobs/{job_id}.json"
    
    def _get_local_path(self, job_id: str) -> str:
        """Get local file path for a job"""
        return os.path.join(self.storage_dir, f"{job_id}.json")
    
    def save_job(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """
        Save job data to storage
        
        Args:
            job_id: Unique job identifier
            job_data: Job data dictionary (must be JSON serializable)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add timestamp
            job_data['updated_at'] = datetime.now().isoformat()
            
            # Convert to JSON
            json_data = json.dumps(job_data, default=str)
            
            if self.use_cloud_storage and self.bucket:
                # Save to GCS
                blob = self.bucket.blob(self._get_job_key(job_id))
                blob.upload_from_string(json_data, content_type='application/json')
                logger.debug(f"Saved job {job_id} to GCS")
            else:
                # Save to local file
                file_path = self._get_local_path(job_id)
                with open(file_path, 'w') as f:
                    f.write(json_data)
                logger.debug(f"Saved job {job_id} to local storage")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save job {job_id}: {e}")
            return False
    
    def load_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Load job data from storage
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            Job data dictionary if found, None otherwise
        """
        try:
            if self.use_cloud_storage and self.bucket:
                # Load from GCS
                blob = self.bucket.blob(self._get_job_key(job_id))
                if blob.exists():
                    json_data = blob.download_as_text()
                    return json.loads(json_data)
                else:
                    logger.debug(f"Job {job_id} not found in GCS")
                    return None
            else:
                # Load from local file
                file_path = self._get_local_path(job_id)
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        return json.load(f)
                else:
                    logger.debug(f"Job {job_id} not found in local storage")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to load job {job_id}: {e}")
            return None
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete job data from storage
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.use_cloud_storage and self.bucket:
                # Delete from GCS
                blob = self.bucket.blob(self._get_job_key(job_id))
                if blob.exists():
                    blob.delete()
                    logger.debug(f"Deleted job {job_id} from GCS")
            else:
                # Delete from local file
                file_path = self._get_local_path(job_id)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Deleted job {job_id} from local storage")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {e}")
            return False
    
    def job_exists(self, job_id: str) -> bool:
        """
        Check if a job exists in storage
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            True if job exists, False otherwise
        """
        try:
            if self.use_cloud_storage and self.bucket:
                blob = self.bucket.blob(self._get_job_key(job_id))
                return blob.exists()
            else:
                file_path = self._get_local_path(job_id)
                return os.path.exists(file_path)
        except Exception as e:
            logger.error(f"Failed to check if job {job_id} exists: {e}")
            return False
