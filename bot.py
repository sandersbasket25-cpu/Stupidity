import os
import asyncio
import traceback
import sys
import pyrogram.errors
import pyrogram.raw.types

# Форсируем вывод в лог Railway мгновенно
def log(text):
    print(text, flush=True)

log("[SYSTEM] Запуск скрипта...")

# --- ПАТЧИ (БЕЗ ИЗМЕНЕНИЙ) ---
error_map = {"GroupcallForbidden": "GroupCallForbidden", "GroupcallInvalid": "GroupCallInvalid"}
for target, source in error_map.items():
    if not hasattr(pyrogram.errors, target):
        err = getattr(pyrogram.errors, source, type(target, (Exception,), {}))
        setattr(pyrogram.errors, target, err)
if not hasattr(pyrogram.raw.types, "InputGroupCallSlug"):
    setattr(pyrogram.raw.types, "InputGroupCallSlug", type("InputGroupCallSlug", (), {"ID": 0x0}))
if not hasattr(pyrogram.raw.types, "PhoneCallDiscardReasonMigrateConferenceCall"):
    setattr(pyrogram.raw.types, "PhoneCallDiscardReasonMigrateConferenceCall", type("PhoneCallDiscardReasonMigrateConferenceCall", (), {"ID": 0x0}))
log("[SYSTEM] Патчи применены.")

from pyrogram import Client, filters, idle
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import config

app = Client(
    "railway_session",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING,
    sleep_threshold=600 # Увеличили до 10 минут
)

calls = PyTgCalls(app)

@app.on_message(filters.chat(config.CHAT) & filters.command(["play", "stop", "pause", "resume"]) & (filters.me | filters.user(config.ADMINS)))
async def command_handler(client, message):
    if not message.text: return
    cmd = message.command[0].lower()
    log(f"[LOG] Получена команда: {cmd} от {message.from_user.id}")

    if cmd == "play":
        if not message.reply_to_message or not message.reply_to_message.video:
            return await message.reply("❌ Ответь на видео!")

        status = await message.reply("⏳ Загрузка видео...")
        path = os.path.join(config.DOWNLOAD_DIR, f"v_{message.id}.mp4")
        try:
            file_path = await client.download_media(message.reply_to_message.video, file_name=path)
            log(f"[ACTION] Файл скачан: {file_path}")
            await status.edit("🚀 Запуск трансляции...")
            await calls.play(config.CHAT, MediaStream(file_path))
            await status.edit("✅ Видео запущено!")
        except Exception as e:
            log(f"[ERROR] {e}")
            await status.edit(f"🔴 Ошибка: {str(e)[:100]}")

    elif cmd == "stop":
        await calls.leave_call(config.CHAT)
        await message.reply("⏹ Стоп.")

async def main():
    log("--- ИНИЦИАЛИЗАЦИЯ main() ---")
    try:
        log("Шаг 1: Подключение к Telegram...")
        await app.start()
        log("✅ Аккаунт подключен!")
        
        log("Шаг 2: Запуск PyTgCalls...")
        await calls.start()
        log(f"✅ Плеер активен в чате {config.CHAT}")
        
        log("--- БОТ ПОЛНОСТЬЮ ГОТОВ ---")
        await idle()
    except Exception as e:
        log(f"❌ Ошибка в main: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
