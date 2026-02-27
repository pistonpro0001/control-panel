# Control Panel

This is the code to have full control of your system, in a sleek and stylish manner! Made entirely in Python 3.

## Supported Systems
v1 is very limited so far, so here are the requirements:

### OS
Any version of Raspberry Pi OS (32 or 64 bit)\
Debian/Ubuntu (64 bit recommended)

### Architecture
ARM (32 bit or 64 bit)\
x86_64 (64 bit)

### Other Requirements
X11 or XWayland\
Python 3.9 or newer\
A standard Linux desktop environment (XFCE, LXDE, MATE, GNOME, KDE, etc.)

## Setup
First, you're going to have to install [Python 3.9](https://www.reddit.com/r/learnpython/comments/n97okh/how_do_i_install_python_391_on_ubuntu_2004/).\
Next, head to your terminal to install the dependecies.

### Installation
All of the python modules you need can be installed with one command:\
`pip install requests urllib3 feedparser beautifulsoup4 Pillow ftfy psutil mutagen pyperclip`\
This installs all of the python requirements that allows it to function.

Next, you need to install a certain text editor and python editor (used by the Files tab)

Upgrade: `sudo apt update && sudo apt upgrade`\
Install: `sudo apt install mousepad thonny python3-tk`

(Note: `/bin/bash` and `xdg-open` must be available (both included by default on Debian/Ubuntu/Raspberry Pi OS))

### Code Setup

To download the code, click on the Code dropdown and then click Download Zip.\
Extract the files anywhere you want.

Some systems (Debian/Ubuntu/Raspberry Pi OS with a non‑`pi` user) require updating the hardcoded paths.

Open `menu.py` in any text editor, and look and the global variables:\
`
THEME_FILE
PLUGIN_DIR
RSS_FEED
SEARCH_HISTORY_FILE
FAVORITES_FILE
`

Change `/home/pi/` to your actual home directory, for example:\
`/home/yourusername/`\
Save and exit.

Now, go to the location you set for `THEME_FILE` and create a file named exactly:\
`.controlpanel_theme`

Open it in a text editor, and put either `light` or `dark`.

Save and close it.
## Final Notes
With the setup complete, the Control Panel is ready to become _your_ system dashboard. Everything—from themes to plugins to file handling—is designed to be edited, extended, and experimented with.
v1 is just the foundation. More features, polish, and customization options will come as the project grows. If you build something cool or find a way to improve the experience, contributions are always welcome.

Although this is just v1, I have actually been working on this project for about 6 months now. There is just a lot to explore, so I hope you have fun with it!
