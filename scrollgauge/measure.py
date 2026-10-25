"""Find how far content scrolled between two screenshots."""

from dataclasses import dataclass

import numpy as np

# A row/column counts as "changed" when more than this fraction of its pixels
# differ. Keeps small updates (panel clock, blinking cursor) from widening the box.
CHANGED_FRACTION = 0.05
PIXEL_THRESHOLD = 8.0


@dataclass(frozen=True)
class Shift:
    dy: float  # positive: content moved up (view scrolled down)
    dx: float
    confidence: float  # phase-correlation peak height, 0..1


def to_gray(img: np.ndarray) -> np.ndarray:
    img = np.asarray(img)
    if img.ndim == 3:
        img = img[..., :3] @ np.array([0.299, 0.587, 0.114])
    return img.astype(np.float64)


def changed_region(a: np.ndarray, b: np.ndarray, pad: int = 4) -> tuple[slice, slice] | None:
    """Bounding box of the area that differs between two gray frames."""
    diff = np.abs(a - b) > PIXEL_THRESHOLD
    rows = np.flatnonzero(diff.mean(axis=1) > CHANGED_FRACTION)
    cols = np.flatnonzero(diff.mean(axis=0) > CHANGED_FRACTION)
    if rows.size == 0 or cols.size == 0:
        return None
    h, w = a.shape
    return (
        slice(max(rows[0] - pad, 0), min(rows[-1] + pad + 1, h)),
        slice(max(cols[0] - pad, 0), min(cols[-1] + pad + 1, w)),
    )


def _subpixel(r: np.ndarray, i: int) -> float:
    """Parabolic fit around index i of a circular 1-D array."""
    n = r.size
    left, mid, right = r[(i - 1) % n], r[i], r[(i + 1) % n]
    denom = left - 2 * mid + right
    return 0.0 if denom == 0 else 0.5 * (left - right) / denom


def phase_correlate(a: np.ndarray, b: np.ndarray) -> Shift:
    """Translation that maps frame a onto frame b."""
    h, w = a.shape
    window = np.outer(np.hanning(h), np.hanning(w))
    fa = np.fft.fft2((a - a.mean()) * window)
    fb = np.fft.fft2((b - b.mean()) * window)
    cross = fa * np.conj(fb)
    cross /= np.maximum(np.abs(cross), 1e-12)
    r = np.fft.ifft2(cross).real

    py, px = np.unravel_index(np.argmax(r), r.shape)
    peak = float(r[py, px])
    fy = py + _subpixel(r[:, px], py)
    fx = px + _subpixel(r[py, :], px)
    # Indices past the midpoint wrap around to negative shifts.
    if fy > h / 2:
        fy -= h
    if fx > w / 2:
        fx -= w
    return Shift(dy=float(fy), dx=float(fx), confidence=peak)


def vertical_shift(before: np.ndarray, after: np.ndarray) -> Shift | None:
    """Measure the scroll between two screenshots, or None if nothing moved."""
    a, b = to_gray(before), to_gray(after)
    if a.shape != b.shape:
        raise ValueError(f"frame sizes differ: {a.shape} vs {b.shape}")
    region = changed_region(a, b)
    if region is None:
        return None
    a, b = a[region], b[region]
    if min(a.shape) < 32:
        return None
    return phase_correlate(a, b)
