import os
import asyncio
import traceback
import sys
import pyrogram.errors
import pyrogram.raw.types
from pyrogram import Client, idle
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import config

# --- СУПЕР-ПАТЧ СОВМЕСТИМОСТИ ---
def apply_patches():
    error_map = {
        "GroupcallForbidden": "GroupCallForbidden", 
        "GroupcallInvalid": "GroupCallInvalid",
        "GroupcallAlreadyJoined": "GroupCallAlreadyJoined"
    }
    for target, source in error_map.items():
        if not hasattr(pyrogram.errors, target):
            err = getattr(pyrogram.errors, source, type(target, (Exception,), {}))
            setattr(pyrogram.errors, target, err)
    missing_types = ["InputGroupCallSlug", "PhoneCallDiscardReasonMigrateConferenceCall"]
    for t in missing_types:
        if not hasattr(pyrogram.raw.types, t):
            setattr(pyrogram.raw.types, t, type(t, (), {"ID": 0x0}))
    print("[SYSTEM] Патчи применены.")

def log(text):
    print(text, flush=True)

# Глобальные переменные, которые мы инициализируем внутри main
app = None
calls = None
last_processed_id = 0

async def process_msg(message):
    global last_processed_id
    if message.id <= last_processed_id:
        return
    last_processed_id = message.id

    text = (message.text or message.caption or "").lower().strip()
    if not text.startswith("/play") and not text.startswith("/stop"):
        return

    log(f"[INCOMING] Команда: {text}")

    if text.startswith("/play"):
        video_msg = None
        if message.video:
            video_msg = message
        elif message.reply_to_message and message.reply_to_message.video:
            video_msg = message.reply_to_message

        if not video_msg:
            await app.send_message(config.CHAT, "❌ Ответь на видео!")
            return

        status = await app.send_message(config.CHAT, "⏳ Скачиваю видео...")
        path = os.path.join(config.DOWNLOAD_DIR, f"v_{video_msg.id}.mp4")

        try:
            file_path = await app.download_media(video_msg.video, file_name=path)
            await status.edit("🚀 Запускаю трансляцию...")
            await calls.play(config.CHAT, MediaStream(file_path))
            await status.edit("✅ Трансляция запущена!")
        except Exception as e:
            log(f"[ERROR] {e}")
            await status.edit(f"🔴 Ошибка: {str(e)[:100]}")

    elif text.startswith("/stop"):
        try:
            await calls.leave_call(config.CHAT)
            await app.send_message(config.CHAT, "⏹ Остановлено.")
        except: pass

async def poll_history():
    log("[SYSTEM] Цикл опроса запущен.")
    while True:
        try:
            async for message in app.get_chat_history(config.CHAT, limit=5):
                await process_msg(message)
            await app.read_chat_history(config.CHAT)
        except Exception as e:
            log(f"[POLL ERROR] {e}")
        await asyncio.sleep(3)

async def main():
    global app, calls, last_processed_id
    apply_patches()
    
    log("--- ИНИЦИАЛИЗАЦИЯ ВНУТРИ LOOP ---")
    
    # СОЗДАЕМ ОБЪЕКТЫ ЗДЕСЬ, чтобы они привязались к текущему циклу событий
    app = Client(
        "railway_v9",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        session_string=config.SESSION_STRING,
        sleep_threshold=300
    )
    
    calls = PyTgCalls(app)

    try:
        await app.start()
        log("✅ Аккаунт подключен.")

        # Узнаем ID последнего сообщения перед стартом
        async for msg in app.get_chat_history(config.CHAT, limit=1):
            last_processed_id = msg.id

        await app.send_message(config.CHAT, "🤖 Бот (V9 Polling) запущен на Railway!")

        await calls.start()
        log("✅ Плеер запущен.")

        # Запускаем фоновый опрос
        asyncio.create_task(poll_history())
        
        log("--- СИСТЕМА ПОЛНОСТЬЮ ГОТОВА ---")
        await idle()
    except Exception as e:
        log(f"❌ Критическая ошибка: {e}")
        traceback.print_exc()
    finally:
        if app: await app.stop()

if __name__ == "__main__":
    # Используем стандартный asyncio.run для Python 3.12
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
