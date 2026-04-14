"""Application settings loaded from environment / .env file."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Security
    secret_key: str = "change-me-in-production"
    session_max_age: int = 60 * 60 * 8  # 8 hours

    # Database
    database_url: str = "sqlite:///./data/omniview.db"

    # Storage
    storage_path: Path = Path("./storage")

    @property
    def originals_path(self) -> Path:
        return self.storage_path / "originals"

    @property
    def working_path(self) -> Path:
        return self.storage_path / "working"

    @property
    def thumbnails_path(self) -> Path:
        return self.storage_path / "thumbnails"

    @property
    def clips_path(self) -> Path:
        return self.storage_path / "clips"

    @property
    def exports_path(self) -> Path:
        return self.storage_path / "exports"

    @property
    def quarantine_path(self) -> Path:
        return self.storage_path / "quarantine"

    # Logging
    log_level: str = "INFO"
    debug: bool = False

    # Motion detection defaults
    motion_min_area: int = 500          # σ2 — minimum contour area (pixels)
    motion_score_threshold: float = 25.0  # σ1 — minimum S_motion score
    motion_sample_every: int = 3        # process 1 of every N frames
    motion_gap_ms: int = 2000           # gap to close nearby events (ms)
    motion_min_duration_ms: int = 300   # discard events shorter than this

    # Thumbnail
    thumbnail_quality: int = 85  # WebP quality

    # Clip
    clip_pre_seconds: float = 3.0
    clip_post_seconds: float = 5.0
    clip_enabled: bool = True


settings = Settings()
