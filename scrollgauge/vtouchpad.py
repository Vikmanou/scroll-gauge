import fcntl
import os
import struct
import time

EV_SYN, EV_KEY, EV_ABS = 0x00, 0x01, 0x03
SYN_REPORT = 0
BTN_LEFT, BTN_TOOL_FINGER, BTN_TOUCH, BTN_TOOL_DOUBLETAP = 0x110, 0x145, 0x14A, 0x14D
ABS_X, ABS_Y = 0x00, 0x01
ABS_MT_SLOT, ABS_MT_POSITION_X, ABS_MT_POSITION_Y, ABS_MT_TRACKING_ID = 0x2F, 0x35, 0x36, 0x39
INPUT_PROP_POINTER, INPUT_PROP_BUTTONPAD = 0x00, 0x02
BUS_VIRTUAL = 0x06


def _iow(nr: int, size: int) -> int:
    return (1 << 30) | (size << 16) | (ord("U") << 8) | nr


UI_DEV_CREATE = ord("U") << 8 | 1
UI_DEV_DESTROY = ord("U") << 8 | 2
UI_DEV_SETUP = _iow(3, 92)
UI_ABS_SETUP = _iow(4, 28)
UI_SET_EVBIT = _iow(100, 4)
UI_SET_KEYBIT = _iow(101, 4)
UI_SET_ABSBIT = _iow(103, 4)
UI_SET_PROPBIT = _iow(110, 4)

UNITS_PER_MM = 12  # libinput rejects touchpads that report no resolution
WIDTH_MM, HEIGHT_MM = 100, 70
FINGER_GAP_MM = 20
FRAME_S = 0.008
SETTLE_S = 0.04


class VirtualTouchpad:
    def __init__(self, name: str = "scrollgauge virtual touchpad"):
        self._fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
        self._next_tracking_id = 0
        xmax, ymax = WIDTH_MM * UNITS_PER_MM, HEIGHT_MM * UNITS_PER_MM

        for ev in (EV_SYN, EV_KEY, EV_ABS):
            fcntl.ioctl(self._fd, UI_SET_EVBIT, ev)
        for key in (BTN_LEFT, BTN_TOUCH, BTN_TOOL_FINGER, BTN_TOOL_DOUBLETAP):
            fcntl.ioctl(self._fd, UI_SET_KEYBIT, key)
        for prop in (INPUT_PROP_POINTER, INPUT_PROP_BUTTONPAD):
            fcntl.ioctl(self._fd, UI_SET_PROPBIT, prop)
        for code, maximum, resolution in (
            (ABS_X, xmax, UNITS_PER_MM),
            (ABS_Y, ymax, UNITS_PER_MM),
            (ABS_MT_SLOT, 1, 0),
            (ABS_MT_TRACKING_ID, 65535, 0),
            (ABS_MT_POSITION_X, xmax, UNITS_PER_MM),
            (ABS_MT_POSITION_Y, ymax, UNITS_PER_MM),
        ):
            fcntl.ioctl(self._fd, UI_SET_ABSBIT, code)
            fcntl.ioctl(self._fd, UI_ABS_SETUP, struct.pack("HxxIiiiii", code, 0, 0, maximum, 0, 0, resolution))

        setup = struct.pack("HHHH80sI", BUS_VIRTUAL, 0, 0, 0, name.encode()[:79], 0)
        fcntl.ioctl(self._fd, UI_DEV_SETUP, setup)
        fcntl.ioctl(self._fd, UI_DEV_CREATE)

    def close(self) -> None:
        fcntl.ioctl(self._fd, UI_DEV_DESTROY)
        os.close(self._fd)

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

    def _write(self, ev_type: int, code: int, value: int) -> None:
        os.write(self._fd, struct.pack("qqHHi", 0, 0, ev_type, code, value))

    def _syn(self) -> None:
        self._write(EV_SYN, SYN_REPORT, 0)

    def _touch_down(self, xs: list[int], y: int) -> None:
        for slot in range(len(xs)):
            self._next_tracking_id = (self._next_tracking_id + 1) % 65535
            self._write(EV_ABS, ABS_MT_SLOT, slot)
            self._write(EV_ABS, ABS_MT_TRACKING_ID, self._next_tracking_id)
        self._write(EV_KEY, BTN_TOUCH, 1)
        self._write(EV_KEY, BTN_TOOL_DOUBLETAP, 1)
        self._move(xs, y)

    def _move(self, xs: list[int], y: int) -> None:
        for slot, x in enumerate(xs):
            self._write(EV_ABS, ABS_MT_SLOT, slot)
            self._write(EV_ABS, ABS_MT_POSITION_X, x)
            self._write(EV_ABS, ABS_MT_POSITION_Y, y)
        self._write(EV_ABS, ABS_X, xs[0])
        self._write(EV_ABS, ABS_Y, y)
        self._syn()

    def _hold(self, xs: list[int], y: int, seconds: float) -> None:
        for _ in range(round(seconds / FRAME_S)):
            time.sleep(FRAME_S)
            self._move(xs, y)

    def _lift(self) -> None:
        for slot in range(2):
            self._write(EV_ABS, ABS_MT_SLOT, slot)
            self._write(EV_ABS, ABS_MT_TRACKING_ID, -1)
        self._write(EV_KEY, BTN_TOUCH, 0)
        self._write(EV_KEY, BTN_TOOL_DOUBLETAP, 0)
        self._syn()
