from statistics import median

from .capture import Screenshotter
from .measure import vertical_shift
from .vtouchpad import VirtualTouchpad

MIN_FACTOR, MAX_FACTOR = 0.05, 5.0
MIN_CONFIDENCE = 0.08
MIN_DISTANCE_PX = 2.0


class Gauge:
    def __init__(self, pad: VirtualTouchpad, screenshots: Screenshotter, samples: int = 3):
        self.pad = pad
        self.screenshots = screenshots
        self.samples = samples

    def measure(self) -> float | None:
        """Median scroll distance in pixels of one swipe, alternating direction between samples."""
        distances = []
        fingers_up = True
        for _ in range(self.samples):
            distance = self._swipe_distance(fingers_up)
            if distance is None:
                fingers_up = not fingers_up  # probably at the end of the page
                distance = self._swipe_distance(fingers_up)
            if distance is not None:
                distances.append(distance)
            fingers_up = not fingers_up
        return median(distances) if distances else None

    def _swipe_distance(self, fingers_up: bool) -> float | None:
        before = self.screenshots.grab_when_still()
        self.pad.swipe(fingers_up=fingers_up)
        after = self.screenshots.grab_when_still()
        shift = vertical_shift(before, after)
        if shift is None or shift.confidence < MIN_CONFIDENCE or abs(shift.dy) < MIN_DISTANCE_PX:
            return None
        return abs(shift.dy)


def balanced_factors(distances: dict[str, float], reference: str, reference_factor: float) -> dict[str, float]:
    """Factors that make one swipe scroll as far in every app as in the reference app."""
    target = distances[reference]
    return {
        app: round(min(max(reference_factor * target / px, MIN_FACTOR), MAX_FACTOR), 2)
        for app, px in distances.items()
    }
