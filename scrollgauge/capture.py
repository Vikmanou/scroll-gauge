import os
import secrets
import time
from urllib.parse import unquote, urlparse

import numpy as np
from jeepney import DBusAddress, MatchRule, new_method_call
from jeepney.bus_messages import message_bus
from jeepney.io.blocking import open_dbus_connection
from PIL import Image

PORTAL = DBusAddress(
    "/org/freedesktop/portal/desktop",
    bus_name="org.freedesktop.portal.Desktop",
    interface="org.freedesktop.portal.Screenshot",
)
TIMEOUT_S = 10


class CaptureError(RuntimeError):
    pass


class Screenshotter:
    def __init__(self):
        self._conn = open_dbus_connection(bus="SESSION")
        self._sender = self._conn.unique_name[1:].replace(".", "_")

    def grab(self) -> np.ndarray:
        token = "scrollgauge_" + secrets.token_hex(4)
        response = MatchRule(
            type="signal",
            interface="org.freedesktop.portal.Request",
            member="Response",
            path=f"/org/freedesktop/portal/desktop/request/{self._sender}/{token}",
        )
        self._conn.send_and_get_reply(message_bus.AddMatch(response))
        try:
            with self._conn.filter(response) as queue:
                options = {"handle_token": ("s", token), "interactive": ("b", False)}
                self._conn.send_and_get_reply(new_method_call(PORTAL, "Screenshot", "sa{sv}", ("", options)))
                try:
                    code, results = self._conn.recv_until_filtered(queue, timeout=TIMEOUT_S).body
                except TimeoutError:
                    raise CaptureError("screenshot portal timed out") from None
        finally:
            self._conn.send_and_get_reply(message_bus.RemoveMatch(response))

        if code != 0:
            raise CaptureError("screenshot was denied; allow screenshots for scrollgauge and retry")

        path = unquote(urlparse(results["uri"][1]).path)
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
