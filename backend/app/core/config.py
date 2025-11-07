"""
Application configuration settings
"""
import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # Server settings
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="ALLOWED_ORIGINS"
    )
    
    # Directory settings
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    UPLOAD_DIR: str = Field(default="./uploads", env="UPLOAD_DIR")
    TEMP_DIR: str = Field(default="./temp", env="TEMP_DIR")
    OUTPUT_DIR: str = Field(default="./outputs", env="OUTPUT_DIR")
    MODELS_DIR: str = Field(default="./models", env="MODELS_DIR")
    
    # File settings
    MAX_UPLOAD_SIZE: int = Field(default=100 * 1024 * 1024, env="MAX_UPLOAD_SIZE")  # 100MB
    ALLOWED_AUDIO_FORMATS: List[str] = Field(
        default=["audio/mpeg", "audio/wav", "audio/mp3", "audio/x-wav"],
        env="ALLOWED_AUDIO_FORMATS"
    )
    
    # Processing settings
    CLEANUP_AFTER_PROCESSING: bool = Field(default=True, env="CLEANUP_AFTER_PROCESSING")
    FILE_RETENTION_HOURS: int = Field(default=24, env="FILE_RETENTION_HOURS")
    MAX_CONCURRENT_JOBS: int = Field(default=3, env="MAX_CONCURRENT_JOBS")
    
    # Job storage settings
    USE_CLOUD_STORAGE: bool = Field(default=False, env="USE_CLOUD_STORAGE")
    GCS_BUCKET_NAME: str = Field(default="", env="GCS_BUCKET_NAME")
    JOB_STORAGE_DIR: str = Field(default="./jobs", env="JOB_STORAGE_DIR")
    
    # Demucs settings
    DEMUCS_MODEL: str = Field(default="htdemucs", env="DEMUCS_MODEL")
    DEMUCS_DEVICE: str = Field(default="cuda", env="DEMUCS_DEVICE")  # cuda or cpu
    DEMUCS_SHIFTS: int = Field(default=1, env="DEMUCS_SHIFTS")
    DEMUCS_OVERLAP: float = Field(default=0.25, env="DEMUCS_OVERLAP")
    
    # Omnizart settings
    OMNIZART_DEVICE: str = Field(default="cuda", env="OMNIZART_DEVICE")
    OMNIZART_MODEL_PATH: str = Field(default="", env="OMNIZART_MODEL_PATH")
    OMNIZART_CHECKPOINT_BUCKET: str = Field(default="groovesheet-omnizart-checkpoints", env="OMNIZART_CHECKPOINT_BUCKET")
    
    # Sheet music settings
    SHEET_MUSIC_FORMAT: str = Field(default="pdf", env="SHEET_MUSIC_FORMAT")
    SHEET_MUSIC_DPI: int = Field(default=300, env="SHEET_MUSIC_DPI")
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field(default="./logs/drumscore.log", env="LOG_FILE")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()
