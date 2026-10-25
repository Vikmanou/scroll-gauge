import ast
import configparser
import os
import subprocess
from pathlib import Path

UUID = "touchpad-speed-control@ritesh"
SCHEMA_ID = "org.gnome.shell.extensions.touchpad-speed-control"


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


def parse_factors(text: str) -> dict[str, float]:
    return ast.literal_eval(text.removeprefix("@a{sd} "))


def load_app_factors(schemas: Path) -> dict[str, float]:
    return parse_factors(_gsettings(schemas, "get", SCHEMA_ID, "app-factors"))


def save_app_factors(schemas: Path, factors: dict[str, float]) -> None:
    value = repr(factors) if factors else "@a{sd} {}"
    for key in ("app-factors", "h-app-factors"):
        _gsettings(schemas, "set", SCHEMA_ID, key, value)


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


def installed_apps() -> dict[str, str]:
    apps: dict[str, str] = {}
    for base in _data_dirs():
        root = base / "applications"
        for desktop_file in sorted(root.rglob("*.desktop")):
            app_id = str(desktop_file.relative_to(root)).replace("/", "-").removesuffix(".desktop")
            if app_id in apps:
                continue
            name = visible_app_name(desktop_file)
            if name:
                apps[app_id] = name
    return apps


def visible_app_name(desktop_file: Path) -> str | None:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        parser.read(desktop_file, encoding="utf-8")
        entry = parser["Desktop Entry"]
    except (configparser.Error, UnicodeDecodeError, KeyError):
        return None
    if entry.get("type") != "Application" or "true" in (entry.get("nodisplay"), entry.get("hidden")):
        return None
    return entry.get("name")
