#!/bin/bash
# install.sh — eDio remote control setup for Artix Linux + runit
set -e

DOTFILES="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing dependencies"
sudo pacman -S --needed --noconfirm python-evdev xdotool mpc

echo "==> Installing udev rules"
sudo cp "$DOTFILES/udev/99-edioremote.rules" /etc/udev/rules.d/
sudo cp "$DOTFILES/udev/99-uinput.rules" /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "==> Loading uinput module"
sudo mkdir -p /etc/modules-load.d
echo 'uinput' | sudo tee /etc/modules-load.d/uinput.conf
sudo modprobe uinput

echo "==> Adding $USER to input group"
sudo usermod -aG input "$USER"

echo "==> Installing scripts"
mkdir -p ~/.local/bin
cp "$DOTFILES/remote/remote-daemon.py"    ~/.local/bin/
cp "$DOTFILES/remote/mpc-mute-toggle.sh" ~/.local/bin/
cp "$DOTFILES/remote/ncmpcpp-view.sh"    ~/.local/bin/
chmod +x ~/.local/bin/remote-daemon.py
chmod +x ~/.local/bin/mpc-mute-toggle.sh
chmod +x ~/.local/bin/ncmpcpp-view.sh

echo "==> Installing runit user service"
mkdir -p ~/.config/sv/remote-daemon/log
cp "$DOTFILES/remote/run"      ~/.config/sv/remote-daemon/run
cp "$DOTFILES/remote/log/run"  ~/.config/sv/remote-daemon/log/run
chmod +x ~/.config/sv/remote-daemon/run
chmod +x ~/.config/sv/remote-daemon/log/run

echo "==> Starting service"
sv start ~/.config/sv/remote-daemon || true

echo ""
echo "==> Done."
echo ""
echo "    IMPORTANT: if the input group was just added, log out and back"
echo "    in for it to take effect, then restart the service:"
echo "      sv restart ~/.config/sv/remote-daemon"
echo ""
echo "    Check status with:"
echo "      sv status ~/.config/sv/remote-daemon"
echo ""
echo "    Watch logs with:"
echo "      tail -f ~/.local/share/log/remote-daemon/current"
