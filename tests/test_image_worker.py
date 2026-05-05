"""Tests for image_worker pre-processing logic."""

import os
import tempfile

import pytest
from PIL import Image

from app.workers.image_worker import _cap_image_size, _OCR_MAX_SIDE


def _make_image(path: str, width: int, height: int) -> None:
    img = Image.new("RGB", (width, height), color="white")
    img.save(path)


class TestCapImageSize:
    def test_small_image_unchanged(self, tmp_path):
        """Image smaller than the limit is not modified."""
        p = str(tmp_path / "small.png")
        _make_image(p, 100, 200)
        mtime_before = os.path.getmtime(p)
        _cap_image_size(p)
        with Image.open(p) as img:
            assert img.size == (100, 200)

    def test_tall_image_scaled_down(self, tmp_path):
        """A tall image (long side > limit) is resized proportionally."""
        p = str(tmp_path / "tall.png")
        _make_image(p, 921, 5571)
        _cap_image_size(p)
        with Image.open(p) as img:
            w, h = img.size
            assert max(w, h) <= _OCR_MAX_SIDE
            assert abs(w / h - 921 / 5571) < 0.01

    def test_wide_image_scaled_down(self, tmp_path):
        """A wide image (long side > limit) is resized proportionally."""
        p = str(tmp_path / "wide.png")
        _make_image(p, 6000, 800)
        _cap_image_size(p)
        with Image.open(p) as img:
            w, h = img.size
            assert max(w, h) <= _OCR_MAX_SIDE
            assert abs(w / h - 6000 / 800) < 0.02

    def test_exact_limit_unchanged(self, tmp_path):
        """Image whose long side equals the limit is not resized."""
        p = str(tmp_path / "exact.png")
        _make_image(p, _OCR_MAX_SIDE, 100)
        _cap_image_size(p)
        with Image.open(p) as img:
            assert img.size == (_OCR_MAX_SIDE, 100)

    def test_overridable_via_env(self, tmp_path, monkeypatch):
        """OCR_MAX_SIDE env var controls the cap at import time; default is 3500."""
        assert _OCR_MAX_SIDE == 3500
