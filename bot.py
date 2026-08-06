import os
import asyncio
import traceback
import pyrogram.errors

# --- ГЛОБАЛЬНЫЙ ПАТЧ СОВМЕСТИМОСТИ (Senior Level) ---
# Исправляем несовместимость имен между Pyrogram 2.0 и Py-TgCalls 2.3+
# Мы мапим существующие ошибки на те имена, которые ищет библиотека.

# Список имен, которые ищет py-tgcalls : существующие аналоги в pyrogram
error_map = {
    "GroupcallForbidden": "GroupCallForbidden",
    "GroupcallInvalid": "GroupCallInvalid",
    "GroupcallAlreadyJoined": "GroupCallAlreadyJoined"
}

for target, source in error_map.items():
    if not hasattr(pyrogram.errors, target):
        # Берем существующий класс или создаем заглушку, если даже аналога нет
        error_class = getattr(pyrogram.errors, source, type(target, (Exception,), {}))
        setattr(pyrogram.errors, target, error_class)

print("[SYSTEM] Патч совместимости применен успешно.")
# ----------------------------------------------------

from pyrogram import Client, filters, idle
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import config

# Инициализация (Railway - прямой интернет)
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

    status = await message.reply("⏳ Загрузка видео на Railway...")
    path = os.path.join(config.DOWNLOAD_DIR, f"v_{message.id}.mp4")

    try:
        file_path = await client.download_media(message.reply_to_message.video, file_name=path)
        await status.edit("🚀 Запуск трансляции...")
        
        # Запускаем без параметров качества (по умолчанию), чтобы избежать AttributeError
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
    print("--- ЗАПУСК НА RAILWAY ---")
    await app.start()
    await calls.start()
    print(f"✅ Бот активен в чате: {config.CHAT}")
    await idle()
    await app.stop()

if __name__ == "__main__":
    # Исправляем работу Event Loop в Windows/Linux средах
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
