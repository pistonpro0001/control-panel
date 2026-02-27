#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import subprocess
import os
import threading
import time
from datetime import datetime
import json
from PIL import Image, ImageTk
import shutil
import psutil
from mutagen import File
import io
from news import show_news
from weather import get_weather
from get_email import fetch_latest_emails as get_emails
import pyperclip

THEME_FILE = "/home/pi/.controlpanel_theme" #this one
CURRENT_BG = "#FFFFFF"
PLUGIN_DIR = "/home/pi/.controlpanel_plugins" 
RSS_FEED = "/home/pi/.controlpanel_rssfeed"
SEARCH_HISTORY_FILE = "/home/pi/.controlpanel_search_history"
FAVORITES_FILE = "/home/pi/.controlpanel_favorites.json"
os.makedirs(PLUGIN_DIR, exist_ok=True)

# -------------------------------
#  Toggle Switch Widget
# -------------------------------
class ToggleSwitch(tk.Canvas):
    def __init__(self, parent, width=60, height=30, bg_on="#4CAF50", bg_off="#888888",
                 circle_color="#FFFFFF", command=None, initial=False):
        global CURRENT_BG

        super().__init__(parent, width=width, height=height, highlightthickness=0,
                         bg=CURRENT_BG)

        self.width = width
        self.height = height
        self.bg_on = bg_on
        self.bg_off = bg_off
        self.circle_color = circle_color
        self.command = command
        self.state = initial

        self.radius = height // 2
        self.circle_pos = self.radius if not initial else width - self.radius

        self.bg_rect = self.create_rounded_rect(
            0, 0, width, height, radius=self.radius,
            fill=self.bg_on if initial else self.bg_off
        )

        self.circle = self.create_oval(
            self.circle_pos - self.radius, 0,
            self.circle_pos + self.radius, height,
            fill=self.circle_color, outline=""
        )

        self.bind("<Button-1>", self.toggle)

    def create_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def toggle(self, event=None):
        self.state = not self.state
        self.animate()
        if self.command:
            self.command(self.state)

    def animate(self):
        target = self.width - self.radius if self.state else self.radius
        step = 2 if self.state else -2

        def slide():
            pos = self.coords(self.circle)
            cx = (pos[0] + pos[2]) / 2

            if (step > 0 and cx < target) or (step < 0 and cx > target):
                self.move(self.circle, step, 0)
                self.after(5, slide)
            else:
                dx = target - cx
                self.move(self.circle, dx, 0)

            self.itemconfig(self.bg_rect, fill=self.bg_on if self.state else self.bg_off)

        slide()

class PanelContext:
    def __init__(self, root, notebook, tabs):
        self.root = root
        self.notebook = notebook
        self.tabs = tabs

# -------------------------------
#  Theme Handling
# -------------------------------
def load_theme():
    with open(THEME_FILE, "r") as f:
        return f.read().strip()

def save_theme(theme):
    with open(THEME_FILE, "w") as f:
        f.write(theme)

def apply_theme():
    global CURRENT_BG
    theme = load_theme()

    if theme == "dark":
        CURRENT_BG = "#222222"
        fg = "#FFFFFF"
        hover_bg = "#444444"
        hover_fg = "#FFFFFF"
    else:
        CURRENT_BG = "#FFFFFF"
        fg = "#000000"
        hover_bg = "#DDDDDD"
        hover_fg = "#000000"

    root.configure(bg=CURRENT_BG)

    style.configure("TButton",
                    background=CURRENT_BG,
                    foreground=fg,
                    borderwidth=0)
    style.map("TButton",
              background=[("active", hover_bg)],
              foreground=[("active", hover_fg)])

    style.configure("CustomNotebook.TNotebook",
                    background=CURRENT_BG,
                    borderwidth=0)
    style.configure("CustomNotebook.TNotebook.Tab",
                    background=CURRENT_BG,
                    foreground=fg)
    style.map("CustomNotebook.TNotebook.Tab",
              background=[("selected", CURRENT_BG)],
              foreground=[("selected", fg)])

    style.configure("TLabel",
                    background=CURRENT_BG,
                    foreground=fg)


# -------------------------------
#  Popups + Command Execution
# -------------------------------
def truncate_output(text, max_lines=15, max_chars=500):
    if not text:
        return ""

    lines = text.splitlines()
    truncated = False

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        truncated = True

    joined = "\n".join(lines)
    if len(joined) > max_chars:
        joined = joined[:max_chars]
        truncated = True

    if truncated:
        joined = joined.rstrip() + "\n...\n(output truncated)"
    return joined

def show_popup(title, message):
    popup = tk.Toplevel(root)
    popup.title(title)
    popup.transient(root)
    popup.resizable(False, False)
    popup.geometry("+%d+%d" % (root.winfo_rootx() + 60,
                               root.winfo_rooty() + 60))
    popup.configure(bg=CURRENT_BG)

    frame = tk.Frame(popup, bg=CURRENT_BG, padx=15, pady=15)
    frame.pack(fill="both", expand=True)

    fg = "#FFFFFF" if CURRENT_BG != "#FFFFFF" else "#000000"
    label = tk.Label(frame, text=message, bg=CURRENT_BG,
                     fg=fg, justify="left")
    label.pack(pady=(0, 10))

    if title in [it["name"] for it in items]:
        def run_again():
            for it in items:
                if it["name"] == title:
                    if it["type"] == "script":
                        run_script_with_popup(it["name"], it["path"])
                    else:
                        run_inline_with_popup(it["name"], it["command"], it["kind"])
                    
        ttk.Button(frame, text="Run Again", command=run_again).pack(pady=(0, 10))
    
    ttk.Button(frame, text="OK", command=popup.destroy).pack()

