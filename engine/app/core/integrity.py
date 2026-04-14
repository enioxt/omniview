"""SHA-256 integrity utilities.

Streams file in 1MB chunks to avoid loading large videos into RAM.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


_CHUNK = 1024 * 1024  # 1 MB


def sha256_file(path: Path) -> str:
    """Compute SHA-256 of a file, streaming in chunks."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def verify_file(path: Path, expected_hash: str) -> bool:
    """Return True if file SHA-256 matches expected_hash."""
    return sha256_file(path) == expected_hash.lower()
