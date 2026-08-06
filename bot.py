import os
import asyncio
import traceback
import sys

# --- ULTRA MONKEYPATCH (Senior Developer Level) ---
# Нам нужно внедрить типы в несколько модулей pyrogram

import pyrogram.errors
import pyrogram.raw.types

# 1. Патчим ошибки
error_map = {
    "GroupcallForbidden": "GroupCallForbidden",
    "GroupcallInvalid": "GroupCallInvalid",
    "GroupcallAlreadyJoined": "GroupCallAlreadyJoined"
}
for target, source in error_map.items():
    if not hasattr(pyrogram.errors, target):
        err = getattr(pyrogram.errors, source, type(target, (Exception,), {}))
        setattr(pyrogram.errors, target, err)

# 2. Патчим Raw Types (то, на чем упал последний деплой)
# Библиотека ищет InputGroupCallSlug, которого нет в оф. версии
if not hasattr(pyrogram.raw.types, "InputGroupCallSlug"):
    # Создаем фиктивный класс типа, чтобы импорт прошел успешно
    class InputGroupCallSlug:
        ID = 0xdeadbeef # Фейковый ID для схемы
    setattr(pyrogram.raw.types, "InputGroupCallSlug", InputGroupCallSlug)

print("[SYSTEM] Ultra-Patch для Pyrogram 2.0 применен.")
# ----------------------------------------------------

from pyrogram import Client, filters, idle
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import config

app = Client(
    "railway_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING
)

# Теперь импорт и инициализация пройдут успешно
calls = PyTgCalls(app)

@app.on_message(filters.chat(config.CHAT) & filters.command("play"))
async def play_handler(client, message):
    if not message.reply_to_message or not message.reply_to_message.video:
        return await message.reply("❌ Ответь на видео!")

    status = await message.reply("⏳ Загрузка видео...")
    path = os.path.join(config.DOWNLOAD_DIR, f"v_{message.id}.mp4")

    try:
        file_path = await client.download_media(message.reply_to_message.video, file_name=path)
        await status.edit("🚀 Запуск трансляции...")
        
        await calls.play(config.CHAT, MediaStream(file_path))
        await status.edit("✅ Трансляция запущена!")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        await status.edit(f"🔴 Ошибка: {str(e)[:100]}")
        if os.path.exists(path):
            os.remove(path)

@app.on_message(filters.chat(config.CHAT) & filters.command("stop"))
async def stop_handler(client, message):
    try:
        await calls.leave_call(config.CHAT)
        await message.reply("⏹ Остановлено.")
    except Exception as e:
        await message.reply(f"🔴 Ошибка: {e}")

async def main():
    print("--- ЗАПУСК НА RAILWAY (FIXED RAW) ---")
    await app.start()
    await calls.start()
    print(f"✅ Бот онлайн. Чат: {config.CHAT}")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
