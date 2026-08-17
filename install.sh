#!/bin/bash
set -euo pipefail

echo "======================================"
echo " Installing FireCenter"
echo "======================================"

# Determine the non-root user running the script
if [ "${SUDO_USER:-}" ]; then
  VENV_OWNER="$SUDO_USER"
  SUDO_PREFIX="sudo -u $VENV_OWNER"
  USER_HOME=$(eval echo "~$SUDO_USER")
else
  VENV_OWNER="$(whoami)"
  SUDO_PREFIX=""
  USER_HOME="$HOME"
fi

# Set dynamic project path
DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$DIR/.venv/bin/python"

echo "Creating venv..."
${SUDO_PREFIX} python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Upgrading pip in venv..."
python -m pip install --upgrade pip setuptools wheel

echo "Updating system and installing system packages (requires sudo)"
sudo apt update && sudo apt full-upgrade -y
# Added 'dex' to the list of packages to handle desktop launches
sudo apt install -y dex python3-tk xdg-utils mousepad thonny xclip xsel build-essential libssl-dev libffi-dev || true

echo "Installing python packages into venv..."
pip install -r requirements.txt

echo "Creating plugin directory..."
mkdir -p "$DIR/.controlpanel_plugins"

echo "Configuring secure passwordless execution for app buttons..."
# This grants your script's specific Python environment passwordless root access
sudo mkdir -p /etc/sudoers.d
echo "pi ALL=(ALL) NOPASSWD: $VENV_PYTHON" | sudo tee /etc/sudoers.d/firecenter-control
sudo chmod 0440 /etc/sudoers.d/firecenter-control

echo "Creating Desktop Shortcut..."
mkdir -p "$USER_HOME/Desktop"
cat <<EOF > "$USER_HOME/Desktop/FireCenter.desktop"
[Desktop Entry]
Name=FireCenter
Comment=Run FireCenter as Root
Exec=sudo $VENV_PYTHON $DIR/main.py
Terminal=false
Type=Application
Categories=Utility;
EOF

# Ensure file belongs to the user and is executable
chown "$VENV_OWNER:$VENV_OWNER" "$USER_HOME/Desktop/FireCenter.desktop"
chmod +x "$USER_HOME/Desktop/FireCenter.desktop"

echo "======================================"
echo "Install complete!"
echo "======================================"
echo "You can now launch FireCenter directly from your desktop."

rm -- "$0" || true