def run_inline_with_popup(name, command, kind="info"):
    try:
        if kind == "info":
            result = subprocess.run( 
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            output = result.stdout.strip() or result.stderr.strip()
            if not output:
                output = "(no output)"
            output = truncate_output(output)
            show_popup(name, output)
        else:
            subprocess.Popen(command, shell=True)
            show_popup(name, "Command executed.")
    except Exception as e:
        show_popup(f"{name} - Error", str(e))

def run_script_with_popup(name, path):
    try:
        subprocess.Popen(["/bin/bash", path])
        show_popup(name, "Script started.")
    except Exception as e:
        show_popup(f"{name} - Error", str(e))


# -------------------------------
#  GUI Setup
# -------------------------------
root = tk.Tk()
root.title("Command Center")
root.geometry("1050x540")   # <--- widened window
root.resizable(False, False)
root.attributes('-topmost', True)

ICON_PATH = "/home/pi/Pictures/"
ICON_SIZE = (24, 24)
    
def load_icon(name):
    img = Image.open(ICON_PATH + name).resize(ICON_SIZE, Image.LANCZOS)
    return ImageTk.PhotoImage(img)

icons = { "folder": load_icon("folder.png"), "file": load_icon("file.png"), "script": load_icon("script.png"), "image": load_icon("image.png"), "exec": load_icon("exec.png"), }

style = ttk.Style()

if not os.path.exists(THEME_FILE):
    with open(THEME_FILE, "w") as f:
        f.write("light")

apply_theme()

notebook = ttk.Notebook(root, style="CustomNotebook.TNotebook")
notebook.pack(fill="both", expand=True)

tab_names = ["Dashboard", "System", "Bullitin", "Developer", "Plugins", "Tasks",
             "Network", "Maintenance", "Visual", "Music", "Files", "Favorites",
             "Scheduler", "Clipboard", "Search", "Settings"]

dash_interval = tk.IntVar(value=5)

tabs = {}
for name in tab_names:
    frame = tk.Frame(notebook, bg=CURRENT_BG)
    notebook.add(frame, text=name)
    tabs[name] = frame
    
def add_section(parent, title):
    fg = "#FFFFFF" if CURRENT_BG != "#FFFFFF" else "#000000"

    frame = tk.Frame(parent, bg=CURRENT_BG)
    frame.pack(fill="x", pady=(15, 5))

    label = tk.Label(
        frame,
        text=title,
        bg=CURRENT_BG,
        fg=fg,
        font=("TkDefaultFont", 12, "bold")
    )
    label.pack(anchor="w", padx=10)

    # Separator line
    sep = tk.Frame(parent, bg=fg, height=1)
    sep.pack(fill="x", padx=10, pady=(0, 10))
    
def build_tasks_panel():
    global task_list_frame

    # Destroy anything that might already be in the Tasks tab
    for child in tabs["Tasks"].winfo_children():
        child.destroy()

    # Now create a clean container
    task_list_frame = tk.Frame(tabs["Tasks"], bg=CURRENT_BG)
    task_list_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
build_tasks_panel()
    
panel = PanelContext(root, notebook, tabs)
    
# Ctrl+S → jump to Search tab
root.bind("<Control-s>", lambda e: notebook.select(tabs["Search"]))

# Ctrl+T → toggle theme
root.bind("<Control-t>", lambda e: theme_toggle.toggle())

# Ctrl+F → open plugin folder in Files tab
root.bind("<Control-f>", lambda e: (
    notebook.select(tabs["Files"]),
    path_var.set(PLUGIN_DIR),
    refresh_files()
))
    
def on_tab_change(event):
    tab = event.widget.tab(event.widget.index("current"))["text"]
    if tab == "Search":
        do_search()

notebook.bind("<<NotebookTabChanged>>", on_tab_change)

def refresh_tab_backgrounds():
    for frame in tabs.values():
        frame.configure(bg=CURRENT_BG)
        
        
tasks_tab = tabs["Tasks"]

def refresh_tasks_panel():
    for child in task_list_frame.winfo_children():
        child.destroy()
        
    fg = "#FFFFFF" if CURRENT_BG != "#FFFFFF" else "#000000"

    header = tk.Label(task_list_frame, text="PID    CPU%    MEM%    NAME",
                      bg=CURRENT_BG, fg=fg, font=("TkDefaultFont", 10, "bold"))
    header.pack(anchor="w", pady=(0, 5))

    # --- Collect processes first ---
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            processes.append(proc.info)
        except Exception:
            continue

    # --- Sort by CPU descending ---
    processes.sort(key=lambda p: p['cpu_percent'], reverse=True)

    # --- Render rows ---
    for info in processes:
        pid = info['pid']
        name = info['name']
        cpu = info['cpu_percent']
        mem = info['memory_percent']

        row = tk.Frame(task_list_frame, bg=CURRENT_BG)
        row.pack(fill="x", pady=1)

        label = tk.Label(row,
                         text=f"{pid:<6} {cpu:>5.1f}%   {mem:>5.1f}%   {name}",
                         bg=CURRENT_BG, fg=fg, anchor="w")
        label.pack(side="left", fill="x", expand=True)

        def kill_process(p=pid):
            try:
                psutil.Process(p).kill()
                refresh_tasks_panel()
            except Exception as e:
                show_popup("Error", str(e))

        ttk.Button(row, text="Kill", command=kill_process).pack(side="right")

    tasks_tab.after(dash_interval.get() * 1000, refresh_tasks_panel)

build_tasks_panel()
refresh_tasks_panel()

settings = tabs["Settings"]

add_section(settings, "Configure Settings")

ttk.Label(settings, text="Appearance").pack(pady=(10, 0))

theme_toggle = ToggleSwitch(
    settings,
    width=35,
    height=17.5,
    bg_on="#00AB41",
    bg_off="#424040",
    circle_color="#FFFFFF",
    initial=(load_theme() == "dark"),
    command=lambda s: (save_theme("dark" if s else "light"), apply_theme(), refresh_tab_backgrounds())
)

theme_toggle.pack(pady=10)

ttk.Label(settings, text="Fuzzy Search").pack(pady=(10, 0))

FUZZY_ENABLED = True

def toggle_fuzzy(state):
    global FUZZY_ENABLED
    FUZZY_ENABLED = state

fuzzy_toggle = ToggleSwitch(
    settings,
    width=35,
    height=17.5,
    bg_on="#FFA500",
    bg_off="#555555",
    circle_color="#FFFFFF",
    initial=FUZZY_ENABLED,
    command=toggle_fuzzy
)
fuzzy_toggle.pack(pady=10)

ttk.Label(settings, text="Standard Refresh Rate (seconds)").pack(pady=(20, 0))
ttk.Spinbox(settings, from_=1, to=60, textvariable=dash_interval).pack()

def save_feed_url(*args):
    with open(RSS_FEED, "w") as f:
        f.write(feed_url.get())
        
feed_url = tk.StringVar()
fe = "http://planetpython.org/rss20.xml"
try:
    with open(RSS_FEED, "r") as f:
        fe = f.readlines()[0].strip()
except:
    with open(RSS_FEED, "w") as f:
        f.write(fe)
    
feed_url.set(fe)
feed_url.trace_add("write", save_feed_url)
ttk.Label(settings, text="News Feed RSS").pack(pady=(20, 0))
ttk.Entry(settings, textvariable=feed_url).pack()

def run_async(func, *args, **kwargs):
    threading.Thread(target=lambda: func(*args, **kwargs), daemon=True).start()
    
    
plugins_tab = tabs["Plugins"]

def refresh_plugins():
    global items, PLUGINS_READY
    
    if not PLUGINS_READY:
        return

    # Remove plugin items
    items = [it for it in items if not it.get("plugin", False)]

    # Clear widget registry
    PLUGIN_API["add_widget"] = []

    # Remove ONLY plugin widgets
    for tab_name in tabs:
        for child in tabs[tab_name].winfo_children():
            if getattr(child, "plugin_owned", False):
                child.destroy()

    # Reload plugin files
    load_plugins()

    # Rebuild plugin buttons
    for it in items:
        if it.get("plugin", False):
            if it["type"] == "script":
                add_button_to_tab(
                    it["tab"],
                    it["name"],
                    lambda it=it: run_script_with_popup(it["name"], it["path"])
                )
            else:
                add_button_to_tab(
                    it["tab"],
                    it["name"],
                    lambda it=it: run_inline_with_popup(it["name"], it["command"], it["kind"])
                )

    # Inject plugin widgets again
    inject_plugin_widgets()

    show_popup("Plugins Reloaded", "All plugins have been refreshed.")
    
    
def create_new_item(base_path, is_folder, callback=None):
    popup = tk.Toplevel(root)
    popup.title("Create")
    popup.configure(bg=CURRENT_BG)
    popup.resizable(False, False)

    fg = "#FFFFFF" if CURRENT_BG != "#FFFFFF" else "#000000"

    tk.Label(popup, text="Name:", bg=CURRENT_BG, fg=fg).pack(padx=10, pady=10)
    name_var = tk.StringVar()
    entry = ttk.Entry(popup, textvariable=name_var)
    entry.pack(padx=10, pady=5)

    def do_create():
        new_path = os.path.join(base_path, name_var.get())
        try:
            if is_folder:
                os.makedirs(new_path)
            else:
                open(new_path, "w").close()
            popup.destroy()
            refresh_files()
            if callback:
                callback(new_path)
        except Exception as e:
            show_popup("Create Error", str(e))

    ttk.Button(popup, text="OK", command=do_create).pack(pady=10)
    
def new_plugin():
    def write_template(filepath):
        template = """#Tutorial:
#Import ttk
from tkinter import ttk

#Just in case you want to change with the theme:
THEME_FILE = "/home/pi/.controlpanel_theme"
bg = None
def load_theme():
    global bg
    with open(THEME_FILE, "r") as f:
        if f.read().strip() == "dark":
            bg = "#222222"
        else:
            bg = "#FFFFFF"

#Main code:
def register(api):
    def draw_widget(parent):
        #Using parent as the root, design whatever widget you want
        #Example code:
        
        #Make a new style using current theme
        s = ttk.Style()
        load_theme()
        s.configure('Widget.TFrame', background=bg)

        #Make the frame using the style
        frame = ttk.Frame(parent, style='Widget.TFrame')
        frame.pack(fill="x", padx=20, pady=10) 
        
        #Add labels
        ttk.Label(frame, text="Example Widget", font=("TkDefaultFont", 12, "bold"), style='RamUsage.TLabel').pack(anchor="w")
        value_label = ttk.Label(frame, text="Loading...", style='Widget.TLabel')
        value_label.pack(anchor="w")

        #Keep this in your code, put main loop in it or leave it empty 
        #Keep .after()
        def update():
            #Do whatever you want
            from time import time
            
            value_label.config(text=str(time()))

            #Update widget
            frame.after(1000, update)
        
        #This code needs to be kept as well
        update()
        return frame
    
    #Add widget to whatever tab you want, replace 'System'
    api["add_widget"].append(("System", draw_widget))"""
        with open(filepath, "w") as f:
            f.write(template)
        
        refresh_plugins()
        
    create_new_item("/home/pi/.controlpanel_plugins", False, callback=write_template)
    
def refresh_plugins_panel():
    for child in plugins_tab.winfo_children():
        child.destroy()

    add_section(plugins_tab, "Plugin Tools")

    fg = "#FFFFFF" if CURRENT_BG != "#FFFFFF" else "#000000"

    ttk.Label(plugins_tab, text="Installed Plugins").pack(pady=10)

    for fname in os.listdir(PLUGIN_DIR):
        if not fname.endswith(".py"):
            continue

        row = tk.Frame(plugins_tab, bg=CURRENT_BG)
        row.pack(fill="x", padx=20, pady=5)

        tk.Label(row, text=fname, bg=CURRENT_BG, fg=fg).pack(side="left")

        ttk.Button(
            row,
            text="Open",
            command=lambda f=fname: (
                path_var.set(PLUGIN_DIR),
                refresh_files(),
                notebook.select(tabs["Files"])
            )
        ).pack(side="right")

    ttk.Button(
        plugins_tab,
        text="Reload Plugins",
        command=lambda: (refresh_plugins(), refresh_plugins_panel())
    ).pack(pady=20)
    
    ttk.Button(
        plugins_tab,
        text="New Plugin",
        command=lambda: (new_plugin())
    ).pack(pady=20)

refresh_plugins_panel()

file_frame = tk.Frame(tabs["Files"], bg=CURRENT_BG)
file_frame.pack(fill="both", expand=True)

left_frame = tk.Frame(file_frame, bg=CURRENT_BG)
left_frame.pack(side="left", fill="both", expand=True)

path_var = tk.StringVar(value=os.path.expanduser("~"))

show_hidden = tk.BooleanVar(value=False)

preview_frame = tk.Frame(file_frame, bg=CURRENT_BG)
preview_frame.pack(side="right", fill="both")

def clear_preview():
    global preview_frame
    if preview_frame is not None:
        preview_frame.destroy()
        preview_frame = None

def show_preview(path):
    global preview_frame
    # Clear old preview
    clear_preview()
    
    preview_frame = tk.Frame(file_frame, bg=CURRENT_BG)
    preview_frame.pack(side="right", fill="both")

    fg = "#FFFFFF" if CURRENT_BG != "#FFFFFF" else "#000000"

    # --- Close button (top-right) ---
    close_btn = tk.Button(
        preview_frame,
        text="✕",
        bg=CURRENT_BG,
        fg=fg,
        bd=0,
        highlightthickness=0,
        font=("TkDefaultFont", 12, "bold"),
        command=lambda: clear_preview()
    )
    close_btn.pack(anchor="ne", padx=5, pady=5)

    # --- Determine file type ---
    ext = os.path.splitext(path)[1].lower()

    # --- Image preview ---
    if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
        try:
            img = Image.open(path)
            img.thumbnail((280, 280))
            tkimg = ImageTk.PhotoImage(img)

            lbl = tk.Label(preview_frame, image=tkimg, bg=CURRENT_BG)
            lbl.image = tkimg
            lbl.pack(pady=10)
            return
        except:
            pass

    # --- Text preview ---
    if ext in [".txt", ".md", ".json", ".py", ".sh", ".log", ".cfg", ".ini"]:
        try:
            with open(path, "r") as f:
                text = f.read(2000)  # first 2k chars

            # Pretty JSON
            if ext == ".json":
                try:
                    import json
                    obj = json.loads(text)
                    text = json.dumps(obj, indent=2)
                except:
                    pass

            txt = tk.Text(preview_frame, bg=CURRENT_BG, fg=fg, wrap="word")
            txt.insert("1.0", text)
            txt.configure(state="disabled")
            txt.pack(fill="both", expand=True, padx=10, pady=10)
            return
        except:
            pass

    # --- Fallback ---
    tk.Label(preview_frame, text="No preview available",
             bg=CURRENT_BG, fg=fg).pack(pady=20)

def rename_file(old_path):
    popup = tk.Toplevel(root)
    popup.title("Rename")
    popup.configure(bg=CURRENT_BG)
    popup.resizable(False, False)

    fg = "#FFFFFF" if CURRENT_BG != "#FFFFFF" else "#000000"

    tk.Label(popup, text="New name:", bg=CURRENT_BG, fg=fg).pack(padx=10, pady=10)
    new_name_var = tk.StringVar(value=os.path.basename(old_path))
    entry = ttk.Entry(popup, textvariable=new_name_var)
    entry.pack(padx=10, pady=5)

    def do_rename():
        new_path = os.path.join(os.path.dirname(old_path), new_name_var.get())
        try:
            os.rename(old_path, new_path)
            popup.destroy()
            refresh_files()
        except Exception as e:
            show_popup("Rename Error", str(e))

    ttk.Button(popup, text="OK", command=do_rename).pack(pady=10)

file_context_menu = None
context_target_path = None

def open_file(p):
    ext = os.path.splitext(p)[1].lower()

    # Python files → Thonny
    if ext == ".py":
        subprocess.Popen(["thonny", p])
        return

    # Text-based files → Mousepad
    text_exts = [
                ".txt", ".md", ".json", ".csv", ".ini", ".cfg",
                ".log", ".yaml", ".yml", ".xml", ".html", ".css",
                ".js", ".c", ".cpp", ".h", ".sh"
    ]
    if ext in text_exts:
        subprocess.Popen(["mousepad", p])
        return

            # Desktop launchers → open normally
    if ext == ".desktop":
        subprocess.Popen(["xdg-open", p])
        return

    # Everything else → default handler
    subprocess.Popen(["xdg-open", p])

FILE_CLIPBOARD = {"mode": None, "path": None}

def copy_file(path):
    global FILE_CLIPBOARD
    FILE_CLIPBOARD["mode"] = "copy"
    FILE_CLIPBOARD["path"] = path

def cut_file(path):
    global FILE_CLIPBOARD
    FILE_CLIPBOARD["mode"] = "cut"
    FILE_CLIPBOARD["path"] = path

def delete_file(path):
    os.remove(path)
    refresh_files()

def paste_file():
    if not FILE_CLIPBOARD["path"]:
        return

    src = FILE_CLIPBOARD["path"]
    dst = os.path.join(path_var.get(), os.path.basename(src))

    if FILE_CLIPBOARD["mode"] == "copy":
        shutil.copy2(src, dst)
    else:
        shutil.move(src, dst)

    FILE_CLIPBOARD["mode"] = None
    FILE_CLIPBOARD["path"] = None
    refresh_files()

def show_file_menu(event, path, is_exec):
    menu = tk.Menu(root, tearoff=0,
                   bg=CURRENT_BG,
                   fg="#FFFFFF" if CURRENT_BG != "#FFFFFF" else "#000000")

    # Always available
    menu.add_command(label="Open", command=lambda: open_file(path))

    # Only show Run if executable/script
    if is_exec:
        menu.add_command(label="Run", command=lambda: run_file(path))

    menu.add_separator()
    menu.add_command(label="Rename", command=lambda: rename_file(path))
    menu.add_command(label="Delete", command=lambda: delete_file(path))
    menu.add_command(label="Copy", command=lambda: copy_file(path))
    menu.add_command(label="Cut", command=lambda: cut_file(path))
    menu.add_command(label="Paste", command=paste_file)

    # Show menu at cursor
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()

# --- Fuzzy matching ---
def fuzzy_score(query, text):
    query = query.lower()
    text = text.lower()
    score = 0
    qi = 0

    for char in text:
        if qi < len(query) and char == query[qi]:
            score += 2
            qi += 1
        elif char in query:
            score += 1

    return score if qi == len(query) else 0

def fuzzy_match(query, choices):
    scored = []
    for c in choices:
        s = fuzzy_score(query, c)
        if s > 0:
            scored.append((s, c))

    # Sort by score descending
    scored.sort(reverse=True, key=lambda x: x[0])

    # Return only the text values
    return [c for _, c in scored]

# --- Image files ---
IMAGE_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp", ".svg"
}

