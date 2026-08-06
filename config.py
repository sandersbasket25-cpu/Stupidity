import os

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

CHAT = int(os.getenv("CHAT", "0"))

admins_raw = os.getenv("ADMINS", "")
ADMINS = [int(x.strip()) for x in admins_raw.split(",") if x.strip()]

DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)
