"""Fidelity scoring: does the render preserve the sketch's geometry?

Compares the Canny edge map of the generated render against the edge map
extracted from the input sketch at upload time.

The score is edge *recall*: what fraction of the sketch's structural edges
is still present in the render (within a small pixel tolerance). Recall —
not precision — because a photorealistic render legitimately contains many
extra edges (foliage, textures, shadows) that the clean sketch lacks.

Range: 0.0 (no structural edge survived) to 1.0 (all survived).
A sketch with no detectable edges trivially scores 1.0.

Initial calibration on real renders (tolerance 3px):
  faithful render (edge-conditioned pipeline): ~0.66
  drifted render (roof redesigned by the model): ~0.45
Suggested FIDELITY_MIN_SCORE starting point: 0.55 — tune from your own data.
"""

from pathlib import Path

import cv2
import numpy as np

_TOLERANCE_PX = 3
_CANNY_LOW = 100
_CANNY_HIGH = 200


class FidelityError(Exception):
    """Raised when the score cannot be computed. Message only."""


def _canny_edges(bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    return cv2.Canny(blurred, _CANNY_LOW, _CANNY_HIGH)


def fidelity_score(sketch_edge_path: Path, render_bytes: bytes) -> float:
    """Edge recall of the render against the sketch edge map, 0.0..1.0."""
    ref = cv2.imread(str(sketch_edge_path), cv2.IMREAD_GRAYSCALE)
    if ref is None:
        raise FidelityError(f"Could not read sketch edge map: {sketch_edge_path.name}")

    arr = np.frombuffer(render_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise FidelityError("Render is not a readable image.")

    height, width = ref.shape
    if (bgr.shape[1], bgr.shape[0]) != (width, height):
        bgr = cv2.resize(bgr, (width, height), interpolation=cv2.INTER_AREA)

    ref_bin = (ref > 0).astype(np.uint8)
    n_ref = int(ref_bin.sum())
    if n_ref == 0:
        return 1.0

    rend_bin = (_canny_edges(bgr) > 0).astype(np.uint8)
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * _TOLERANCE_PX + 1, 2 * _TOLERANCE_PX + 1)
    )
    rend_dilated = cv2.dilate(rend_bin, kernel)
    matched = int(((ref_bin > 0) & (rend_dilated > 0)).sum())
    return matched / n_ref