# --- Script / code files ---
SCRIPT_EXTS = {
    ".py", ".sh", ".html", ".htm", ".css", ".js",
    ".c", ".cpp", ".h", ".hpp", ".java", ".php",
    ".rb", ".lua", ".go", ".rs", ".swift", ".ts"
}

# --- Text-like files (fallback to file icon) ---
TEXT_EXTS = {
    ".txt", ".md", ".json", ".csv", ".ini", ".cfg", ".log",
    ".yaml", ".yml", ".xml", ".toml", ".rst"
}


def refresh_files(search_query=None):
    for child in left_frame.winfo_children():
        child.destroy()

    fg = "#FFFFFF" if CURRENT_BG != "#FFFFFF" else "#000000"

    # Path entry
    entry = ttk.Entry(left_frame, textvariable=path_var)
    entry.pack(fill="x", padx=10, pady=10)

    def go():
        refresh_files()
        
    style.configure("My.TButton", 
                foreground=fg, 
                background=CURRENT_BG, 
                font=("Helvetica", 12))
    
    ttk.Button(left_frame, text="Go", command=go).pack(pady=(0, 10))
    ttk.Button(left_frame, text="New File",
           command=lambda: create_new_item(path_var.get(), False)).pack(pady=2)
    
    # --- Search Bar ---
    search_var = tk.StringVar()
    
    search_entry = ttk.Entry(left_frame, textvariable=search_var)
    search_entry.pack(fill="x", padx=10, pady=(0, 10))
    
    def do_search(event=None):
        refresh_files(search_query=search_var.get().strip())
        
    def clear_search(event=None):
        refresh_files()
        
    search_entry.bind("<Return>", do_search)
    search_entry.bind("<Escape>", do_search)
    
    ttk.Button(left_frame, text="New Folder",
               command=lambda: create_new_item(path_var.get(), True)).pack(pady=2)
    
    show_hidden_check = ttk.Checkbutton(left_frame, text="Show hidden files", style="My.TButton", variable=show_hidden, command=lambda search_query=search_query: refresh_files(search_query))
    show_hidden_check.pack(pady=(0, 10))
    
    # File list
    try:
        if search_query == "../":
            path_var.set(os.path.abspath(path_var.get() + "/../"))
            refresh_files()
            return
        files = os.listdir(path_var.get())
        
        # Filter hidden files unless toggle is on
        if not show_hidden.get():
            files = [f for f in files if not f.startswith(".")]
            
        if search_query:
            files = fuzzy_match(search_query.lower(), files)

    except:
        tk.Label(left_frame, text="Invalid path", bg=CURRENT_BG, fg=fg).pack()
        return

    for f in files:
        full = os.path.join(path_var.get(), f)
        frame = tk.Frame(left_frame, bg=CURRENT_BG)
        frame.pack(fill="x", padx=20, pady=2)

        # Choose icon based on file type
        if os.path.isdir(full):
            icon = icons["folder"]
        else:
            ext = os.path.splitext(full)[1].lower()

            if ext in TEXT_EXTS:
                icon = icons["file"]
            elif ext in SCRIPT_EXTS:
                icon = icons["script"]
            elif ext in IMAGE_EXTS:
                icon = icons["image"]
            elif os.access(full, os.X_OK) or ext == ".desktop":
                icon = icons["exec"]
            else:
                icon = icons["file"]

        # Label with icon + filename
        label = tk.Label(frame, text=f"  {f}", image=icon, compound="left",
                         bg=CURRENT_BG, fg=fg)
        label.image = icon  # prevent garbage collection
        label.pack(side="left")
        
        label.bind("<Button-1>", lambda e, p=full: show_preview(p))


        # -----------------------------
        # DIRECTORY HANDLING
        # -----------------------------
        if os.path.isdir(full):
            ttk.Button(
                frame,
                text="Open",
                command=lambda p=full: path_var.set(p) or refresh_files()
            ).pack(side="right")
            continue

        # -----------------------------
        # FILE HANDLING
        # -----------------------------
        def open_file(p):
            ext = os.path.splitext(p)[1].lower()

            # Python files → Thonny
            if ext == ".py":
                subprocess.Popen(["thonny", p])
                return

            # Text-based files → Mousepad
            text_exts = [
                ".txt", ".md", ".json", ".csv", ".ini", ".cfg",
                ".log", ".yaml", ".yml", ".xml", ".html", ".css",
                ".js", ".c", ".cpp", ".h", ".sh"
            ]
            if ext in text_exts:
                subprocess.Popen(["mousepad", p])
                return

            # Desktop launchers → open normally
            if ext == ".desktop":
                subprocess.Popen(["xdg-open", p])
                return

            # Everything else → default handler
            subprocess.Popen(["xdg-open", p])

        def run_file(p):
            ext = os.path.splitext(p)[1].lower()

            # Desktop launchers
            if ext == ".desktop":
                subprocess.Popen(["xdg-open", p])
                return

            # Shell scripts
            if ext == ".sh":
                subprocess.Popen(["/bin/bash", p])
                return

            # Python scripts (run, not open)
            if ext == ".py":
                subprocess.Popen(["python3", p])
                return

            # Executable bit set
            if os.access(p, os.X_OK):
                subprocess.Popen([p])
                return

            # Fallback
            subprocess.Popen(["xdg-open", p])

        # -----------------------------
        # RUN BUTTON (only when valid)
        # -----------------------------
        is_exec = ( os.access(full, os.X_OK) or full.endswith(".sh") or full.endswith(".desktop") or full.endswith(".py") )
        if (is_exec):
            ttk.Button(frame, text="Run", command=lambda p=full: run_file(p)).pack(side="right")

        # -----------------------------
        # OPEN BUTTON (always available)
        # -----------------------------

        ttk.Button(frame, text="Open", command=lambda p=full: open_file(p)).pack(side="right")
        
        label.bind("<Button-3>", lambda e, p=full, ex=is_exec: show_file_menu(e, p, ex))

