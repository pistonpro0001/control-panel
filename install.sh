#!/bin/bash
set -euo pipefail

echo "======================================"
echo " Installing FireCenter"
echo "======================================"

# Determine the non-root user running the script
if [ "${SUDO_USER:-}" ]; then
  VENV_OWNER="$SUDO_USER"
  USER_HOME=$(eval echo "~$SUDO_USER")
else
  VENV_OWNER="$(whoami)"
  USER_HOME="$HOME"
fi

# Set project path
DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$DIR/.venv/bin/python"

# 1. Update system and install system packages first (Requires Root)
echo "Updating system and installing system packages..."
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y dex python3-tk xdg-utils mousepad thonny xclip xsel build-essential libssl-dev libffi-dev ffmpeg || true

# 2. Create and configure virtual environment as the standard user (No Sudo)
echo "Creating venv..."
sudo -u "$VENV_OWNER" python3 -m venv "$DIR/.venv"

# 3. Use the venv's direct python path to install packages
echo "Upgrading pip in venv..."
sudo -u "$VENV_OWNER" "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel

echo "Installing python packages into venv..."
sudo -u "$VENV_OWNER" "$VENV_PYTHON" -m pip install -r "$DIR/requirements.txt"

echo "Creating plugin directory..."
sudo -u "$VENV_OWNER" mkdir -p "$DIR/.controlpanel_plugins"

# 4. Configure secure passwordless execution for app buttons (Dynamic User)
echo "Configuring secure passwordless execution for app buttons..."
sudo mkdir -p /etc/sudoers.d
echo "$VENV_OWNER ALL=(ALL) NOPASSWD: $VENV_PYTHON" | sudo tee /etc/sudoers.d/firecenter-control
sudo chmod 0440 /etc/sudoers.d/firecenter-control

# 5. Creating Desktop Shortcut
echo "Creating Desktop Shortcut..."
sudo -u "$VENV_OWNER" mkdir -p "$USER_HOME/Desktop"

cat <<EOF | sudo tee "$USER_HOME/Desktop/FireCenter.desktop" > /dev/null
[Desktop Entry]
Name=FireCenter
Comment=Run FireCenter as Root
Exec=sudo $VENV_PYTHON $DIR/main.py
Terminal=false
Type=Application
Categories=Utility;
EOF

sudo chown "$VENV_OWNER:$VENV_OWNER" "$USER_HOME/Desktop/FireCenter.desktop"
sudo chmod +x "$USER_HOME/Desktop/FireCenter.desktop"

echo "======================================"
echo "Install complete!"
echo "======================================"
echo "You can now launch FireCenter directly from your desktop."

# Clean up the script itself
rm -- "$0" || true
