"""Geometry lock: OpenCV Canny edge extraction on the uploaded sketch.

The edge map is stored as evidence that generation stays locked to the input
sketch's geometry; it is also passed to the render provider alongside the
sketch with a fidelity-focused prompt.
"""

from pathlib import Path

import cv2


class GeometryError(Exception):
    """Raised when edge extraction fails. Message only — no stack detail."""


def extract_edges(src: Path, dst: Path) -> Path:
    """Extract Canny edges from src image and write PNG to dst.

    Output has identical width/height to the input.
    Raises GeometryError if the source cannot be read or the edge map
    cannot be written.
    """
    img = cv2.imread(str(src), cv2.IMREAD_COLOR)
    if img is None:
        raise GeometryError(f"Could not read image: {src.name}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 100, 200)

    if not cv2.imwrite(str(dst), edges):
        raise GeometryError(f"Could not write edge map: {dst.name}")

    return dst
