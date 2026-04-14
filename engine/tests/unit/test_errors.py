"""Unit tests for error taxonomy."""
from app.core.errors import (
    AuthFailed,
    IngestValidationError,
    IntegrityCheckFailed,
    OmniError,
    PermissionDenied,
    VideoCorrupt,
)


def test_error_codes() -> None:
    assert IngestValidationError().code == "OMNI-001"
    assert IntegrityCheckFailed().code == "OMNI-002"
    assert VideoCorrupt().code == "OMNI-003"
    assert AuthFailed().code == "OMNI-400"
    assert PermissionDenied().code == "OMNI-401"


def test_to_dict_has_required_keys() -> None:
    err = IngestValidationError(detail="test")
    d = err.to_dict()
    assert "code" in d
    assert "message" in d
    assert "correlation_id" in d


def test_error_is_exception() -> None:
    err = VideoCorrupt(detail="corrupt")
    assert isinstance(err, Exception)
    assert isinstance(err, OmniError)


def test_status_codes() -> None:
    assert AuthFailed().status_code == 401
    assert PermissionDenied().status_code == 403
    assert IngestValidationError().status_code == 422
