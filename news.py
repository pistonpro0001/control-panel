import feedparser
import html
import requests
from io import BytesIO
import os
from bs4 import BeautifulSoup
from PIL import Image, ImageTk
import tkinter as tk
import webbrowser
from ftfy import fix_text

FEED_URL = "http://planetpython.org/rss20.xml"
SCROLL_SPEED = 3

LIGHT_THEME = {
    "bg": "#FFFFFF",
    "fg": "#000000",
    "title_fg": "#0044AA",
    "divider": "#CCCCCC",
    "button_bg": "#EEEEEE",
    "button_fg": "#000000",
}

DARK_THEME = {
    "bg": "#1E1E1E",
    "fg": "#E0E0E0",
    "title_fg": "#6CA8FF",
    "divider": "#444444",
    "button_bg": "#333333",
    "button_fg": "#FFFFFF",
}

def load_theme():
    theme_file = "/home/pi/.controlpanel_theme"
    if os.path.exists(theme_file):
        try:
            mode = open(theme_file).read().strip().lower()
            if mode == "dark":
                return DARK_THEME
        except:
            pass
    return LIGHT_THEME


def bind_mousewheel(widget, target):
    # Windows + Linux
    widget.bind_all("<MouseWheel>", lambda e: target.yview_scroll(int(-1*(e.delta/120)) * SCROLL_SPEED, "units"))
    # macOS
    widget.bind_all("<Button-4>", lambda e: target.yview_scroll(-1, "units"))
    widget.bind_all("<Button-5>", lambda e: target.yview_scroll(1, "units"))
    
def extract_first_image(soup):
    # Find the first <img> anywhere in the summary
    img = soup.find("img")
    if not img:
        return None

    src = img.get("src") or img.get("data-src")
    if not src:
        return None

    # Skip SVGs (Pillow can't open them)
    if src.lower().endswith(".svg"):
        return None

    return src

def extract_paragraphs(summary_html, count=3):
    # Use 'lxml' or 'html.parser'
    soup = BeautifulSoup(summary_html, "html.parser")

    # 1. Try to find actual <p> tags (standard blogs)
    paragraphs = soup.find_all("p")
    
    if paragraphs:
        # Filter out empty or very short paragraphs
        valid_p = [p.get_text(" ", strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 5]
        selected = valid_p#[:count]
        text = "\n\n".join(selected)
    else:
        # 2. Fallback for IGN/News: No <p> tags found
        # We strip out scripts/styles first to avoid "garbage" text
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
            
        # Get all text, using a double newline to separate any block elements
        text = soup.get_text("\n\n", strip=True)
        
        # 3. Trim the text so it doesn't fill the whole screen if the feed is huge
        if len(text) > 800:
            text = text[:800].rsplit(' ', 1)[0] + "..."

    # Fix encoding and unescape HTML entities (like &amp; or &quot;)
    text = fix_text(html.unescape(text))

    # Existing image extraction
    img_src = extract_first_image(soup)
    images = [img_src] if img_src else []
    
    return text, images

def open_link(url):
    webbrowser.open(url)


def show_news(feed_url):
    feed = feedparser.parse(feed_url)

    root = tk.Tk()
    root.title("News")

    canvas = tk.Canvas(root, width=800, height = 600)
    scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas)

    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    theme = load_theme()

    root.configure(bg=theme["bg"])
    canvas.configure(bg=theme["bg"])
    scroll_frame.configure(bg=theme["bg"])

    for entry in feed.entries:
        title = entry.get("title", "No title")
        link = entry.get("link", "")
        summary_html = entry.get("summary", "")
        
        title = fix_text(title)
        
        count = 5
        if "podcast" in title.lower():
            count = 1
            
        text, image_urls = extract_paragraphs(summary_html, count=5)

        frame = tk.Frame(scroll_frame, padx=10, pady=10, bg=theme["bg"])
        frame.pack(fill="x", anchor="w")

        # Title (clickable)
        title_label = tk.Label(
            frame,
            text=title,
            fg=theme["title_fg"],
            bg=theme["bg"],
            cursor="hand2",
            font=("Arial", 14, "bold"),
            wraplength=760,
            justify="left"
        )
        title_label.pack(anchor="w")
        title_label.bind("<Button-1>", lambda e, url=link: open_link(url))

        # Images (if present)
        for img_url in image_urls:
            try:
                headers = {"User-Agent": "Mozilla/5.0"}

                resp = requests.get(img_url, headers=headers, timeout=10)
                resp.raise_for_status()
                img_data = resp.content

                pil_img = Image.open(BytesIO(img_data))
                pil_img.thumbnail((600, 400))
                tk_img = ImageTk.PhotoImage(pil_img)

                img_label = tk.Label(frame, image=tk_img, bg=theme["bg"])
                img_label.image = tk_img
                img_label.pack(anchor="w", pady=5)
            except Exception as e:
                print("Image load failed:", e)

        # Text paragraphs
        text_label = tk.Label(
            frame,
            text=text,
            fg=theme["fg"],
            bg=theme["bg"],
            wraplength=760,
            justify="left",
            font=("Arial", 11)
        )

        text_label.pack(anchor="w", pady=5)

        # Link button
        link_button = tk.Button(
            frame,
            text="Read more",
            command=lambda url=link: open_link(url),
            bg=theme["button_bg"],
            fg=theme["button_fg"],
            activebackground=theme["button_bg"],
            activeforeground=theme["button_fg"]
        )

        link_button.pack(anchor="w")

        divider = tk.Frame(scroll_frame, height=2, bg=theme["divider"])
        divider.pack(fill="x", pady=10)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    canvas.bind("<Enter>", lambda e: bind_mousewheel(canvas, canvas))
    canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    root.mainloop()


if __name__ == "__main__":
    show_news(FEED_URL)
