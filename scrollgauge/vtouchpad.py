import time

from evdev import AbsInfo, UInput, ecodes as e

UNITS_PER_MM = 12  # libinput rejects touchpads that report no resolution
WIDTH_MM, HEIGHT_MM = 100, 70
FINGER_GAP_MM = 20
FRAME_S = 0.008
SETTLE_S = 0.04


class VirtualTouchpad:
    def __init__(self, name: str = "scrollgauge virtual touchpad"):
        xmax, ymax = WIDTH_MM * UNITS_PER_MM, HEIGHT_MM * UNITS_PER_MM
        caps = {
            e.EV_KEY: [e.BTN_LEFT, e.BTN_TOUCH, e.BTN_TOOL_FINGER, e.BTN_TOOL_DOUBLETAP],
            e.EV_ABS: [
                (e.ABS_X, AbsInfo(0, 0, xmax, 0, 0, UNITS_PER_MM)),
                (e.ABS_Y, AbsInfo(0, 0, ymax, 0, 0, UNITS_PER_MM)),
                (e.ABS_MT_SLOT, AbsInfo(0, 0, 1, 0, 0, 0)),
                (e.ABS_MT_TRACKING_ID, AbsInfo(0, 0, 65535, 0, 0, 0)),
                (e.ABS_MT_POSITION_X, AbsInfo(0, 0, xmax, 0, 0, UNITS_PER_MM)),
                (e.ABS_MT_POSITION_Y, AbsInfo(0, 0, ymax, 0, 0, UNITS_PER_MM)),
            ],
        }
        self._ui = UInput(caps, name=name, input_props=[e.INPUT_PROP_POINTER, e.INPUT_PROP_BUTTONPAD])
        self._next_tracking_id = 0

    def close(self) -> None:
        self._ui.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def swipe(self, dist_mm: float = 30, duration_ms: float = 300, hold_ms: float = 150, fingers_up: bool = True) -> None:
        """Two-finger vertical swipe that pauses before lifting, so apps add no momentum."""
        direction = 1 if fingers_up else -1
        center_x = WIDTH_MM * UNITS_PER_MM // 2
        half_gap = FINGER_GAP_MM * UNITS_PER_MM // 2
        xs = [center_x - half_gap, center_x + half_gap]
        span = dist_mm * UNITS_PER_MM
        start_y = HEIGHT_MM * UNITS_PER_MM // 2 + direction * span // 2

        self._touch_down(xs, start_y)
        self._hold(xs, start_y, SETTLE_S)

        steps = max(round(duration_ms / 1000 / FRAME_S), 1)
        for i in range(1, steps + 1):
            time.sleep(FRAME_S)
            self._move(xs, start_y - direction * round(span * i / steps))

        end_y = start_y - direction * span
        self._hold(xs, end_y, hold_ms / 1000)
        self._lift()

    def _touch_down(self, xs: list[int], y: int) -> None:
        for slot in range(len(xs)):
            self._next_tracking_id = (self._next_tracking_id + 1) % 65535
            self._ui.write(e.EV_ABS, e.ABS_MT_SLOT, slot)
            self._ui.write(e.EV_ABS, e.ABS_MT_TRACKING_ID, self._next_tracking_id)
        self._ui.write(e.EV_KEY, e.BTN_TOUCH, 1)
        self._ui.write(e.EV_KEY, e.BTN_TOOL_DOUBLETAP, 1)
        self._move(xs, y)

    def _move(self, xs: list[int], y: int) -> None:
        for slot, x in enumerate(xs):
            self._ui.write(e.EV_ABS, e.ABS_MT_SLOT, slot)
            self._ui.write(e.EV_ABS, e.ABS_MT_POSITION_X, x)
            self._ui.write(e.EV_ABS, e.ABS_MT_POSITION_Y, y)
        self._ui.write(e.EV_ABS, e.ABS_X, xs[0])
        self._ui.write(e.EV_ABS, e.ABS_Y, y)
        self._ui.syn()

    def _hold(self, xs: list[int], y: int, seconds: float) -> None:
        for _ in range(round(seconds / FRAME_S)):
            time.sleep(FRAME_S)
            self._move(xs, y)

    def _lift(self) -> None:
        for slot in range(2):
            self._ui.write(e.EV_ABS, e.ABS_MT_SLOT, slot)
            self._ui.write(e.EV_ABS, e.ABS_MT_TRACKING_ID, -1)
        self._ui.write(e.EV_KEY, e.BTN_TOUCH, 0)
        self._ui.write(e.EV_KEY, e.BTN_TOOL_DOUBLETAP, 0)
        self._ui.syn()
