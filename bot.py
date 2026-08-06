import os
import asyncio
import traceback
import pyrogram.errors

# --- СИСТЕМНЫЙ ПАТЧ СОВМЕСТИМОСТИ (Senior Fix) ---
# Py-TgCalls 2.3.x ищет GroupcallForbidden, которой нет в обычном Pyrogram.
# Мы создаем её динамически, чтобы избежать ImportError.
if not hasattr(pyrogram.errors, "GroupcallForbidden"):
    setattr(pyrogram.errors, "GroupcallForbidden", type("GroupcallForbidden", (Exception,), {}))
# -------------------------------------------------

from pyrogram import Client, filters, idle
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import config

# Инициализация клиента (Railway использует прямой интернет)
app = Client(
    "railway_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING
)

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
    print("--- ЗАПУСК НА RAILWAY С ПАТЧЕМ ---")
    await app.start()
    await calls.start()
    print(f"✅ Бот запущен. Чат ID: {config.CHAT}")
    await idle()
    await app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
