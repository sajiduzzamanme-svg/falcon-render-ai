"""Tests for the OpenCV geometry lock (edge extraction)."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.geometry import GeometryError, extract_edges


def _synthetic_sketch(path: Path, width: int = 400, height: int = 300) -> None:
    """White canvas with black rectangles — a stand-in architectural sketch."""
    canvas = np.full((height, width, 3), 255, dtype=np.uint8)
    # Building outline.
    cv2.rectangle(canvas, (40, 60), (360, 260), (0, 0, 0), 3)
    # Window/door openings.
    cv2.rectangle(canvas, (80, 100), (160, 180), (0, 0, 0), -1)
    cv2.rectangle(canvas, (200, 100), (280, 180), (0, 0, 0), -1)
    cv2.rectangle(canvas, (310, 150), (345, 260), (0, 0, 0), -1)
    assert cv2.imwrite(str(path), canvas)


def test_extract_edges_preserves_dimensions(tmp_path: Path) -> None:
    src = tmp_path / "sketch.png"
    dst = tmp_path / "edge.png"
    _synthetic_sketch(src)

    extract_edges(src, dst)

    assert dst.exists(), "edge.png must be written"
    assert dst.stat().st_size > 0, "edge.png must be non-empty"

    src_img = cv2.imread(str(src))
    edge_img = cv2.imread(str(dst), cv2.IMREAD_GRAYSCALE)
    assert src_img is not None and edge_img is not None
    # Edge map must have identical width/height to the input.
    assert (edge_img.shape[1], edge_img.shape[0]) == (
        src_img.shape[1],
        src_img.shape[0],
    )
    # A sketch with geometry must produce edge pixels.
    assert int(np.count_nonzero(edge_img)) > 0


def test_extract_edges_unreadable_source(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.png"
    with pytest.raises(GeometryError):
        extract_edges(missing, tmp_path / "edge.png")

    not_an_image = tmp_path / "junk.png"
    not_an_image.write_bytes(b"this is not image data")
    with pytest.raises(GeometryError):
        extract_edges(not_an_image, tmp_path / "edge2.png")
