import os

# Railway будет брать эти данные из раздела Variables
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

# Превращаем строку ID чата в число
CHAT = int(os.getenv("CHAT", "0"))

# Превращаем строку админов "123,456" в список чисел [123, 456]
ADMINS_STR = os.getenv("ADMINS", "")
ADMINS = [int(x.strip()) for x in ADMINS_STR.split(",") if x.strip()]

DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)