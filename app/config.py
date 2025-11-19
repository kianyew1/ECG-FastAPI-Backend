"""
Configuration management for ECG Processing Service.
Uses pydantic-settings for environment variable validation.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Configuration
    app_name: str = "ECG Processing Service"
    app_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # CORS Configuration - includes Railway wildcard for production
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "https://*.up.railway.app",
    ]
    
    @property
    def port(self) -> int:
        """Get port from PORT env variable (Railway) or api_port."""
        import os
        return int(os.environ.get("PORT", self.api_port))
    
    # File Processing
    max_upload_size_mb: int = 50
    temp_dir: str = "/tmp/ecg_uploads"
    
    # ECG Processing
    default_sampling_rate: int = 500
    default_channels: List[str] = ["CH2", "CH3", "CH4"]
    max_duration_seconds: int = 300  # 5 minutes max
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