refresh_files()

dash = tabs["Dashboard"]

def update_dashboard():
    for child in dash.winfo_children():
        child.destroy()
        
    add_section(dash, "Dashboard")

    fg = "#FFFFFF" if CURRENT_BG != "#FFFFFF" else "#000000"

    # CPU Temp
    try:
        raw = subprocess.check_output("vcgencmd measure_temp", shell=True).decode().strip()
        # raw looks like: temp=48.0'C
        celsius = float(raw.split("=")[1].split("'")[0])
        fahrenheit = (celsius * 9/5) + 32
        temp = f"{celsius:.1f}°C / {fahrenheit:.1f}°F"
    except:
        temp = "N/A"


    # Memory
    try:
        mem = subprocess.check_output("free -h", shell=True).decode().splitlines()[1]
    except:
        mem = "N/A"

    # Disk
    try:
        disk = subprocess.check_output("df -h /", shell=True).decode().splitlines()[1]
    except:
        disk = "N/A"

    # IP
    try:
        ip = subprocess.check_output("hostname -I", shell=True).decode().strip()
    except:
        ip = "N/A"

    # --- Styled Dashboard Layout ---
    row = tk.Frame(dash, bg=CURRENT_BG)
    row.pack(pady=10, anchor="w")
    
    # Color-code based on Fahrenheit
    if fahrenheit < 110:
        temp_color = "#4CAF50"   # green
    elif fahrenheit < 140:
        temp_color = "#FFC107"   # yellow
    else:
        temp_color = "#F44336"   # red


    def add_row(label, value, color=None):
        frame = tk.Frame(dash, bg=CURRENT_BG)
        frame.pack(fill="x", padx=20, pady=5)

        tk.Label(frame, text=label, bg=CURRENT_BG, fg=fg,
                 font=("TkDefaultFont", 12, "bold")).pack(side="left")

        tk.Label(frame, text=value, bg=CURRENT_BG, fg=color if color else fg,
                 font=("TkDefaultFont", 12)).pack(side="right")

    add_row("CPU Temp:", temp, temp_color)
    add_row("Memory:", mem)
    add_row("Disk:", disk)
    add_row("IP Address:", ip)

    dash.after(dash_interval.get() * 1000, lambda: run_async(update_dashboard))

