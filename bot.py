import os
import asyncio
import traceback
import sys
import pyrogram.errors
import pyrogram.raw.types
from pyrogram.raw import types

def log(text):
    print(text, flush=True)

# --- ПАТЧИ СОВМЕСТИМОСТИ ---
error_map = {"GroupcallForbidden": "GroupCallForbidden", "GroupcallInvalid": "GroupCallInvalid"}
for target, source in error_map.items():
    if not hasattr(pyrogram.errors, target):
        err = getattr(pyrogram.errors, source, type(target, (Exception,), {}))
        setattr(pyrogram.errors, target, err)

if not hasattr(pyrogram.raw.types, "InputGroupCallSlug"):
    setattr(pyrogram.raw.types, "InputGroupCallSlug", type("InputGroupCallSlug", (), {"ID": 0x0}))
if not hasattr(pyrogram.raw.types, "PhoneCallDiscardReasonMigrateConferenceCall"):
    setattr(pyrogram.raw.types, "PhoneCallDiscardReasonMigrateConferenceCall", type("PhoneCallDiscardReasonMigrateConferenceCall", (), {"ID": 0x0}))
# ---------------------------

from pyrogram import Client, filters, idle
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import config

app = Client(
    "railway_final_v7", 
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING
)

calls = PyTgCalls(app)

# ОБРАБОТЧИК: УБРАНЫ ВСЕ ПРОВЕРКИ АДМИНОВ
@app.on_message(filters.chat(config.CHAT))
async def on_group_message(client, message):
    text = message.text or ""
    log(f"[INCOMING] Сообщение: {text}")

    if text.startswith("/play"):
        log("[ACTION] Попытка запуска видео...")
        
        # Проверяем, есть ли видео в реплае
        video_msg = message.reply_to_message
        if not video_msg or not video_msg.video:
            await message.reply("❌ Ответь этой командой на сообщение с видео!")
            return

        status = await message.reply("⏳ Railway скачивает видео...")
        path = os.path.join(config.DOWNLOAD_DIR, f"v_{video_msg.id}.mp4")

        try:
            file_path = await client.download_media(video_msg.video, file_name=path)
            log(f"[FILE] Видео скачано в {file_path}")
            
            await status.edit("🚀 Запускаю трансляцию...")
            await calls.play(config.CHAT, MediaStream(file_path))
            await status.edit("✅ Видео запущено! Приятного просмотра.")
            
        except Exception as e:
            log(f"[ERROR] {e}")
            await status.edit(f"🔴 Ошибка: {str(e)[:100]}")

    elif text.startswith("/stop"):
        try:
            await calls.leave_call(config.CHAT)
            await message.reply("⏹ Остановлено.")
        except:
            pass

# ФОНОВАЯ ЗАДАЧА: Принудительная синхронизация
async def sync_loop():
    while True:
        try:
            # Читаем историю (это заставляет Telegram "протолкнуть" новые сообщения)
            await app.read_chat_history(config.CHAT)
            # Каждые 10 секунд бот проверяет наличие обновлений
            log("[SYNC] Сообщения прочитаны.")
        except Exception as e:
            log(f"[SYNC ERROR] {e}")
        await asyncio.sleep(10)

async def main():
    log("--- ЗАПУСК СИСТЕМЫ V7 ---")
    try:
        await app.start()
        log("✅ Юзербот подключен.")

        # Синхронизация чата при старте
        async for dialog in app.get_dialogs(limit=20):
            if dialog.chat.id == config.CHAT:
                log(f"✅ Чат '{dialog.chat.title}' синхронизирован.")
                break
        
        await app.send_message(config.CHAT, "🤖 Бот на Railway готов! Фильтры админов отключены. Жду /play")

        await calls.start()
        
        # Запускаем цикл синхронизации
        asyncio.create_task(sync_loop())
        
        await idle()
    except Exception as e:
        log(f"❌ Критическая ошибка: {e}")
        traceback.print_exc()
    finally:
        try: await app.stop()
        except: pass

if __name__ == "__main__":
    asyncio.run(main())
