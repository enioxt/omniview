"""Unit tests for the auto-conversion layer."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestNeedsConversion:
    def test_dvr_extensions_need_conversion(self):
        from app.core.converter import needs_conversion
        for ext in (".264", ".h264", ".dav", ".dvr", ".m2ts", ".mts"):
            assert needs_conversion(Path(f"video{ext}")), ext

    def test_standard_extensions_no_conversion(self):
        from app.core.converter import needs_conversion
        for ext in (".mp4", ".avi", ".mov", ".mkv", ".webm"):
            assert not needs_conversion(Path(f"video{ext}")), ext

    def test_codec_hevc_needs_conversion(self):
        from app.core.converter import needs_conversion
        assert needs_conversion(Path("video.avi"), codec="hevc")

    def test_codec_h264_no_conversion(self):
        from app.core.converter import needs_conversion
        assert not needs_conversion(Path("video.avi"), codec="h264")


class TestEnsurePlayable:
    def test_no_conversion_needed_returns_source(self, tmp_path: Path):
        from app.core.converter import ensure_playable
        src = tmp_path / "clip.mp4"
        src.write_bytes(b"\x00" * 16)
        result = ensure_playable(src, tmp_path)
        assert result == src

    def test_ffmpeg_missing_returns_source_with_warning(self, tmp_path: Path):
        from app.core.converter import ensure_playable
        src = tmp_path / "clip.264"
        src.write_bytes(b"\x00" * 16)
        with patch("app.core.converter.shutil.which", return_value=None):
            result = ensure_playable(src, tmp_path)
        assert result == src

    def test_conversion_success(self, tmp_path: Path):
        from app.core.converter import ensure_playable
        src = tmp_path / "clip.dav"
        src.write_bytes(b"\x00" * 16)
        dest = tmp_path / "converted" / "clip.mp4"

        mock_result = MagicMock()
        mock_result.returncode = 0

        def _fake_run(cmd, **kwargs):
            # Simulate ffmpeg creating the output file
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"\x00" * 1024)
            return mock_result

        with patch("app.core.converter.shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("app.core.converter.subprocess.run", side_effect=_fake_run) as mock_run:
            result = ensure_playable(src, tmp_path)

        assert result == dest
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "-c:v" in cmd
        assert "libx264" in cmd

    def test_conversion_failure_raises_video_corrupt(self, tmp_path: Path):
        from app.core.converter import ensure_playable
        from app.core.errors import VideoCorrupt
        src = tmp_path / "bad.dav"
        src.write_bytes(b"\x00" * 16)

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "codec not supported"

        with patch("app.core.converter.shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("app.core.converter.subprocess.run", return_value=mock_result):
            try:
                ensure_playable(src, tmp_path)
                assert False, "should have raised"
            except VideoCorrupt as exc:
                assert "Conversion failed" in exc.message_en

    def test_cached_conversion_reuses_file(self, tmp_path: Path):
        """If converted file already exists, skip ffmpeg entirely."""
        from app.core.converter import ensure_playable
        src = tmp_path / "clip.h264"
        src.write_bytes(b"\x00" * 16)
        dest = tmp_path / "converted" / "clip.mp4"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"already_converted")

        with patch("app.core.converter.shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("app.core.converter.subprocess.run") as mock_run:
            result = ensure_playable(src, tmp_path)

        assert result == dest
        mock_run.assert_not_called()
