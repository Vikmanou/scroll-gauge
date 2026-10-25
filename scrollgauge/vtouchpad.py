"""A virtual two-finger touchpad built on uinput."""

import time

from evdev import AbsInfo, UInput, ecodes as e

RES = 12  # units per mm; libinput refuses touchpads without a resolution
WIDTH_MM, HEIGHT_MM = 100, 70
FRAME_S = 0.008
FINGER_GAP_MM = 20


class VirtualTouchpad:
    def __init__(self, name: str = "scrollgauge virtual touchpad"):
        xmax, ymax = WIDTH_MM * RES, HEIGHT_MM * RES
        caps = {
            e.EV_KEY: [e.BTN_LEFT, e.BTN_TOUCH, e.BTN_TOOL_FINGER, e.BTN_TOOL_DOUBLETAP],
            e.EV_ABS: [
                (e.ABS_X, AbsInfo(0, 0, xmax, 0, 0, RES)),
                (e.ABS_Y, AbsInfo(0, 0, ymax, 0, 0, RES)),
                (e.ABS_MT_SLOT, AbsInfo(0, 0, 1, 0, 0, 0)),
                (e.ABS_MT_TRACKING_ID, AbsInfo(0, 0, 65535, 0, 0, 0)),
                (e.ABS_MT_POSITION_X, AbsInfo(0, 0, xmax, 0, 0, RES)),
                (e.ABS_MT_POSITION_Y, AbsInfo(0, 0, ymax, 0, 0, RES)),
            ],
        }
        self._ui = UInput(caps, name=name, input_props=[e.INPUT_PROP_POINTER, e.INPUT_PROP_BUTTONPAD])
        self._tracking_id = 0

    def close(self) -> None:
        self._ui.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _fingers(self, xs: list[int], y: int) -> None:
        for slot, x in enumerate(xs):
            self._ui.write(e.EV_ABS, e.ABS_MT_SLOT, slot)
            self._ui.write(e.EV_ABS, e.ABS_MT_POSITION_X, x)
            self._ui.write(e.EV_ABS, e.ABS_MT_POSITION_Y, y)
        self._ui.write(e.EV_ABS, e.ABS_X, xs[0])
        self._ui.write(e.EV_ABS, e.ABS_Y, y)
        self._ui.syn()

    def swipe(self, dist_mm: float = 30, duration_ms: float = 300, hold_ms: float = 150, direction: int = 1) -> None:
        """Two-finger vertical swipe. direction=1 moves the fingers up.

        Holding still before lifting stops apps from adding momentum, so the
        measured distance reflects only the base scroll speed.
        """
        cx = WIDTH_MM * RES // 2
        gap = FINGER_GAP_MM * RES // 2
        xs = [cx - gap, cx + gap]
        span = dist_mm * RES
        y = HEIGHT_MM * RES // 2 + direction * span // 2

        for slot in range(2):
            self._tracking_id = (self._tracking_id + 1) % 65535
            self._ui.write(e.EV_ABS, e.ABS_MT_SLOT, slot)
            self._ui.write(e.EV_ABS, e.ABS_MT_TRACKING_ID, self._tracking_id)
        self._ui.write(e.EV_KEY, e.BTN_TOUCH, 1)
        self._ui.write(e.EV_KEY, e.BTN_TOOL_DOUBLETAP, 1)
        self._fingers(xs, y)

        # Rest briefly so libinput settles on a two-finger touch before motion.
        for _ in range(5):
            time.sleep(FRAME_S)
            self._fingers(xs, y)

        steps = max(int(duration_ms / 1000 / FRAME_S), 1)
        start = y
        for i in range(1, steps + 1):
            time.sleep(FRAME_S)
            y = start - direction * round(span * i / steps)
            self._fingers(xs, y)

        for _ in range(max(int(hold_ms / 1000 / FRAME_S), 0)):
            time.sleep(FRAME_S)
            self._fingers(xs, y)

        for slot in range(2):
            self._ui.write(e.EV_ABS, e.ABS_MT_SLOT, slot)
            self._ui.write(e.EV_ABS, e.ABS_MT_TRACKING_ID, -1)
        self._ui.write(e.EV_KEY, e.BTN_TOUCH, 0)
        self._ui.write(e.EV_KEY, e.BTN_TOOL_DOUBLETAP, 0)
        self._ui.syn()
