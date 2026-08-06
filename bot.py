import os
import asyncio
import traceback
import sys

# --- СУПЕР-ПАТЧ СОВМЕСТИМОСТИ (Senior Level) ---
# Мы принудительно внедряем недостающие типы в Pyrogram до импорта Py-TgCalls
import pyrogram.errors
import pyrogram.raw.types

# 1. Исправляем ошибки (Error Classes)
missing_errors = ["GroupcallForbidden", "GroupcallInvalid", "GroupcallAlreadyJoined"]
for err_name in missing_errors:
    if not hasattr(pyrogram.errors, err_name):
        # Пробуем найти аналог или создаем заглушку
        source_name = err_name.replace("Groupcall", "GroupCall")
        err_class = getattr(pyrogram.errors, source_name, type(err_name, (Exception,), {}))
        setattr(pyrogram.errors, err_name, err_class)

# 2. Исправляем Raw-типы (Data Types)
missing_types = ["InputGroupCallSlug", "PhoneCallDiscardReasonMigrateConferenceCall"]
for type_name in missing_types:
    if not hasattr(pyrogram.raw.types, type_name):
        # Создаем фиктивный класс с фейковым ID для схемы MTProto
        fake_type = type(type_name, (), {"ID": 0x0})
        setattr(pyrogram.raw.types, type_name, fake_type)

print("[SYSTEM] Все патчи совместимости применены.")
# -----------------------------------------------

from pyrogram import Client, filters, idle
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import config

# Инициализируем только Юзербота
app = Client(
    "userbot_railway",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING
)

calls = PyTgCalls(app)

# Хендлер команд для Юзербота
# Он будет реагировать на сообщения от админов и на свои собственные
@app.on_message(filters.chat(config.CHAT) & filters.command(["play", "stop", "pause", "resume"]))
async def command_handler(client, message):
    if not message.from_user or (message.from_user.id not in config.ADMINS and not message.from_user.is_self):
        return

    command = message.command[0].lower()

    if command == "play":
        if not message.reply_to_message or not message.reply_to_message.video:
            return await message.reply("❌ Ответь на сообщение с видео!")

        status = await message.reply("⏳ Юзербот скачивает видео...")
        path = os.path.join(config.DOWNLOAD_DIR, f"v_{message.id}.mp4")

        try:
            file_path = await client.download_media(message.reply_to_message.video, file_name=path)
            await status.edit("🚀 Запуск трансляции...")
            
            # В Railway (США/Европа) это сработает стабильно
            await calls.play(config.CHAT, MediaStream(file_path))
            await status.edit("✅ Видео запущено успешно!")
            
        except Exception:
            err = traceback.format_exc()
            print(f"[ERROR] {err}")
            await status.edit(f"🔴 Ошибка:\n`{err[-100:]}`")

    elif command == "stop":
        await calls.leave_call(config.CHAT)
        await message.reply("⏹ Трансляция остановлена.")

    elif command == "pause":
        await calls.pause(config.CHAT)
        await message.reply("⏸ Пауза.")

    elif command == "resume":
        await calls.resume(config.CHAT)
        await message.reply("▶️ Продолжено.")

async def main():
    print("--- ЗАПУСК ЮЗЕРБОТА НА RAILWAY ---")
    await app.start()
    await calls.start()
    
    me = await app.get_me()
    print(f"✅ Юзербот {me.first_name} онлайн.")
    print(f"Слушаю чат: {config.CHAT}")
    
    await idle()
    await app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