update_dashboard()

# -------------------------------
#  Command Definitions
# -------------------------------
items = []
favorites = []

def load_favorites():
    global favorites
    if not os.path.exists(FAVORITES_FILE):
        favorites = []
        return

    try:
        with open(FAVORITES_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                favorites = data
            else:
                favorites = []
    except Exception as e:
        print("Error loading favorites:", e)
        favorites = []

def save_favorites():
    try:
        with open(FAVORITES_FILE, "w") as f:
            json.dump(favorites, f, indent=2)
    except Exception as e:
        print("Error saving favorites:", e)
        
load_favorites()

def add_script_item(tab_name, label, path):
    items.append({
        "name": label,
        "type": "script",
        "tab": tab_name,
        "path": path
    })

def add_inline_item(tab_name, label, command, kind="info"):
    items.append({
        "name": label,
        "type": "inline",
        "tab": tab_name,
        "command": command,
        "kind": kind
    })
    
def add_script_item_plugin(tab_name, label, path):
    items.append({
        "name": label,
        "type": "script",
        "tab": tab_name,
        "path": path,
        "plugin": True
    })

def add_inline_item_plugin(tab_name, label, command, kind="info"):
    items.append({
        "name": label,
        "type": "inline",
        "tab": tab_name,
        "command": command,
        "kind": kind,
        "plugin": True
    })

PLUGIN_API = {
    "add_inline": add_inline_item_plugin,
    "add_script": add_script_item_plugin,
    "add_widget": []   # list of (tab_name, widget_func)
}
 
def load_plugins():
    for fname in os.listdir(PLUGIN_DIR):
        if fname.endswith(".py"):
            path = os.path.join(PLUGIN_DIR, fname)
            module_name = fname[:-3]
            try:
                mod = {}
                exec(open(path).read(), mod)
                if "register" in mod:
                    mod["register"](PLUGIN_API)
            except Exception as e:
                show_popup(
                    f"Plugin Load Error: {module_name}",
                    f"Plugin failed during register:\n{e}"
                )
        
"""
To register, put this in code:
# ~/.controlpanel_plugins/myplugin.py

def register(api):
    do some tk stuff here

    widget = the tk widget to add
    api["add_inline"]("Tab name", widget)
    
Choose add_inline or add_script
"""

def get_storage_usage():
    try:
        result = subprocess.check_output("df -h /", shell=True).decode().splitlines()[1]
        parts = result.split()
        size = parts[1]      # total
        used = parts[2]      # used
        percent = parts[4]   # e.g. "41%"
        return f"{used} used / {size} total ({percent})"
    except Exception as e:
        return f"Error: {e}"

add_section(tabs["Music"], "Music Tools")
add_section(tabs["Scheduler"], "Schedule Events")
add_section(tabs["Search"], "System Search")

# --- System ---
add_section(tabs["System"], "System Commands")
add_script_item("System", "Startup", "/home/pi/Documents/Startup.sh")
add_script_item("System", "Start Background", "/home/pi/Documents/bg.sh")
add_script_item("System", "Stop Background", "/home/pi/Documents/kill_gif_wallpaper.sh")
add_inline_item("System", "Reboot", "sudo reboot", kind="action")
add_inline_item("System", "Shutdown", "sudo shutdown now", kind="action")
add_inline_item("System", "Chromium", "chromium", kind="action")

# --- Developer ---
add_section(tabs["Developer"], "Developer Tools")
add_inline_item("Developer", "Python Version", "python3 --version", kind="info")
add_inline_item("Developer", "Pip Packages", "pip3 list", kind="info")
add_inline_item("Developer", "Disk Usage", "df -h /", kind="info")
add_inline_item("Developer", "Memory Usage", "free -h", kind="info")
add_inline_item("Developer", "CPU Temperature", "vcgencmd measure_temp", kind="info")
add_inline_item("Developer", "ARM Memory", "vcgencmd get_mem arm", kind="info")
add_inline_item("Developer", "GPU Memory", "vcgencmd get_mem gpu", kind="info")
add_inline_item("Developer", "Display Server", "echo $XDG_SESSION_TYPE", kind="info")

# --- Network ---
add_section(tabs["Network"], "Network Tools")
add_inline_item("Network", "Show IP Address", "hostname -I", kind="info")
add_inline_item("Network", "Ping Google", "ping -c 4 google.com", kind="info")
add_inline_item("Network", "Restart Networking", "sudo systemctl restart NetworkManager", kind="action")

# --- Maintenance ---
add_section(tabs["Maintenance"], "Maintenance Tasks")
add_inline_item("Maintenance", "Update System",
                "sudo apt update && sudo apt upgrade -y", kind="action")
add_inline_item("Maintenance", "Clean Packages",
                "sudo apt autoremove -y && sudo apt clean", kind="action")

# --- Visual ---
add_section(tabs["Visual"], "Visual & UI Tools")
add_script_item("Visual", "Start Picom", "/home/pi/Documents/start_picom.sh")
add_script_item("Visual", "Open Pet", "/home/pi/Documents/pet.sh")
add_inline_item("Visual", "Open File Manager", "pcmanfm", kind="action")
add_inline_item("Visual", "Open Terminal", "lxterminal", kind="action")
add_inline_item("Visual", "Restart Panel", "lxpanelctl restart", kind="action")
add_inline_item("Visual", "Restart Openbox", "openbox --restart", kind="action")

# --- Clipboard ---
clipboard_tab = tabs["Clipboard"]

history = []
last = None

def update_clipboard():
    global last, history
    for child in clipboard_tab.winfo_children():
        child.destroy()
        
    try:
        text = pyperclip.paste()
        if text != last and text.strip() != "":
            history.append(text)
            last = text
            
            if len(history) > 15:
                history.pop(0)
                
    except Exception as e:
        print(str(e))
                
    for item in reversed(history):
        btn = ttk.Button(
            clipboard_tab,
            text = item[:97].replace("\n", " ") + "..." if len(item) > 97 else item[:97].replace("\n", " "),
            command = lambda t=item: pyperclip.copy(t)
            )
        btn.pack(fill="x", pady=5)
        
    clipboard_tab.after(1000, update_clipboard)
    
update_clipboard()

# --- Bullitin ---
bullitin = tabs["Bullitin"]

emails = get_emails(count=2)

def update_bullitin():
    for child in bullitin.winfo_children():
        child.destroy()
        
    wth = get_weather()
    
    ttk.Button(bullitin, text="News",
           command=lambda: show_news(feed_url.get())).pack(pady=5)
    
    ttk.Label(bullitin, text="\n").pack(pady=(10, 0))
    ttk.Label(bullitin, text=f"Temperature: {wth['temperature']}").pack(pady=(10, 0))
    ttk.Label(bullitin, text=f"Wind Speed: {wth['wind_speed']}").pack(pady=(10, 0))
    ttk.Label(bullitin, text=f"Wind Direction: {wth['wind_dir']}").pack(pady=(10, 0))
    ttk.Label(bullitin, text=f"Condition: {wth['condition']}").pack(pady=(10, 0))
    ttk.Label(bullitin, text="\n").pack(pady=(10, 0))
    
    for i, (sender, subject) in enumerate(emails, 1):
        ttk.Label(bullitin, text=f"{i}. From: {sender}\n       Subject: {subject}\n").pack(pady=(10, 0))
    
    bullitin.after(5000, update_bullitin)
    
root.after(1000, update_bullitin())

# --- Music ---
add_script_item("Music", "Start Music", "/home/pi/Music/start_music.sh")
music_tab = tabs["Music"]

def set_volume(val):
    with open("/home/pi/.taskbar_volume", "r") as f:
        c = f.readlines()[0].strip()
        control = False if c == "t" else True
        
    if control:
        subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{val}%"])

def next_track():
    subprocess.Popen(["mpc", "next"])

def prev_track():
    subprocess.Popen(["mpc", "prev"])

def pause_play():
    subprocess.Popen(["mpc", "toggle"])
    
def send_music_command(cmd):
    with open("/home/pi/Music/music_cmd", "w") as f:
        f.write(cmd)
        
current_track_var = tk.StringVar(value="Loading...")
    
def update_current_track():
    try:
        with open("/home/pi/Music/current_track.txt", "r") as f:
            name = f.read().strip()
    except:
        name = ""
        
    current_track_var.set(name)

# Label
ttk.Label(music_tab, text="Current Track:").pack(pady=(10, 0))
ttk.Label(music_tab, textvariable=current_track_var,
          font=("TkDefaultFont", 12, "bold")).pack(pady=(0, 10))

# Start updating
update_current_track()

progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(music_tab, variable=progress_var, maximum=1.0)
progress_bar.pack(fill="x", padx=20, pady=10)

time_label = ttk.Label(music_tab, text="0:00 / 0:00")
time_label.pack()

last_progress = 0.0

def update_progress():
    global last_progress
    try:
        with open("/home/pi/Music/current_time.txt") as f:
            both = f.readlines()
            pos = int(both[0].strip()) / 1000
            length = float(both[1])

        target = pos / length if length > 0 else 0
        
        smooth = last_progress + (target - last_progress) * .2
        last_progress = smooth
        
        progress_var.set(smooth)

        # Format time
        elapsed = time.strftime("%M:%S", time.gmtime(pos))
        total = time.strftime("%M:%S", time.gmtime(length))
        time_label.config(text=f"{elapsed} / {total}")
        
        update_current_track()

    except:
        pass

    music_tab.after(300, update_progress)

update_progress()

# Volume slider
vol_label = ttk.Label(music_tab, text="Volume")
vol_label.pack(pady=5)

vol_slider = ttk.Scale(music_tab, from_=0, to=100, orient="horizontal",
                       command=set_volume)
vol_slider.set(70)
vol_slider.pack(fill="x", padx=20)

# Playback controls
btn_frame = tk.Frame(music_tab, bg=CURRENT_BG)
btn_frame.pack(pady=10)

music_tab = tabs["Music"]

ttk.Button(music_tab, text="Pause",
           command=lambda: send_music_command("pause")).pack(pady=5)

ttk.Button(music_tab, text="Resume",
           command=lambda: send_music_command("resume")).pack(pady=5)

ttk.Button(music_tab, text="Next Track",
           command=lambda: send_music_command("next")).pack(pady=5)

ttk.Button(music_tab, text="Stop Music",
           command=lambda: send_music_command("stop")).pack(pady=5)

# ============================
# COMMAND PALETTE DICTIONARY
# ============================

COMMANDS = []

def register_command(name, category, description, action):
    COMMANDS.append({
        "name": name,
        "category": category,
        "description": description,
        "action": action
    })

def register_builtin_commands():
    # Navigation
    for tab_name in tabs:
        register_command(
            name=f"Open {tab_name}",
            category="Navigation",
            description=f"Switch to the {tab_name} tab",
            action=lambda t=tab_name: notebook.select(tabs[t])
        )

    # Settings
    register_command(
        "Toggle Theme",
        "Settings",
        "Switch between light and dark mode",
        lambda: theme_toggle.toggle()
    )

    register_command(
        "Toggle Fuzzy Search",
        "Settings",
        "Enable or disable fuzzy matching",
        lambda: fuzzy_toggle.toggle()
    )

    # System
    register_command(
        "Open Terminal",
        "System",
        "Launch LXTerminal",
        lambda: subprocess.Popen(["lxterminal"])
    )

    register_command(
        "Reboot",
        "System",
        "Restart the Raspberry Pi",
        lambda: subprocess.Popen(["reboot"])
    )

    register_command(
        "Shutdown",
        "System",
        "Power off the Raspberry Pi",
        lambda: subprocess.Popen(["shutdown", "now"])
    )

    # Files
    register_command(
        "Open Home Folder",
        "Files",
        "Jump to your home directory",
        lambda: (path_var.set(os.path.expanduser("~")), refresh_files(), notebook.select(tabs["Files"]))
    )

    register_command(
        "Open Plugin Folder",
        "Files",
        "Jump to the plugin directory",
        lambda: (path_var.set(PLUGIN_DIR), refresh_files(), notebook.select(tabs["Files"]))
    )

    # Developer
    register_command(
        "Reload Plugins",
        "Developer",
        "Reload all plugins and refresh UI",
        lambda: refresh_plugins()
    )

register_builtin_commands()

# ============================
# COMMAND PALETTE POPUP
# ============================

def open_command_palette():
    palette = tk.Toplevel(root)
    palette.title("Command Palette")
    palette.geometry("600x400")
    palette.configure(bg=CURRENT_BG)
    palette.transient(root)
    palette.grab_set()

    fg = "#FFFFFF" if CURRENT_BG != "#FFFFFF" else "#000000"
    
    style.configure("TEntry", padding=5, relief="flat")
    style.map("TEntry",
              background=[("active", CURRENT_BG)],
              foreground=[("active", fg)])

    # Search bar
    search_var = tk.StringVar()
    search_entry = ttk.Entry(palette, textvariable=search_var)
    search_entry.pack(fill="x", padx=10, pady=10)
    search_entry.focus()

    # Results frame
    results_frame = tk.Frame(palette, bg=CURRENT_BG)
    results_frame.pack(fill="both", expand=True)

    # Preview panel
    preview = tk.Label(palette, text="", bg=CURRENT_BG, fg=fg, anchor="nw", justify="left")
    preview.pack(fill="x", padx=10, pady=5)

    def render_results(query=""):
        for child in results_frame.winfo_children():
            child.destroy()

        # Fuzzy or normal search
        if FUZZY_ENABLED:
            filtered = fuzzy_match(query.lower(), [cmd["name"] for cmd in COMMANDS])
            filtered_cmds = [cmd for cmd in COMMANDS if cmd["name"] in filtered]
        else:
            filtered_cmds = [cmd for cmd in COMMANDS if query.lower() in cmd["name"].lower()]

        # Group by category
        categories = {}
        for cmd in filtered_cmds:
            categories.setdefault(cmd["category"], []).append(cmd)

        for cat, cmds in categories.items():
            cat_label = tk.Label(results_frame, text=cat, bg=CURRENT_BG, fg=fg,
                                 font=("TkDefaultFont", 10, "bold"))
            cat_label.pack(anchor="w", padx=10, pady=(5, 0))

            for cmd in cmds:
                btn = tk.Button(
                    results_frame,
                    text=cmd["name"],
                    bg=CURRENT_BG,
                    fg=fg,
                    anchor="w",
                    relief="flat",
                    highlightthickness=0,
                    command=lambda c=cmd: (c["action"](), palette.destroy())
                )
                btn.pack(fill="x", padx=20, pady=2)

                # Hover preview
                def on_enter(e, c=cmd):
                    preview.config(text=c["description"])

                def on_leave(e):
                    preview.config(text="")

                btn.bind("<Enter>", on_enter)
                btn.bind("<Leave>", on_leave)

    def on_search(*_):
        render_results(search_var.get())

    search_var.trace_add("write", on_search)
    render_results()
    

# Ctrl+Space → open command palette
root.bind("<Control-p>", lambda e: open_command_palette())

def switch_tab(offset):
    current = notebook.index("current")
    total = len(tab_names)
    new_index = (current + offset) % total
    notebook.select(new_index)

root.bind("<Control-Tab>", lambda e: switch_tab(1))
root.bind("<Control-Shift-Tab>", lambda e: switch_tab(-1))

# -------------------------------
#  Render Buttons Into Tabs
# -------------------------------

def add_button_to_tab(tab_name, label, callback):
    tab = tabs[tab_name]
    frame = tk.Frame(tab, bg=CURRENT_BG)
    frame.pack(fill="x", padx=20, pady=8)

    item = {
        "name": label,
        "type": "inline",
        "tab": tab_name,
        "command": None,
        "kind": "action"
    }

    btn = ttk.Button(frame, text=label, command=callback)
    btn.pack(fill="x")

    # -----------------------------
    # FAVORITE CONTEXT MENU (normal tabs only)
    # -----------------------------
    
    def is_favorite(it):
        if not isinstance(favorites, list):
            return False
        return any(f["name"] == it["name"] for f in favorites)

    def add_to_favorites(it):
        real = next((x for x in items if x["name"] == it["name"]), None)
        if real is None:
            real = it
                    
        if not is_favorite(real):
            favorites.append(real)
            save_favorites()
            refresh_favorites()

    def remove_from_favorites(it):
        global favorites
        favorites = [f for f in favorites if f["name"] != it["name"]]
        save_favorites()
        refresh_favorites()

    def show_fav_menu(event, it=item):
        menu = tk.Menu(btn, tearoff=0,
                       bg=CURRENT_BG,
                       fg="#FFFFFF" if CURRENT_BG != "#FFFFFF" else "#000000")

        if is_favorite(it):
            menu.add_command(
                label="Remove from Favorites",
                command=lambda: remove_from_favorites(it)
            )
        else:
            menu.add_command(
                label="Add to Favorites",
                command=lambda: add_to_favorites(it)
            )

        menu.tk_popup(event.x_root, event.y_root)

    # Attach right-click menu ONLY for non-Favorites tabs
    if tab_name != "Favorites":
        btn.bind("<Button-3>", show_fav_menu)

def refresh_favorites():
    tab = tabs["Favorites"]
    for child in tab.winfo_children():
        child.destroy()
        
    add_section(tab, "Favorites")

    fg = "#FFFFFF" if CURRENT_BG != "#FFFFFF" else "#000000"

    if not favorites:
        tk.Label(tab, text="No favorites yet.",
                 bg=CURRENT_BG, fg=fg).pack(pady=20)
        return

    for it in favorites:
        frame = tk.Frame(tab, bg=CURRENT_BG)
        frame.pack(fill="x", padx=20, pady=8)

        def run(it=it):
            if it["type"] == "script":
                run_script_with_popup(it["name"], it["path"])
            else:
                run_inline_with_popup(it["name"], it["command"], it["kind"])

        # Simple button — NO right-click menu
        btn = ttk.Button(frame, text=it["name"], command=run)
        btn.pack(fill="x")

    save_favorites()

    
refresh_favorites()

# -------------------------------
#  PLUGIN WIDGET SUPPORT
# -------------------------------
def add_widget_to_tab(tab_widget, widget_func):
    widget = widget_func(tab_widget)
    if widget is not None:
        widget.plugin_owned = True
    return widget


def inject_plugin_widgets():
    if not PLUGINS_READY:
        return
    
    for tab_name, func in PLUGIN_API["add_widget"]:
        widget = func(tabs[tab_name])
        if widget is not None:
            widget.plugin_owned = True


# -------------------------------
#  STARTUP ORDER (IMPORTANT)
# -------------------------------
# 1. Load plugins (register items + widget funcs)
run_async(load_plugins)

# 2. Build ONLY built-in buttons
for item in items:
    if not item.get("plugin", False):
        if item["type"] == "script":
            add_button_to_tab(
                item["tab"],
                item["name"],
                lambda it=item: run_script_with_popup(it["name"], it["path"])
            )
        else:
            add_button_to_tab(
                item["tab"],
                item["name"],
                lambda it=item: run_inline_with_popup(it["name"], it["command"], it["kind"])
            )

# 3. Inject plugin widgets ONCE at startup
PLUGINS_READY = True
inject_plugin_widgets()

# -------------------------------
#  Scheduler
# -------------------------------
scheduled_tasks = []
scheduler_running = True

def scheduler_loop():
    while scheduler_running:
        now = datetime.now().strftime("%H:%M")
        for task in scheduled_tasks[:]:
            if task["time"] == now:
                # Run task
                if task["type"] == "script":
                    run_script_with_popup(task["name"], task["path"])
                else:
                    run_inline_with_popup(task["name"], task["command"], task["kind"])
                scheduled_tasks.remove(task)
                refresh_task_list()
        time.sleep(30)

threading.Thread(target=scheduler_loop, daemon=True).start()

# --- Scheduler UI ---
sched_frame = tabs["Scheduler"]

ttk.Label(sched_frame, text="Schedule a Command").pack(pady=10)

# Dropdown of commands
command_names = [it["name"] for it in items]
command_var = tk.StringVar()
command_dropdown = ttk.Combobox(sched_frame, textvariable=command_var,
                                values=command_names, state="readonly")
command_dropdown.pack(pady=5)

# Time entry
ttk.Label(sched_frame, text="Time (HH:MM)").pack(pady=(10, 0))
time_var = tk.StringVar()
time_entry = ttk.Entry(sched_frame, textvariable=time_var)
time_entry.pack(pady=5)

# Task list
scheduler_list_frame = tk.Frame(sched_frame, bg=CURRENT_BG)
scheduler_list_frame.pack(fill="both", expand=True, pady=10)

def refresh_task_list():
    for child in scheduler_list_frame.winfo_children():
        child.destroy()

    fg = "#FFFFFF" if CURRENT_BG != "#FFFFFF" else "#000000"

    if not scheduled_tasks:
        tk.Label(scheduler_list_frame, text="No scheduled tasks.",
                 bg=CURRENT_BG, fg=fg).pack()
        return

    for task in scheduled_tasks:
        row = tk.Frame(scheduler_list_frame, bg=CURRENT_BG)
        row.pack(fill="x", pady=3)

        label = tk.Label(row, text=f"{task['time']} — {task['name']}",
                         bg=CURRENT_BG, fg=fg)
        label.pack(side="left", padx=5)

        def cancel_task(t=task):
            scheduled_tasks.remove(t)
            refresh_task_list()

        ttk.Button(row, text="Cancel", command=cancel_task).pack(side="right")

def schedule_task():
    name = command_var.get()
    time_str = time_var.get().strip()

    if not name or not time_str:
        show_popup("Error", "Please select a command and enter a time.")
        return

    # Find the command
    for it in items:
        if it["name"] == name:
            scheduled_tasks.append({
                "name": it["name"],
                "type": it["type"],
                "time": time_str,
                "command": it.get("command"),
                "path": it.get("path"),
                "kind": it.get("kind")
            })
            refresh_task_list()
            show_popup("Scheduled", f"{name} scheduled for {time_str}")
            return

ttk.Button(sched_frame, text="Schedule", command=schedule_task).pack(pady=10)


# -------------------------------
#  Search Upgrades
# -------------------------------
search_frame = tabs["Search"]

search_label = ttk.Label(search_frame, text="Search commands")
search_label.pack(pady=(20, 5))

search_var = tk.StringVar()
search_entry = ttk.Entry(search_frame, textvariable=search_var)
search_entry.pack(fill="x", padx=20, pady=(0, 10))

results_container = tk.Frame(search_frame, bg=CURRENT_BG)
results_container.pack(fill="both", expand=True, padx=10, pady=10)

search_history = []
MAX_HISTORY = 5

# Load history from file
if os.path.exists(SEARCH_HISTORY_FILE):
    try:
        with open(SEARCH_HISTORY_FILE, "r") as f:
            for line in f:
                term = line.strip()
                if term:
                    search_history.append(term)
        search_history = search_history[-MAX_HISTORY:]
    except:
        pass


def clear_search_results():
    for child in results_container.winfo_children():
        child.destroy()

# --- Highlight ---
def highlight(text, query):
    q = query.lower()
    t = text.lower()
    start = t.find(q)
    if start == -1:
        return text
    end = start + len(query)
    return text[:start] + "**" + text[start:end] + "**" + text[end:]


# -------------------------------
#  Search Logic
# -------------------------------

def do_search(*args):
    query = search_var.get().strip().lower()
    clear_search_results()

    fg = "#FFFFFF" if CURRENT_BG != "#FFFFFF" else "#000000"
    results_container.configure(bg=CURRENT_BG)

    # Show history when empty
    if not query:
        if search_history:
            hist_label = tk.Label(results_container, text="Recent Searches:",
                                  bg=CURRENT_BG, fg=fg)
            hist_label.pack(anchor="w", pady=(0, 5))

            for item in reversed(search_history):
                btn = ttk.Button(results_container, text=item,
                                 command=lambda q=item: search_var.set(q))
                btn.pack(fill="x", pady=2)
        return

    # -----------------------------
    # BUILD SEARCH SOURCES
    # -----------------------------
    sources = []

    # 1. Commands
    for name in COMMANDS:
        sources.append({
            "name": name,
            "tab": "Commands",
            "type": "command",
            "command": COMMANDS[COMMANDS.index(name)]
        })

    # 2. Tabs
    for tab_name in tabs:
        sources.append({
            "name": tab_name,
            "tab": "Tabs",
            "type": "tab",
            "command": lambda t=tab_name: notebook.select(tabs[t])
        })

    # 3. Plugins
    for f in os.listdir(PLUGIN_DIR):
        sources.append({
            "name": f,
            "tab": "Plugins",
            "type": "plugin",
            "path": os.path.join(PLUGIN_DIR, f),
            "command": lambda p=os.path.join(PLUGIN_DIR, f): (
                path_var.set(PLUGIN_DIR),
                refresh_files(),
                notebook.select(tabs["Files"])
            )
        })

    def get_dirname(p):
        if os.path.isdir(p):
            return p
        
        return os.path.dirname(p)

    # 4. Files (non-recursive for now)
    for f in os.listdir(path_var.get()):
        sources.append({
            "name": f,
            "tab": "Files",
            "type": "file",
            "path": os.path.join(path_var.get(), f),
            "command": lambda p=os.path.join(path_var.get(), f): (
                print(p),
                path_var.set(get_dirname(p)),
                print(path_var.get()),
                refresh_files(),
                notebook.select(tabs["Files"])
            )
        })

    # -----------------------------
    # FUZZY MATCH
    # -----------------------------
    
    names = [
        s.get("name", {}).get("name") if isinstance(s.get("name"), dict) 
        else s.get("name", "Unknown") 
        for s in sources
    ]

    
    matches = fuzzy_match(query, names) if FUZZY_ENABLED else [
        n for n in names if query in n.lower()
    ]

    if not matches:
        lbl = tk.Label(results_container,
                       text="No matches.\nTry: files, plugins, commands, tabs",
                       bg=CURRENT_BG, fg=fg)
        lbl.pack(pady=10)
        return

    # Map back to full objects
    # 1. Get the match or None if not found
    matched_items = [
        next((s for s in sources if (s["name"]["name"] if isinstance(s["name"], dict) else s["name"]) == m), None) 
        for m in matches
    ]

    # 2. Filter out any None values to avoid further errors
    matched_items = [item for item in matched_items if item is not None]


    # -----------------------------
    # GROUP BY TAB
    # -----------------------------
    grouped = {}
    for it in matched_items:
        grouped.setdefault(it["tab"], []).append(it)

    # -----------------------------
    # RENDER RESULTS
    # -----------------------------
    for tab_name, group in grouped.items():
        header = tk.Label(results_container, text=tab_name,
                          bg=CURRENT_BG, fg=fg, font=("TkDefaultFont", 10, "bold"))
        header.pack(anchor="w", pady=(10, 2))

        for it in group:
            outer = tk.Frame(results_container, bg=CURRENT_BG)
            outer.pack(fill="x", pady=2)
            
            to_match = it.get("name", {}).get("name") if isinstance(it.get("name"), dict) else it.get("name", "Unknown")
            display = highlight(to_match, query)

            def run_and_record(it=it):
                # Save history
                if query not in search_history:
                    search_history.append(query)
                    if len(search_history) > MAX_HISTORY:
                        search_history.pop(0)
                    try:
                        with open(SEARCH_HISTORY_FILE, "w") as f:
                            for term in search_history:
                                f.write(term + "\n")
                    except:
                        pass
                else:
                    del search_history[search_history.index(query)]
                    search_history.append(query)
                    if len(search_history) > MAX_HISTORY:
                        search_history.pop(0)
                    try:
                        with open(SEARCH_HISTORY_FILE, "w") as f:
                            for term in search_history:
                                f.write(term + "\n")
                    except:
                        pass

                # Execute
                # 1. Safely extract the potential command
                if isinstance(it.get("name"), dict):
                    # For nested 'Command' type items
                    cmd = it.get("name", {}).get("action")
                else:
                    # For flat 'Tab' or 'File' type items
                    if "command" in it:
                        cmd = it.get("command")
                    else:
                        cmd = it.get("action")

                # 2. Check if it's a function before calling it
                if callable(cmd):
                    cmd()
                else:
                    print(f"Error: No executable command found for {it.get('name')}")


            ttk.Button(outer, text=display, command=run_and_record).pack(fill="x")

# -------------------------------
#  Keyboard Navigation
# -------------------------------
selected_index = -1
search_results_flat = []

def update_flat_results():
    global search_results_flat
    search_results_flat = [child for child in results_container.winfo_children()
                           if isinstance(child, tk.Frame)]

def move_selection(delta):
    global selected_index
    update_flat_results()

    if not search_results_flat:
        return

    selected_index = (selected_index + delta) % len(search_results_flat)

    for i, frame in enumerate(search_results_flat):
        frame.configure(bg="#5555AA" if i == selected_index else CURRENT_BG)

def run_selected():
    if 0 <= selected_index < len(search_results_flat):
        btn = search_results_flat[selected_index].winfo_children()[0]
        btn.invoke()

def clear_search():
    search_var.set("")
    clear_search_results()

search_entry.bind("<Down>", lambda e: move_selection(1))
search_entry.bind("<Up>", lambda e: move_selection(-1))
search_entry.bind("<Return>", lambda e: run_selected())
search_entry.bind("<Escape>", lambda e: (clear_search(), do_search()))

search_var.trace_add("write", do_search)

root.mainloop()
