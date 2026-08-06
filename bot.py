import os
import asyncio
import traceback
import sys
import pyrogram.errors

# --- СУПЕР-ПАТЧ СОВМЕСТИМОСТИ ---
import pyrogram.raw.types
error_map = {"GroupcallForbidden": "GroupCallForbidden", "GroupcallInvalid": "GroupCallInvalid"}
for target, source in error_map.items():
    if not hasattr(pyrogram.errors, target):
        err = getattr(pyrogram.errors, source, type(target, (Exception,), {}))
        setattr(pyrogram.errors, target, err)

if not hasattr(pyrogram.raw.types, "InputGroupCallSlug"):
    setattr(pyrogram.raw.types, "InputGroupCallSlug", type("InputGroupCallSlug", (), {"ID": 0x0}))
if not hasattr(pyrogram.raw.types, "PhoneCallDiscardReasonMigrateConferenceCall"):
    setattr(pyrogram.raw.types, "PhoneCallDiscardReasonMigrateConferenceCall", type("PhoneCallDiscardReasonMigrateConferenceCall", (), {"ID": 0x0}))

print("[SYSTEM] Патчи применены.")
# --------------------------------

from pyrogram import Client, filters, idle
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import config

# Инициализация Юзербота
app = Client(
    "userbot_railway",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING,
    sleep_threshold=120  # Бот будет сам ждать до 2 минут, если Telegram скажет "FloodWait"
)

calls = PyTgCalls(app)

# Команды. filters.me позволяет тебе управлять ботом со своего же аккаунта
@app.on_message(filters.chat(config.CHAT) & filters.command(["play", "stop", "pause", "resume"]) & (filters.me | filters.user(config.ADMINS)))
async def command_handler(client, message):
    cmd = message.command[0].lower()

    if cmd == "play":
        if not message.reply_to_message or not message.reply_to_message.video:
            return await message.reply("❌ Ответь на видео!")

        status = await message.reply("⏳ Обработка видео...")
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

async def main():
    print("--- ЗАПУСК ЮЗЕРБОТА ---")
    try:
        await app.start()
        print("✅ Сессия аккаунта активна.")
        
        # Небольшая пауза для стабилизации после FloodWait
        await asyncio.sleep(2)
        
        await calls.start()
        print(f"✅ Плеер запущен. Чат: {config.CHAT}")
        
        await idle()
    except pyrogram.errors.FloodWait as e:
        print(f"⚠️ Нужно подождать {e.value} сек (FloodWait)...")
        await asyncio.sleep(e.value)
        # После ожидания Railway сам перезапустит бота, и он пойдет дальше
    except Exception as e:
        print(f"❌ Ошибка при старте: {e}")
        traceback.print_exc()
    finally:
        try: await app.stop()
        except: pass

if __name__ == "__main__":
    # Для Python 3.12 на Linux (Railway) это самый надежный запуск
    asyncio.run(main())
