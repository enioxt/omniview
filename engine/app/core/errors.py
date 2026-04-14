"""OmniView error taxonomy.

Every user-facing error has a stable code, an English message (for logs),
and a Portuguese message (for UI). The correlation_id links log → API response.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class OmniError(Exception):
    code: str
    message_en: str
    message_pt: str
    status_code: int = 400
    correlation_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message_pt,
            "message_en": self.message_en,
            "correlation_id": self.correlation_id,
        }


# ── Ingest (001–099) ───────────────────────────────────────────────────────────

class IngestValidationError(OmniError):
    def __init__(self, detail: str = "", **kwargs: object) -> None:
        super().__init__(
            code="OMNI-001",
            message_en=f"Ingest validation failed: {detail}",
            message_pt=f"Falha na validação do arquivo: {detail}",
            status_code=422,
            **kwargs,  # type: ignore[arg-type]
        )


class IntegrityCheckFailed(OmniError):
    def __init__(self, expected: str = "", actual: str = "", **kwargs: object) -> None:
        super().__init__(
            code="OMNI-002",
            message_en=f"Integrity check failed — expected {expected}, got {actual}",
            message_pt="Falha na verificação de integridade do arquivo",
            status_code=409,
            **kwargs,  # type: ignore[arg-type]
        )


class VideoCorrupt(OmniError):
    def __init__(self, detail: str = "", **kwargs: object) -> None:
        super().__init__(
            code="OMNI-003",
            message_en=f"Video file is corrupt or unreadable: {detail}",
            message_pt=f"Arquivo de vídeo corrompido ou ilegível: {detail}",
            status_code=422,
            **kwargs,  # type: ignore[arg-type]
        )


class InsufficientStorage(OmniError):
    def __init__(self, required_mb: int = 0, **kwargs: object) -> None:
        super().__init__(
            code="OMNI-004",
            message_en=f"Insufficient storage — need at least {required_mb} MB",
            message_pt=f"Espaço insuficiente em disco — necessário: {required_mb} MB",
            status_code=507,
            **kwargs,  # type: ignore[arg-type]
        )


# ── Motion / processing (100–199) ─────────────────────────────────────────────

class MotionPipelineError(OmniError):
    def __init__(self, detail: str = "", **kwargs: object) -> None:
        super().__init__(
            code="OMNI-100",
            message_en=f"Motion pipeline error: {detail}",
            message_pt=f"Erro no pipeline de detecção de movimento: {detail}",
            status_code=500,
            **kwargs,  # type: ignore[arg-type]
        )


# ── Detector (200–299) ────────────────────────────────────────────────────────

class DetectorUnavailable(OmniError):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(
            code="OMNI-200",
            message_en="Object detector is unavailable or not installed",
            message_pt="Detector de objetos indisponível ou não instalado",
            status_code=503,
            **kwargs,  # type: ignore[arg-type]
        )


# ── Export (300–399) ──────────────────────────────────────────────────────────

class ExportSignatureFailed(OmniError):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(
            code="OMNI-300",
            message_en="Failed to sign export package",
            message_pt="Falha ao assinar pacote de exportação",
            status_code=500,
            **kwargs,  # type: ignore[arg-type]
        )


# ── Auth (400–499) ────────────────────────────────────────────────────────────

class AuthFailed(OmniError):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(
            code="OMNI-400",
            message_en="Authentication failed",
            message_pt="Autenticação falhou",
            status_code=401,
            **kwargs,  # type: ignore[arg-type]
        )


class PermissionDenied(OmniError):
    def __init__(self, action: str = "", **kwargs: object) -> None:
        super().__init__(
            code="OMNI-401",
            message_en=f"Permission denied: {action}",
            message_pt=f"Permissão negada: {action}",
            status_code=403,
            **kwargs,  # type: ignore[arg-type]
        )


# ── Quarantine (500–599) ──────────────────────────────────────────────────────

class QuarantineHeld(OmniError):
    def __init__(self, video_id: str = "", **kwargs: object) -> None:
        super().__init__(
            code="OMNI-500",
            message_en=f"Video {video_id} is held in quarantine pending validation",
            message_pt=f"Vídeo {video_id} em quarentena aguardando validação",
            status_code=202,
            **kwargs,  # type: ignore[arg-type]
        )
