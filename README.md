# Scroll Gauge

Touchpad scrolling on GNOME Wayland covers a different distance in every app: GTK4, Firefox and Chromium each scale scroll input their own way. [Wayland Scroll Factor](https://github.com/daniel-g-carrasco/wayland-scroll-factor) (WSF) can slow scrolling down, and [Touchpad Speed Control](https://github.com/ritesh-777/touchpad-speed-control) can give each app its own factor, but you still have to work out what those factors should be.

Scroll Gauge works them out for you. It sends an identical swipe from a virtual touchpad to each app, measures how far the content moves, and saves per-app factors so that one swipe scrolls the same distance everywhere.

## How it works

1. A virtual two-finger touchpad is created through `/dev/uinput`. GNOME treats it like real hardware, so its swipes go through WSF like yours do.
2. Screenshots are taken through the `org.freedesktop.portal.Screenshot` portal before and after each swipe, waiting until the content stops moving.
3. Phase correlation over the changed region finds the scroll distance to sub-pixel accuracy. Each app is sampled three times and the median is used.
4. Every app's factor is scaled so its distance matches the reference app's, then saved to Touchpad Speed Control (or exported as a JSON file you can import).

## Where it runs

Scroll Gauge runs on **Linux with GNOME on Wayland**, on any distribution.

| Environment | Supported |
| --- | --- |
| GNOME on Wayland (Fedora, Ubuntu, Debian, Arch, openSUSE, …) | Yes |
| GNOME on X11 | No: GNOME Shell doesn't handle touchpad input there, so WSF can't hook it |
| KDE Plasma, Sway, Hyprland and other desktops | No: WSF only supports GNOME |
| macOS, Windows | No |

Tested on Fedora 44 with GNOME 50.

## Requirements

- Python 3.11 or newer
- [WSF](https://github.com/daniel-g-carrasco/wayland-scroll-factor), enabled with `wsf enable`
- [Touchpad Speed Control](https://extensions.gnome.org/extension/10008/touchpad-speed-control/) to apply factors automatically (optional, since `--json` works without it)

## Install

```bash
git clone https://github.com/Vikmanou/Scroll-Gauge.git
cd Scroll-Gauge
pip install -r requirements.txt
pip install .
```

`evdev` and `PyGObject` build from source, so install the usual build packages first:

```bash
# Fedora
sudo dnf install gcc python3-devel kernel-headers gobject-introspection-devel cairo-gobject-devel
# Ubuntu / Debian
sudo apt install build-essential python3-dev pkg-config libgirepository-2.0-dev libcairo2-dev
# Arch
sudo pacman -S base-devel linux-api-headers gobject-introspection cairo
```

### Allow access to /dev/uinput

Creating the virtual touchpad needs write access to `/dev/uinput`, which is root-only by default. Add a udev rule that grants it to the logged-in user:

```bash
echo 'KERNEL=="uinput", SUBSYSTEM=="misc", TAG+="uaccess", OPTIONS+="static_node=uinput"' | sudo tee /etc/udev/rules.d/60-uinput.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Usage

Find the app ids you want to calibrate:

```bash
scrollgauge apps firefox
```

Calibrate against an app whose scrolling already feels right:

```bash
scrollgauge run org.gnome.Ptyxis org.mozilla.firefox org.gnome.Nautilus
```

For each app, press Enter and then hover the pointer over long, static content, such as a terminal full of `seq 1 5000` or a plain text page. Scroll Gauge swipes three times and moves on. While it runs it pauses Touchpad Speed Control and sets WSF to a fixed calibration factor, and it restores both afterwards, including on Ctrl-C.

| Option | Effect |
| --- | --- |
| `--reference-factor F` | Factor for the reference app (default: current WSF vertical factor) |
| `--samples N` | Swipes per app (default 3) |
| `--dry-run` | Print factors without saving |
| `--json PATH` | Write a Touchpad Speed Control import file instead of changing settings |

`scrollgauge measure` measures a single app and prints the distance, which is useful for checking a setup.

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
