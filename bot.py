import os
import asyncio
import traceback
import sys
import pyrogram.errors

# --- СУПЕР-ПАТЧ (БЕЗ ИЗМЕНЕНИЙ) ---
import pyrogram.raw.types
error_map = {"GroupcallForbidden": "GroupCallForbidden", "GroupcallInvalid": "GroupCallInvalid"}
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
import config

# Инициализация с огромным порогом ожидания
app = Client(
    "userbot_railway",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    sleep_threshold=1000 # Позволяем боту ждать очень долго
)

calls = PyTgCalls(app)

@app.on_message(filters.chat(config.CHAT) & filters.command(["play", "stop"]) & (filters.me | filters.user(config.ADMINS)))
async def handle_commands(client, message):
    if message.command[0] == "play":
        if not message.reply_to_message or not message.reply_to_message.video:
            return await message.reply("Ответь на видео!")
        
        status = await message.reply("⏳ Качаю...")
        path = os.path.join(config.DOWNLOAD_DIR, f"{message.id}.mp4")
        try:
            file_path = await client.download_media(message.reply_to_message.video, file_name=path)
            await status.edit("🚀 Запускаю...")
            await calls.play(config.CHAT, MediaStream(file_path))
            await status.edit("✅ Играет!")
        except Exception as e:
            await status.edit(f"❌ Ошибка: {e}")

    elif message.command[0] == "stop":
        await calls.leave_call(config.CHAT)
        await message.reply("⏹ Стоп.")

async def main():
    print("--- СИСТЕМА ЗАПУСКАЕТСЯ ---")
    try:
        # Мы НЕ вызываем get_me(), чтобы не тратить лимиты запросов
        await app.start()
        print("1. Юзербот подключен.")
        
        await asyncio.sleep(5)
        
        await calls.start()
        print(f"2. Плеер готов. Чат: {config.CHAT}")
        
        print("--- БОТ В ОНЛАЙНЕ ---")
        await idle()
    except pyrogram.errors.FloodWait as e:
        print(f"!!! НУЖНО ПОДОЖДАТЬ {e.value} СЕКУНД !!!")
        await asyncio.sleep(e.value + 10)
        # Railway может убить процесс, но при следующем запуске время будет меньше
    except Exception as e:
        print(f"Ошибка старта: {e}")
    finally:
        try: await app.stop()
        except: pass

if __name__ == "__main__":
    asyncio.run(main())
