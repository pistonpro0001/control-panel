import imaplib
import email
from email.header import decode_header
import json

with open("/home/pi/pass.json", "r") as f:
    l = json.load(f)
    
    USERNAME = l["mail"]
    APP_PASSWORD = l["app_pas"]

IMAP_SERVER = "imap.gmail.com"

is_google = lambda sender: "@google.com" in sender.lower() or "google" in sender.lower() or "twitch.tv" in sender.lower()

def decode_maybe(encoded):
    """Decode email headers safely."""
    if not encoded:
        return ""
    parts = decode_header(encoded)
    decoded = ""
    for text, enc in parts:
        if isinstance(text, bytes):
            decoded += text.decode(enc or "utf-8", errors="replace")
        else:
            decoded += text
    return decoded

def fetch_latest_emails(username=USERNAME, app_password=APP_PASSWORD, count=5):
    # Connect to Gmail IMAP
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(username, app_password)

    # Select inbox
    mail.select("inbox")

    # Search for all messages
    result, data = mail.search(None, "ALL")
    ids = data[0].split()

    # Get the last N message IDs

    emails = []

    for msg_id in reversed(ids):
        if len(emails) > count:
            break
            
        result, msg_data = mail.fetch(msg_id, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        sender = decode_maybe(msg.get("From"))
        subject = decode_maybe(msg.get("Subject"))

        if is_google(sender):
            continue
        
        emails.append((sender, subject))

    mail.logout()
    return emails


if __name__ == "__main__":
    # Replace these with your actual Gmail + App Password

    print("Fetching latest emails...\n")

    try:
        messages = fetch_latest_emails(USERNAME, APP_PASSWORD, count=55)
        for i, (sender, subject) in enumerate(messages, 1):
            print(f"{i}. From: {sender}")
            print(f"   Subject: {subject}\n")

    except Exception as e:
        print("Error:", e)
        
#get_latest_email("piston.pro0001@gmail.com", "omanzpilipwtjzxf")
