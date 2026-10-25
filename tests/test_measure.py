import numpy as np
import pytest

from scrollgauge.measure import changed_region, phase_correlate, to_gray, vertical_shift

rng = np.random.default_rng(0)
UP = 4  # texture is built at 4x and averaged down, so shifts of 0.25 px are exact
BASE = rng.normal(0, 1, (1200 * UP, 800 * UP))
BASE = np.cumsum(np.cumsum(BASE, 0), 1)
BASE = BASE[8:, 8:] - BASE[:-8, 8:] - BASE[8:, :-8] + BASE[:-8, :-8]  # 8x8 box blur


def texture(h: int, w: int, y0: float = 0.0) -> np.ndarray:
    off = 100 * UP + round(y0 * UP)
    hi = BASE[off : off + h * UP, : w * UP]
    lo = hi.reshape(h, UP, w, UP).mean(axis=(1, 3))
    return 128 + 40 * lo / lo.std()


@pytest.mark.parametrize("d", [5, 23, 40, -17, 12.5, 7.25])
def test_phase_correlate_finds_shift(d):
    before = texture(200, 300)
    after = texture(200, 300, y0=d)  # content moved up by d
    s = phase_correlate(before, after)
    assert s.dy == pytest.approx(d, abs=0.5)
    assert abs(s.dx) < 0.5
    assert s.confidence > 0.1


def test_noise_has_low_confidence():
    a = rng.normal(128, 40, (200, 300))
    b = rng.normal(128, 40, (200, 300))
    assert phase_correlate(a, b).confidence < 0.05


def test_changed_region_ignores_static_border():
    h, w = 400, 600
    before = np.full((h, w), 50.0)
    after = before.copy()
    before[100:300, 150:450] = texture(200, 300)
    after[100:300, 150:450] = texture(200, 300, y0=20)
    rows, cols = changed_region(before, after)
    assert 95 <= rows.start <= 100 and 300 <= rows.stop <= 305
    assert 145 <= cols.start <= 150 and 450 <= cols.stop <= 455


def test_vertical_shift_on_screenshot_like_frames():
    h, w = 400, 600
    before = np.zeros((h, w, 4), np.uint8)
    after = before.copy()
    before[60:360, 100:500, :3] = texture(300, 400)[..., None].astype(np.uint8)
    after[60:360, 100:500, :3] = texture(300, 400, y0=31)[..., None].astype(np.uint8)
    s = vertical_shift(before, after)
    assert s is not None and s.dy == pytest.approx(31, abs=1)


def test_vertical_shift_none_when_static():
    frame = texture(100, 100)
    assert vertical_shift(frame, frame) is None


def test_to_gray_drops_alpha():
    rgba = np.zeros((2, 2, 4), np.uint8)
    rgba[..., 3] = 255
    assert to_gray(rgba).max() == 0
