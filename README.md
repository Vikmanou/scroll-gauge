# Scroll Gauge

Measures each app's touchpad scroll speed and sets per-app factors so one swipe scrolls the same distance everywhere.

[WSF](https://github.com/daniel-g-carrasco/wayland-scroll-factor) applies one global factor, and [Touchpad Speed Control](https://github.com/ritesh-777/touchpad-speed-control) applies per-app factors, but you have to find each value by trial and error. Scroll Gauge measures them for you.

## Where it runs

Linux, GNOME on Wayland, any distribution. Not GNOME on X11 or other desktops (WSF is GNOME Wayland only). Tested on Fedora 44, GNOME 50.

## Requirements

- Python 3.11+
- [WSF](https://github.com/daniel-g-carrasco/wayland-scroll-factor), enabled with `wsf enable`
- [Touchpad Speed Control](https://extensions.gnome.org/extension/10008/touchpad-speed-control/) (optional; without it, use `--json`)

## Install

Build packages for `evdev` and `PyGObject`:

```bash
sudo dnf install gcc python3-devel kernel-headers gobject-introspection-devel cairo-gobject-devel  # Fedora
sudo apt install build-essential python3-dev pkg-config libgirepository-2.0-dev libcairo2-dev       # Ubuntu/Debian
sudo pacman -S base-devel linux-api-headers gobject-introspection cairo                            # Arch
```

```bash
git clone https://github.com/Vikmanou/Scroll-Gauge.git
cd Scroll-Gauge
pip install -r requirements.txt
pip install .
```

Allow access to `/dev/uinput`:

```bash
echo 'KERNEL=="uinput", SUBSYSTEM=="misc", TAG+="uaccess", OPTIONS+="static_node=uinput"' | sudo tee /etc/udev/rules.d/60-uinput.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Usage

```bash
scrollgauge apps firefox                                                 # find app ids
scrollgauge run org.gnome.Ptyxis org.mozilla.firefox org.gnome.Nautilus  # first id is the reference
```

For each app, press Enter, then hover over long static content (e.g. `seq 1 5000` in a terminal).

| Option | Effect |
| --- | --- |
| `--reference-factor F` | Reference app's factor (default: current WSF factor) |
| `--samples N` | Swipes per app (default 3) |
| `--dry-run` | Print factors without saving |
| `--json PATH` | Write a Touchpad Speed Control import file |

`scrollgauge measure` measures the app under the pointer.

## Limitations

- Only vertical scrolling is measured. The same factor is applied horizontally.
- Animated or lazy-loading pages can give unreliable readings. Pages with low-confidence readings are skipped.
- GNOME may ask once for permission to take screenshots.

## Development

```bash
pip install -e '.[test]'
pytest
```

## License

MIT
