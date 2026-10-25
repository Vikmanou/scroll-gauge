from dataclasses import dataclass

import numpy as np

PIXEL_DIFF_THRESHOLD = 8.0
MIN_CHANGED_FRACTION = 0.05


@dataclass(frozen=True)
class Shift:
    """dy > 0 means the content moved up, i.e. the view scrolled down."""

    dy: float
    dx: float
    confidence: float


def to_gray(img: np.ndarray) -> np.ndarray:
    img = np.asarray(img)
    if img.ndim == 3:
        img = img[..., :3] @ np.array([0.299, 0.587, 0.114])
    return img.astype(np.float64)


def changed_region(a: np.ndarray, b: np.ndarray, pad: int = 4) -> tuple[slice, slice] | None:
    changed = np.abs(a - b) > PIXEL_DIFF_THRESHOLD
    rows = np.flatnonzero(changed.mean(axis=1) > MIN_CHANGED_FRACTION)
    cols = np.flatnonzero(changed.mean(axis=0) > MIN_CHANGED_FRACTION)
    if rows.size == 0 or cols.size == 0:
        return None
    h, w = a.shape
    return (
        slice(max(rows[0] - pad, 0), min(rows[-1] + pad + 1, h)),
        slice(max(cols[0] - pad, 0), min(cols[-1] + pad + 1, w)),
    )


def _parabolic_offset(r: np.ndarray, i: int) -> float:
    n = r.size
    left, mid, right = r[(i - 1) % n], r[i], r[(i + 1) % n]
    denom = left - 2 * mid + right
    return 0.0 if denom == 0 else 0.5 * (left - right) / denom


def _signed(index: float, size: int) -> float:
    return index - size if index > size / 2 else index


def phase_correlate(a: np.ndarray, b: np.ndarray) -> Shift:
    h, w = a.shape
    window = np.outer(np.hanning(h), np.hanning(w))
    fa = np.fft.fft2((a - a.mean()) * window)
    fb = np.fft.fft2((b - b.mean()) * window)
    cross = fa * np.conj(fb)
    cross /= np.maximum(np.abs(cross), 1e-12)
    r = np.fft.ifft2(cross).real

    py, px = np.unravel_index(np.argmax(r), r.shape)
    dy = _signed(py + _parabolic_offset(r[:, px], py), h)
    dx = _signed(px + _parabolic_offset(r[py, :], px), w)
    return Shift(dy=float(dy), dx=float(dx), confidence=float(r[py, px]))


def vertical_shift(before: np.ndarray, after: np.ndarray) -> Shift | None:
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
