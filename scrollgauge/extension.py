import json
import subprocess
from pathlib import Path

from gi.repository import Gio, GLib

UUID = "touchpad-speed-control@ritesh"
SCHEMA_ID = "org.gnome.shell.extensions.touchpad-speed-control"
INSTALL_DIRS = [
    Path.home() / ".local/share/gnome-shell/extensions",
    Path("/usr/share/gnome-shell/extensions"),
]


def load_settings() -> Gio.Settings | None:
    for base in INSTALL_DIRS:
        schema_dir = base / UUID / "schemas"
        if not (schema_dir / "gschemas.compiled").exists():
            continue
        source = Gio.SettingsSchemaSource.new_from_directory(
            str(schema_dir), Gio.SettingsSchemaSource.get_default(), False
        )
        schema = source.lookup(SCHEMA_ID, False)
        if schema is not None:
            return Gio.Settings.new_full(schema, None, None)
    return None


def is_enabled() -> bool:
    shell = Gio.Settings.new("org.gnome.shell")
    return UUID in shell.get_strv("enabled-extensions") and not shell.get_boolean("disable-user-extensions")


def set_enabled(enabled: bool) -> None:
    subprocess.run(["gnome-extensions", "enable" if enabled else "disable", UUID], check=True)


def write_app_factors(settings: Gio.Settings, factors: dict[str, float]) -> None:
    for key in ("app-factors", "h-app-factors"):
        merged = settings.get_value(key).unpack() | factors
        settings.set_value(key, GLib.Variant("a{sd}", merged))
    Gio.Settings.sync()


def export_json(path: Path, factors: dict[str, float], global_factor: float) -> None:
    axis = {"global_factor": global_factor, "app_factors": factors}
    path.write_text(json.dumps({"version": 1, "vertical": axis, "horizontal": axis}, indent=2) + "\n")


def installed_apps() -> dict[str, str]:
    apps = {}
    for info in Gio.AppInfo.get_all():
        app_id = info.get_id() or ""
        if info.should_show() and app_id.endswith(".desktop"):
            apps[app_id.removesuffix(".desktop")] = info.get_display_name()
    return dict(sorted(apps.items()))
