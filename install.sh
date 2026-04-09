#!/bin/bash
set -euo pipefail

echo "======================================"
echo " Installing FireCenter"
echo "======================================"

if [ "${SUDO_USER:-}" ]; then
  VENV_OWNER="$SUDO_USER"
  SUDO_PREFIX="sudo -u $VENV_OWNER"
else
  VENV_OWNER=""
  SUDO_PREFIX=""
fi

echo "Creating venv..."
${SUDO_PREFIX} python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Upgrading pip in venv..."
python -m pip install --upgrade pip setuptools wheel

echo "Updating system and installing system packages (requires sudo)"
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y python3-tk xdg-utils mousepad thonny xclip xsel build-essential libssl-dev libffi-dev || true

echo "Installing python packages into venv..."
pip install -r requirements.txt

echo "Creating plugin directory..."
mkdir -p "$(dirname "$0")/.controlpanel_plugins"

echo "======================================"
echo "Install complete!"
echo "======================================"
echo "Run it (in this directory) with:"
echo "source .venv/bin/activate && python menu.py"

rm -- "$0" || true
