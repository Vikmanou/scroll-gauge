# Scroll Gauge

A GNOME app for setting touchpad scroll speed on GNOME Wayland: one global speed, per-app speeds, and a demo page to feel the result while you drag the slider.

WSF's own window only sets one global speed, and Touchpad Speed Control's settings only set per-app speeds, and neither lets you try the speed while you adjust it. Scroll Gauge puts both in one window with a live demo.

## Where it runs

Linux, GNOME on Wayland, any distribution. Not GNOME on X11 or other desktops (WSF is GNOME Wayland only). Tested on Fedora 44, GNOME 50.

## Requirements

- Python 3.11+ with PyGObject, GTK 4 and libadwaita 1.4+ (already installed on GNOME). If missing: `sudo dnf install python3-gobject libadwaita` (Fedora), `sudo apt install python3-gi gir1.2-adw-1` (Ubuntu/Debian), `sudo pacman -S python-gobject libadwaita` (Arch)
- [WSF](https://github.com/daniel-g-carrasco/wayland-scroll-factor), enabled with `wsf enable`
- [Touchpad Speed Control](https://extensions.gnome.org/extension/10008/touchpad-speed-control/) for per-app speeds (optional)

## Install

```bash
git clone https://github.com/Vikmanou/Scroll-Gauge.git
cd Scroll-Gauge
pip install .
```

## Usage

Run `scrollgauge`.

- **Global speed:** used by every app without its own speed.
- **Per-app speeds:** pick an app, press Add, then drag its slider. Touchpad Speed Control switches to it whenever you use that app.
- **Try it:** swipe on the demo text. Moving any slider applies that speed to the demo straight away, and the window shows how many lines your last swipe moved.

Changes save automatically.

## Limitations

- The demo shows the speed in Scroll Gauge's own window. Apps scale scrolling differently, so the same speed can still feel a little different elsewhere.
- Per-app speeds need Touchpad Speed Control.
- Horizontal scrolling gets the same speed as vertical.

## Development

```bash
pip install -e '.[test]'
pytest
```

## License

MIT
