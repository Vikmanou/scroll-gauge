import json
import shutil
import subprocess
from dataclasses import dataclass


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

