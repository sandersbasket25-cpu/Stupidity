import os
import asyncio
import traceback
from pyrogram import Client, filters, idle
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import config

# Инициализация клиента (БЕЗ ПРОКСИ)
app = Client(
    "railway_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING
)

calls = PyTgCalls(app)

@app.on_message(filters.chat(config.CHAT) & (filters.me | ~filters.me))
async def handle_commands(client, message):
    if not message.text:
        return

    # Проверка на админа
    if not message.from_user or message.from_user.id not in config.ADMINS:
        return

    if message.text.startswith("/play"):
        if not message.reply_to_message or not message.reply_to_message.video:
            return await message.reply("❌ Ответь на видео!")

        status = await message.reply("⏳ Загрузка видео на сервер Railway...")
        path = os.path.join(config.DOWNLOAD_DIR, f"v_{message.id}.mp4")

        try:
            file_path = await client.download_media(message.reply_to_message.video, file_name=path)
            await status.edit("🚀 Запуск трансляции...")
            
            # В облаке прямой интернет, TelegramServerError (500) здесь почти невозможен
            await calls.play(config.CHAT, MediaStream(file_path))
            await status.edit("✅ Трансляция запущена!")
            
        except Exception:
            err = traceback.format_exc()
            print(f"[ERROR] {err}")
            await status.edit(f"🔴 Ошибка: {err[-100:]}")

    elif message.text.startswith("/stop"):
        try:
            await calls.leave_call(config.CHAT)
            await message.reply("⏹ Остановлено.")
        except:
            pass

async def main():
    print("--- ЗАПУСК НА RAILWAY ---")
    await app.start()
    await calls.start()
    
    # Проверка связи
    try:
        chat = await app.get_chat(config.CHAT)
        print(f"✅ Бот видит чат: {chat.title}")
    except Exception as e:
        print(f"⚠️ Ошибка доступа к чату: {e}")

    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())