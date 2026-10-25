import ast
import configparser
import json
import os
import subprocess
from pathlib import Path

UUID = "touchpad-speed-control@ritesh"
SCHEMA_ID = "org.gnome.shell.extensions.touchpad-speed-control"
FACTOR_KEYS = ("app-factors", "h-app-factors")


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


def read_app_factors(schemas: Path, key: str = "app-factors") -> dict[str, float]:
    text = _gsettings(schemas, "get", SCHEMA_ID, key).removeprefix("@a{sd} ")
    return ast.literal_eval(text)


def write_app_factors(schemas: Path, factors: dict[str, float]) -> None:
    for key in FACTOR_KEYS:
        merged = read_app_factors(schemas, key) | factors
        _gsettings(schemas, "set", SCHEMA_ID, key, repr(merged))


def is_enabled() -> bool:
    try:
        out = subprocess.run(["gnome-extensions", "list", "--enabled"], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return False
    return UUID in out.split()


def set_enabled(enabled: bool) -> None:
    subprocess.run(["gnome-extensions", "enable" if enabled else "disable", UUID], check=True)


def export_json(path: Path, factors: dict[str, float], global_factor: float) -> None:
    axis = {"global_factor": global_factor, "app_factors": factors}
    path.write_text(json.dumps({"version": 1, "vertical": axis, "horizontal": axis}, indent=2) + "\n")


def installed_apps() -> dict[str, str]:
    apps: dict[str, str] = {}
    for base in _data_dirs():
        root = base / "applications"
        for desktop_file in sorted(root.rglob("*.desktop")):
            app_id = str(desktop_file.relative_to(root)).replace("/", "-").removesuffix(".desktop")
            if app_id in apps:
                continue
            name = _visible_app_name(desktop_file)
            if name:
                apps[app_id] = name
    return dict(sorted(apps.items()))


def _visible_app_name(desktop_file: Path) -> str | None:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        parser.read(desktop_file, encoding="utf-8")
        entry = parser["Desktop Entry"]
    except (configparser.Error, UnicodeDecodeError, KeyError):
        return None
    if entry.get("type") != "Application" or "true" in (entry.get("nodisplay"), entry.get("hidden")):
        return None
    return entry.get("name")
