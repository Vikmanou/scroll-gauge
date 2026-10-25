#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "$0")" && pwd)"
rule=/etc/udev/rules.d/60-scrollgauge-uinput.rules
launcher="$HOME/.local/bin/scrollgauge"

if [[ "${1:-}" == "--uninstall" ]]; then
    sudo rm -f "$rule"
    sudo udevadm control --reload-rules
    rm -f "$launcher"
    echo "Removed $rule and $launcher."
    exit 0
fi

sudo dnf install -y python3-evdev python3-numpy python3-pillow python3-gobject

# uaccess grants /dev/uinput to the logged-in seat user only, unlike the input group.
echo 'KERNEL=="uinput", SUBSYSTEM=="misc", TAG+="uaccess", OPTIONS+="static_node=uinput"' | sudo tee "$rule" >/dev/null
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=misc --sysname-match=uinput

mkdir -p "$(dirname "$launcher")"
cat > "$launcher" <<EOF
#!/bin/sh
PYTHONPATH="$repo\${PYTHONPATH:+:\$PYTHONPATH}" exec python3 -m scrollgauge "\$@"
EOF
chmod +x "$launcher"

echo "Installed. Run: scrollgauge apps"
