import os
import asyncio
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

calls = PyTgCalls(app)

@app.on_message(filters.chat(config.CHAT) & filters.command("play"))
async def play_handler(client, message):
    if not message.reply_to_message or not message.reply_to_message.video:
        return await message.reply("❌ Ответь на видео!")

    status = await message.reply("⏳ Загрузка...")
    path = os.path.join(config.DOWNLOAD_DIR, f"v_{message.id}.mp4")

    try:
        file_path = await client.download_media(message.reply_to_message.video, file_name=path)
        
        # В версии 2.x просто передаем путь в MediaStream
        await calls.play(
            config.CHAT,
            MediaStream(file_path)
        )
        await status.edit("✅ Трансляция запущена!")
    except Exception as e:
        await status.edit(f"🔴 Ошибка: {e}")

@app.on_message(filters.chat(config.CHAT) & filters.command("stop"))
async def stop_handler(client, message):
    await calls.leave_call(config.CHAT)
    await message.reply("⏹ Остановлено.")

async def main():
    await app.start()
    await calls.start()
    print("--- БОТ ЗАПУЩЕН НА RAILWAY ---")
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
