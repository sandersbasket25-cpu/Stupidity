import os
import asyncio
import traceback
import sys
import pyrogram.errors

# --- СУПЕР-ПАТЧ СОВМЕСТИМОСТИ ---
import pyrogram.raw.types
error_map = {
    "GroupcallForbidden": "GroupCallForbidden", 
    "GroupcallInvalid": "GroupCallInvalid",
    "GroupcallAlreadyJoined": "GroupCallAlreadyJoined"
}
for target, source in error_map.items():
    if not hasattr(pyrogram.errors, target):
        err = getattr(pyrogram.errors, source, type(target, (Exception,), {}))
        setattr(pyrogram.errors, target, err)

# Патчим типы данных для Py-TgCalls 2.3.x
missing_types = ["InputGroupCallSlug", "PhoneCallDiscardReasonMigrateConferenceCall"]
for t in missing_types:
    if not hasattr(pyrogram.raw.types, t):
        setattr(pyrogram.raw.types, t, type(t, (), {"ID": 0x0}))

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
    sleep_threshold=180 # Авто-ожидание до 3 минут
)

calls = PyTgCalls(app)

@app.on_message(filters.chat(config.CHAT) & filters.command(["play", "stop", "pause", "resume"]) & (filters.me | filters.user(config.ADMINS)))
async def command_handler(client, message):
    if not message.text: return
    cmd = message.command[0].lower()

    if cmd == "play":
        if not message.reply_to_message or not message.reply_to_message.video:
            return await message.reply("❌ Ответь на видео этой командой!")

        status = await message.reply("⏳ Юзербот обрабатывает видео...")
        path = os.path.join(config.DOWNLOAD_DIR, f"v_{message.id}.mp4")

        try:
            file_path = await client.download_media(message.reply_to_message.video, file_name=path)
            await status.edit("🚀 Запуск трансляции в видеочате...")
            
            await calls.play(config.CHAT, MediaStream(file_path))
            await status.edit("✅ Видео запущено!")
            
        except Exception as e:
            print(f"[ERROR] {e}")
            await status.edit(f"🔴 Ошибка:\n`{str(e)[:100]}`")
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
        # Шаг 1: Запуск клиента Pyrogram
        await app.start()
        print("✅ Аккаунт Krasavitsa подключен.")
        
        # Шаг 2: Пауза 10 секунд (чтобы Telegram не давал FloodWait)
        print("⏳ Ждем 10 секунд перед запуском плеера...")
        await asyncio.sleep(10)
        
        # Шаг 3: Запуск PyTgCalls
        await calls.start()
        print(f"✅ Плеер активен в чате: {config.CHAT}")
        
        print("--- СИСТЕМА ПОЛНОСТЬЮ ГОТОВА ---")
        await idle()
    except pyrogram.errors.FloodWait as e:
        print(f"🔴 FloodWait: нужно подождать {e.value} секунд...")
        await asyncio.sleep(e.value + 5)
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        traceback.print_exc()
    finally:
        try: await app.stop()
        except: pass

if __name__ == "__main__":
    asyncio.run(main())
