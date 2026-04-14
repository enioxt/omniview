"""Unit tests for SHA-256 integrity utilities."""
from pathlib import Path

import pytest

from app.core.integrity import sha256_file, verify_file


def test_sha256_file_deterministic(tmp_path: Path) -> None:
    f = tmp_path / "test.bin"
    f.write_bytes(b"hello omniview")
    h1 = sha256_file(f)
    h2 = sha256_file(f)
    assert h1 == h2
    assert len(h1) == 64  # hex SHA-256


def test_sha256_file_different_content(tmp_path: Path) -> None:
    f1 = tmp_path / "a.bin"
    f2 = tmp_path / "b.bin"
    f1.write_bytes(b"content-a")
    f2.write_bytes(b"content-b")
    assert sha256_file(f1) != sha256_file(f2)


def test_verify_file_correct(tmp_path: Path) -> None:
    f = tmp_path / "data.bin"
    f.write_bytes(b"verify-me")
    h = sha256_file(f)
    assert verify_file(f, h) is True


def test_verify_file_wrong_hash(tmp_path: Path) -> None:
    f = tmp_path / "data.bin"
    f.write_bytes(b"verify-me")
    assert verify_file(f, "deadbeef" * 8) is False


def test_sha256_large_file(tmp_path: Path) -> None:
    """Ensure streaming works for files larger than chunk size."""
    f = tmp_path / "large.bin"
    f.write_bytes(b"x" * (2 * 1024 * 1024 + 1))  # 2MB + 1 byte
    h = sha256_file(f)
    assert len(h) == 64
