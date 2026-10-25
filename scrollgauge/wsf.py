import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

PRELOAD_LIBRARY = "libwsf_preload.so"
CONFIG_PATH = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "wayland-scroll-factor/config"


class WsfError(RuntimeError):
    pass


@dataclass(frozen=True)
class Factors:
    vertical: float
    horizontal: float


def _run(*args: str) -> str:
    exe = shutil.which("wsf")
    if exe is None:
        raise WsfError("wsf not found; install Wayland Scroll Factor first")
    proc = subprocess.run([exe, *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise WsfError(proc.stderr.strip() or f"wsf {' '.join(args)} failed")
    return proc.stdout


def read() -> Factors:
    data = json.loads(_run("get", "--json"))
    return Factors(data["scroll_vertical_factor"], data["scroll_horizontal_factor"])


def write(factors: Factors) -> None:
    _run("set", "--scroll-vertical", f"{factors.vertical:.4f}", "--scroll-horizontal", f"{factors.horizontal:.4f}")


def is_active() -> bool:
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != os.getuid() or (proc / "comm").read_text().strip() != "gnome-shell":
                continue
            return PRELOAD_LIBRARY in (proc / "maps").read_text()
        except OSError:
            continue
    return False
