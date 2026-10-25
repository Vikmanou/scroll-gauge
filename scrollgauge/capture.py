import os
import secrets
import time
from urllib.parse import unquote, urlparse

import numpy as np
from gi.repository import Gio, GLib
from PIL import Image

PORTAL = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
TIMEOUT_S = 10


class CaptureError(RuntimeError):
    pass


class Screenshotter:
    def __init__(self):
        self._bus = Gio.bus_get_sync(Gio.BusType.SESSION)
        self._sender = self._bus.get_unique_name()[1:].replace(".", "_")

    def grab(self) -> np.ndarray:
        token = "scrollgauge_" + secrets.token_hex(4)
        handle = f"{PORTAL_PATH}/request/{self._sender}/{token}"
        loop = GLib.MainLoop()
        result: dict = {}

        def on_response(_conn, _sender, _path, _iface, _signal, params):
            result["code"], result["results"] = params.unpack()
            loop.quit()

        sub = self._bus.signal_subscribe(
            PORTAL, "org.freedesktop.portal.Request", "Response", handle, None,
            Gio.DBusSignalFlags.NO_MATCH_RULE, on_response,
        )
        timeout = GLib.timeout_add_seconds(TIMEOUT_S, loop.quit)
        try:
            self._bus.call_sync(
                PORTAL, PORTAL_PATH, "org.freedesktop.portal.Screenshot", "Screenshot",
                GLib.Variant("(sa{sv})", ("", {
                    "handle_token": GLib.Variant("s", token),
                    "interactive": GLib.Variant("b", False),
                })),
                None, Gio.DBusCallFlags.NONE, -1, None,
            )
            loop.run()
        finally:
            self._bus.signal_unsubscribe(sub)
            if "code" in result:
                GLib.source_remove(timeout)

        if "code" not in result:
            raise CaptureError("screenshot portal timed out")
        if result["code"] != 0:
            raise CaptureError("screenshot was denied; allow screenshots for scrollgauge and retry")

        path = unquote(urlparse(result["results"]["uri"]).path)
        try:
            with Image.open(path) as img:
                return np.asarray(img.convert("RGB"))
        finally:
            os.unlink(path)

    def grab_when_still(self, interval_s: float = 0.15, max_wait_s: float = 3.0, tolerance: float = 0.5) -> np.ndarray:
        prev = self.grab()
        deadline = time.monotonic() + max_wait_s
        while time.monotonic() < deadline:
            time.sleep(interval_s)
            cur = self.grab()
            if np.abs(cur.astype(np.int16) - prev).mean() < tolerance:
                return cur
            prev = cur
        return prev
