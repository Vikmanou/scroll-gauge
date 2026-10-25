import argparse
import sys
import time
from pathlib import Path

from . import __version__, extension, wsf
from .calibrate import Gauge, balanced_factors

# Linear scaling makes the factor cancel out; a low one keeps each swipe's
# scroll well inside the measured region so the offset can't alias.
CALIBRATION_FACTOR = 0.3
HOVER_COUNTDOWN_S = 3
DEVICE_WARMUP_S = 1.0


def _open_gauge(samples: int):
    from .capture import Screenshotter
    from .vtouchpad import VirtualTouchpad

    try:
        pad = VirtualTouchpad()
    except PermissionError:
        sys.exit("No access to /dev/uinput. Run ./install.sh, then log out and back in.")
    time.sleep(DEVICE_WARMUP_S)
    return pad, Gauge(pad, Screenshotter(), samples)


def _wait_for_hover(label: str) -> None:
    input(f"\n{label}: press Enter, then hover the pointer over its scrollable content. ")
    for remaining in range(HOVER_COUNTDOWN_S, 0, -1):
        print(f"  measuring in {remaining}…", end="\r", flush=True)
        time.sleep(1)
    print(" " * 30, end="\r")


def cmd_apps(args) -> None:
    for app_id, name in extension.installed_apps().items():
        if not args.filter or args.filter.lower() in f"{app_id} {name}".lower():
            print(f"{app_id:45} {name}")


def cmd_measure(args) -> None:
    pad, gauge = _open_gauge(args.samples)
    with pad:
        _wait_for_hover("Target app")
        distance = gauge.measure()
    if distance is None:
        sys.exit("No scroll detected. Hover over plain scrollable content and try again.")
    print(f"One swipe scrolled {distance:.1f} px at WSF factor {wsf.read().vertical:.2f}")


def cmd_run(args) -> None:
    apps = extension.installed_apps()
    unknown = [a for a in [args.reference, *args.apps] if a not in apps]
    if unknown:
        sys.exit(f"Unknown app id(s): {', '.join(unknown)}. See `scrollgauge apps`.")

    saved = wsf.read()
    reference_factor = args.reference_factor or saved.vertical
    extension_was_enabled = extension.is_enabled()
    distances: dict[str, float] = {}

    pad, gauge = _open_gauge(args.samples)
    try:
        if extension_was_enabled:
            extension.set_enabled(False)
        wsf.write(wsf.Factors(CALIBRATION_FACTOR, CALIBRATION_FACTOR))
        with pad:
            for app_id in [args.reference, *args.apps]:
                _wait_for_hover(f"{apps[app_id]} ({app_id})")
                distance = gauge.measure()
                if distance is None:
                    print(f"  {app_id}: no scroll detected, skipping")
                    continue
                print(f"  {app_id}: {distance:.1f} px per swipe")
                distances[app_id] = distance
    finally:
        wsf.write(saved)
        if extension_was_enabled:
            extension.set_enabled(True)

    if args.reference not in distances:
        sys.exit("The reference app could not be measured; nothing to balance against.")

    factors = balanced_factors(distances, args.reference, reference_factor)
    print(f"\n{'app':45} {'px/swipe':>9} {'factor':>7}")
    for app_id, factor in factors.items():
        print(f"{app_id:45} {distances[app_id]:9.1f} {factor:7.2f}")

    if args.dry_run:
        return
    settings = extension.load_settings()
    if settings is not None and args.json is None:
        extension.write_app_factors(settings, factors)
        print("\nSaved to Touchpad Speed Control.")
    else:
        path = args.json or Path("scrollgauge-factors.json")
        extension.export_json(path, factors, reference_factor)
        print(f"\nWrote {path}. Import it in Touchpad Speed Control's settings.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="scrollgauge", description="Auto-calibrate per-app touchpad scroll speed on GNOME Wayland.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("apps", help="list app ids to calibrate")
    p.add_argument("filter", nargs="?")
    p.set_defaults(func=cmd_apps)

    p = sub.add_parser("measure", help="measure one swipe in the app under the pointer")
    p.add_argument("--samples", type=int, default=3)
    p.set_defaults(func=cmd_measure)

    p = sub.add_parser("run", help="calibrate apps against a reference app")
    p.add_argument("reference", help="app id whose scroll feel is right, e.g. org.gnome.Ptyxis")
    p.add_argument("apps", nargs="+", help="app ids to balance against the reference")
    p.add_argument("--reference-factor", type=float, help="factor for the reference app (default: current WSF value)")
    p.add_argument("--samples", type=int, default=3)
    p.add_argument("--dry-run", action="store_true", help="print factors without saving")
    p.add_argument("--json", type=Path, help="write an import file instead of changing settings")
    p.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except wsf.WsfError as err:
        sys.exit(str(err))
    except KeyboardInterrupt:
        sys.exit("\nCancelled.")
