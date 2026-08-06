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

# --- СИСТЕМНЫЕ ПАТЧИ (БЕЗ ИЗМЕНЕНИЙ) ---
def apply_patches():
    error_map = {"GroupcallForbidden": "GroupCallForbidden", "GroupcallInvalid": "GroupCallInvalid"}
    for target, source in error_map.items():
        if not hasattr(pyrogram.errors, target):
            err = getattr(pyrogram.errors, source, type(target, (Exception,), {}))
            setattr(pyrogram.errors, target, err)
    missing_types = ["InputGroupCallSlug", "PhoneCallDiscardReasonMigrateConferenceCall"]
    for t in missing_types:
        if not hasattr(pyrogram.raw.types, t):
            setattr(pyrogram.raw.types, t, type(t, (), {"ID": 0x0}))
    print("[SYSTEM] Патчи применены.", flush=True)

def log(text):
    print(text, flush=True)

app = None
calls = None
last_processed_id = 0

async def process_msg(message):
    global last_processed_id
    if message.id <= last_processed_id:
        return
    
    last_processed_id = message.id
    text = (message.text or message.caption or "").lower().strip()
    
    log(f"[POLL] Вижу сообщение ID {message.id}: {text[:20]}...")

    if text.startswith("/play"):
        video_msg = None
        if message.video:
            video_msg = message
        elif message.reply_to_message and message.reply_to_message.video:
            video_msg = message.reply_to_message

        if not video_msg:
            await app.send_message(config.CHAT, "❌ Ответь на видео!")
            return

        status = await app.send_message(config.CHAT, "⏳ Качаю видео...")
        path = os.path.join(config.DOWNLOAD_DIR, f"v_{video_msg.id}.mp4")

        try:
            file_path = await app.download_media(video_msg.video, file_name=path)
            await status.edit("🚀 Запускаю трансляцию...")
            await calls.play(config.CHAT, MediaStream(file_path))
            await status.edit("✅ Видео запущено!")
        except Exception as e:
            log(f"[ERROR] {e}")
            await status.edit(f"🔴 Ошибка: {str(e)[:100]}")

    elif text.startswith("/stop"):
        try:
            await calls.leave_call(config.CHAT)
            await app.send_message(config.CHAT, "⏹ Остановлено.")
        except: pass

async def poll_history():
    global last_processed_id
    log("[SYSTEM] Цикл опроса истории активирован.")
    
    # "Разогрев" - узнаем текущий последний ID
    try:
        async for msg in app.get_chat_history(config.CHAT, limit=1):
            last_processed_id = msg.id
            log(f"[SYSTEM] Начальный ID сообщения: {last_processed_id}")
    except Exception as e:
        log(f"[SYSTEM ERROR] Не удалось получить историю: {e}")

    while True:
        try:
            # Каждые 2 секунды проверяем последние 5 сообщений
            # log("[HEARTBEAT] Опрашиваю...") # Раскомментируй, если хочешь видеть "пульс"
            async for message in app.get_chat_history(config.CHAT, limit=5):
                await process_msg(message)
            
            # Помечаем всё как прочитанное, чтобы Telegram "освежил" поток
            await app.read_chat_history(config.CHAT)
        except Exception as e:
            log(f"[POLL ERROR] {e}")
        
        await asyncio.sleep(2)

async def main():
    global app, calls
    apply_patches()
    
    app = Client(
        "railway_v10", # Обновили имя сессии
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        session_string=config.SESSION_STRING,
        sleep_threshold=300
    )
    
    calls = PyTgCalls(app)

    try:
        log("Шаг 1: Запуск клиента...")
        await app.start()
        
        log("Шаг 2: Синхронизация...")
        # Пройдемся по диалогам, чтобы "зацепить" чат
        async for dialog in app.get_dialogs(limit=10):
            if dialog.chat.id == config.CHAT:
                log(f"✅ Чат '{dialog.chat.title}' найден.")

        await app.send_message(config.CHAT, "🤖 Бот (V10 Turbo) запущен!")
        
        log("Шаг 3: Запуск плеера...")
        await calls.start()
        
        # Запускаем бесконечный опрос
        asyncio.create_task(poll_history())
        
        log("--- БОТ ГОТОВ К ПРИЕМУ КОМАНД ---")
        await idle()
    except Exception as e:
        log(f"❌ Критическая ошибка: {e}")
        traceback.print_exc()
    finally:
        if app: await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
