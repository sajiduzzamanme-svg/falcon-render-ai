"""Fidelity scorer unit tests (no network)."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.fidelity import FidelityError, fidelity_score


def _png_of(rect: tuple[int, int, int, int] | None, size: int = 200) -> bytes:
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    if rect is not None:
        x, y, w, h = rect
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 0), thickness=3)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return bytes(buf)


def _edge_file(png_bytes: bytes, tmp_path: Path) -> Path:
    img = cv2.imdecode(np.frombuffer(png_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 100, 200)
    path = tmp_path / "edge.png"
    cv2.imwrite(str(path), edges)
    return path


def test_identical_structure_scores_one(tmp_path: Path) -> None:
    png = _png_of((40, 40, 120, 120))
    edge = _edge_file(png, tmp_path)
    assert fidelity_score(edge, png) == pytest.approx(1.0)


def test_blank_render_scores_zero(tmp_path: Path) -> None:
    png = _png_of((40, 40, 120, 120))
    edge = _edge_file(png, tmp_path)
    assert fidelity_score(edge, _png_of(None)) == pytest.approx(0.0)


def test_shifted_structure_scores_between(tmp_path: Path) -> None:
    png = _png_of((40, 40, 120, 120))
    edge = _edge_file(png, tmp_path)
    shifted = _png_of((60, 60, 120, 120))
    score = fidelity_score(edge, shifted)
    assert 0.0 < score < 1.0


def test_different_size_render_is_resized(tmp_path: Path) -> None:
    png = _png_of((40, 40, 120, 120))
    edge = _edge_file(png, tmp_path)
    big = cv2.imdecode(np.frombuffer(png, dtype=np.uint8), cv2.IMREAD_COLOR)
    big = cv2.resize(big, (400, 400), interpolation=cv2.INTER_NEAREST)
    ok, buf = cv2.imencode(".png", big)
    assert ok
    assert fidelity_score(edge, bytes(buf)) == pytest.approx(1.0)


def test_unreadable_render_raises(tmp_path: Path) -> None:
    png = _png_of((40, 40, 120, 120))
    edge = _edge_file(png, tmp_path)
    with pytest.raises(FidelityError):
        fidelity_score(edge, b"not-an-image")


def test_edgeless_sketch_scores_one(tmp_path: Path) -> None:
    blank = _png_of(None)
    edge = _edge_file(blank, tmp_path)
    assert fidelity_score(edge, _png_of((10, 10, 50, 50))) == pytest.approx(1.0)
