import ast
import os
import subprocess
from pathlib import Path

UUID = "touchpad-speed-control@ritesh"
SCHEMA_ID = "org.gnome.shell.extensions.touchpad-speed-control"
DCONF_PATH = "/org/gnome/shell/extensions/touchpad-speed-control/"
FILES_APP = "org.gnome.Nautilus"
TERMINAL_APPS = ("org.gnome.Ptyxis", "org.gnome.Console", "org.gnome.Terminal")


def _data_dirs() -> list[Path]:
    home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share")
    system = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    return [Path(d) for d in [home, *system.split(":")] if d]


def schema_dir() -> Path | None:
    for base in _data_dirs():
        candidate = base / "gnome-shell/extensions" / UUID / "schemas"
        if (candidate / "gschemas.compiled").exists():
            return candidate
    return None


def _gsettings(schemas: Path, *args: str) -> str:
    cmd = ["gsettings", "--schemadir", str(schemas), *args]
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()


def is_customized(key: str) -> bool:
    out = subprocess.run(["dconf", "read", DCONF_PATH + key], capture_output=True, text=True).stdout
    return bool(out.strip())


def starter_app_factors(installed: set[str], speed: float) -> dict[str, float]:
    terminal = next((app for app in TERMINAL_APPS if app in installed), None)
    return {app: speed for app in (FILES_APP, terminal) if app in installed}


def parse_factors(text: str) -> dict[str, float]:
    return ast.literal_eval(text.removeprefix("@a{sd} "))


def load_app_factors(schemas: Path) -> dict[str, float]:
    return parse_factors(_gsettings(schemas, "get", SCHEMA_ID, "app-factors"))


def save_app_factors(schemas: Path, factors: dict[str, float]) -> None:
    value = repr(factors) if factors else "@a{sd} {}"
    for key in ("app-factors", "h-app-factors"):
        _gsettings(schemas, "set", SCHEMA_ID, key, value)


def load_global_factor(schemas: Path) -> float:
    return float(_gsettings(schemas, "get", SCHEMA_ID, "global-factor"))


def save_global_factor(schemas: Path, factor: float) -> None:
    for key in ("global-factor", "h-global-factor"):
        _gsettings(schemas, "set", SCHEMA_ID, key, f"{factor:.2f}")


def is_enabled() -> bool:
    try:
        out = subprocess.run(["gnome-extensions", "list", "--enabled"], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return False
    return UUID in out.split()


def enable() -> None:
    subprocess.run(["gnome-extensions", "enable", UUID], check=True)

