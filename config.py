import os

# Railway Variables
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

# ID чата (группы)
CHAT = int(os.getenv("CHAT", "0"))

# Список админов (принимаем строку "123,456", превращаем в список [123, 456])
admins_raw = os.getenv("ADMINS", "")
ADMINS = [int(x.strip()) for x in admins_raw.split(",") if x.strip()]

DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)
