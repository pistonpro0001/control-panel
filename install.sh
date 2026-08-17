#!/bin/bash

echo "======================================"
echo " Installing FireCenter"
echo "======================================"

sudo apt update && sudo apt full-upgrade -y

echo "---- installing system packages ----"
sudo apt install -y \
    python3 \
    python3-pip \
    python3-tk \
    xdg-utils \
    mousepad \
    thonny

echo "---- installing python packages ----"
pip3 install --upgrade pip

pip3 install \
    pillow \
    psutil \
    pyperclip

echo "----instaling clipboard support ----"
sudo apt install -y xclip xsel 2>/dev/null

echo "---- creating plugin directory ----"
mkdir -p "$(dirname "$0")/.controlpanel_plugins"

echo "======================================"
echo "Install complete!"
echo "======================================"
echo "Run it (in this directory) with:"
echo "python3 menu.py"
