import os
import asyncio
import traceback
import sys
import pyrogram.errors
import pyrogram.raw.types

# --- СУПЕР-ПАТЧ СОВМЕСТИМОСТИ ---
# Это лечит ошибки импорта в Py-TgCalls 2.3+ на Railway
error_map = {
    "GroupcallForbidden": "GroupCallForbidden", 
    "GroupcallInvalid": "GroupCallInvalid",
    "GroupcallAlreadyJoined": "GroupCallAlreadyJoined"
}
for target, source in error_map.items():
    if not hasattr(pyrogram.errors, target):
        err = getattr(pyrogram.errors, source, type(target, (Exception,), {}))
        setattr(pyrogram.errors, target, err)

missing_types = ["InputGroupCallSlug", "PhoneCallDiscardReasonMigrateConferenceCall"]
for t in missing_types:
    if not hasattr(pyrogram.raw.types, t):
        setattr(pyrogram.raw.types, t, type(t, (), {"ID": 0x0}))
# --------------------------------

from pyrogram import Client, filters, idle
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import config  # Импортируем наш конфиг

# Инициализация Юзербота (используем префикс config.)
app = Client(
    "railway_session",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING,
    sleep_threshold=300 # Чтобы не вылетать при FloodWait
)

calls = PyTgCalls(app)

@app.on_message(filters.chat(config.CHAT) & filters.command(["play", "stop", "pause", "resume"]) & (filters.me | filters.user(config.ADMINS)))
async def command_handler(client, message):
    if not message.text: return
    cmd = message.command[0].lower()

    if cmd == "play":
        if not message.reply_to_message or not message.reply_to_message.video:
            return await message.reply("❌ Ответь на видео этой командой!")

        status = await message.reply("⏳ Юзербот загружает видео...")
        path = os.path.join(config.DOWNLOAD_DIR, f"v_{message.id}.mp4")

        try:
            file_path = await client.download_media(message.reply_to_message.video, file_name=path)
            await status.edit("🚀 Запуск трансляции...")
            
            await calls.play(config.CHAT, MediaStream(file_path))
            await status.edit("✅ Трансляция запущена!")
            
        except Exception as e:
            print(f"[ERROR] {e}")
            await status.edit(f"🔴 Ошибка: {str(e)[:100]}")
            if os.path.exists(path): os.remove(path)

    elif cmd == "stop":
        try:
            await calls.leave_call(config.CHAT)
            await message.reply("⏹ Остановлено.")
        except: pass

    elif cmd == "pause":
        await calls.pause(config.CHAT)
        await message.reply("⏸ Пауза.")

    elif cmd == "resume":
        await calls.resume(config.CHAT)
        await message.reply("▶️ Продолжено.")

async def main():
    print("--- ЗАПУСК ЮЗЕРБОТА НА RAILWAY ---")
    try:
        await app.start()
        print("✅ Аккаунт подключен.")
        
        await asyncio.sleep(5) # Защита от моментального спама запросами
        
        await calls.start()
        print(f"✅ Плеер активен. Чат ID: {config.CHAT}")
        
        await idle()
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        traceback.print_exc()
    finally:
        try: await app.stop()
        except: pass

if __name__ == "__main__":
    asyncio.run(main())
