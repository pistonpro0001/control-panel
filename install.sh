#!/bin/bash

echo "======================================"
echo " Installing Command Center (Clean Build)"
echo "======================================"

# Update system
sudo apt update

echo "---- Installing system packages ----"
sudo apt install -y \
    python3 \
    python3-pip \
    python3-tk \
    xdg-utils \
    mousepad \
    thonny

echo "---- Installing Python packages ----"
pip3 install --upgrade pip

pip3 install \
    pillow \
    psutil \
    pyperclip

echo "---- Optional clipboard support ----"
sudo apt install -y xclip xsel 2>/dev/null

echo "---- Creating plugin directory ----"
mkdir -p ~/.controlpanel_plugins

echo "======================================"
echo " Installation Complete!"
echo "======================================"
echo "Run your app with:"
echo "python3 menu.py"
