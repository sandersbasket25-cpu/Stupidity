import os
import asyncio
import traceback
import sys
import pyrogram.errors
import pyrogram.raw.types
import pyrogram.raw.functions.phone as phone_funcs

def log(text):
    print(text, flush=True)

# --- ПАТЧИ (БЕЗ ИЗМЕНЕНИЙ, РАБОТАЮТ) ---
original_join_class = phone_funcs.JoinGroupCall
def patched_join_constructor(*args, **kwargs):
    kwargs.pop("public_key", None)
    return original_join_class(*args, **kwargs)
phone_funcs.JoinGroupCall = patched_join_constructor

error_map = {"GroupcallForbidden": "GroupCallForbidden", "GroupcallInvalid": "GroupCallInvalid", "GroupcallAlreadyJoined": "GroupCallAlreadyJoined"}
for target, source in error_map.items():
    if not hasattr(pyrogram.errors, target):
        err = getattr(pyrogram.errors, source, type(target, (Exception,), {}))
        setattr(pyrogram.errors, target, err)

if not hasattr(pyrogram.raw.types, "InputGroupCallSlug"):
    setattr(pyrogram.raw.types, "InputGroupCallSlug", type("InputGroupCallSlug", (), {"ID": 0x0}))
if not hasattr(pyrogram.raw.types, "PhoneCallDiscardReasonMigrateConferenceCall"):
    setattr(pyrogram.raw.types, "PhoneCallDiscardReasonMigrateConferenceCall", type("PhoneCallDiscardReasonMigrateConferenceCall", (), {"ID": 0x0}))
# ---------------------------------------

from pyrogram import Client, idle
from pytgcalls import PyTgCalls, filters as pytg_filters # Добавили фильтры для событий
from pytgcalls.types import MediaStream
import config

app = None
calls = None
last_processed_id = 0
current_file = None # Переменная для отслеживания текущего файла

async def process_msg(message):
    global last_processed_id, current_file
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
            await app.send_message(config.CHAT, "❌ Ответь на видео этой командой!")
            return

        status = await app.send_message(config.CHAT, "⏳ Скачиваю видео...")
        path = os.path.join(config.DOWNLOAD_DIR, f"v_{video_msg.id}.mp4")

        try:
            current_file = await app.download_media(video_msg.video, file_name=path)
            await status.edit("🚀 Запускаю трансляцию...")
            await calls.play(config.CHAT, MediaStream(current_file))
            await status.edit("✅ Трансляция активна!")
        except Exception as e:
            log(f"[ERROR] {e}")
            await status.edit(f"🔴 Ошибка: {str(e)[:100]}")

    elif text.startswith("/stop"):
        try:
            await calls.leave_call(config.CHAT)
            await app.send_message(config.CHAT, "⏹ Остановлено.")
        except: pass

# --- НОВЫЙ БЛОК: АВТО-ВЫХОД ---
async def setup_event_handlers():
    @calls.on_update()
    async def on_update(client, update):
        global current_file
        # Проверяем, является ли событие окончанием стрима
        if pytg_filters.stream_end(update):
            log("[EVENT] Видео закончилось. Выхожу из чата...")
            try:
                await calls.leave_call(config.CHAT)
                if current_file and os.path.exists(current_file):
                    os.remove(current_file)
                    log(f"[CLEANUP] Файл {current_file} удален.")
                    current_file = None
            except Exception as e:
                log(f"[EVENT ERROR] {e}")

async def poll_history():
    global last_processed_id
    log("[SYSTEM] Опрос истории запущен.")
    while True:
        try:
            async for message in app.get_chat_history(config.CHAT, limit=5):
                await process_msg(message)
            await app.read_chat_history(config.CHAT)
        except Exception as e:
            log(f"[POLL ERROR] {e}")
        await asyncio.sleep(4)

async def main():
    global app, calls, last_processed_id
    
    app = Client("railway_v13", api_id=config.API_ID, api_hash=config.API_HASH, session_string=config.SESSION_STRING)
    calls = PyTgCalls(app)

    try:
        await app.start()
        log("✅ Аккаунт подключен.")

        # Прогрев чата
        async for dialog in app.get_dialogs(limit=100):
            if dialog.chat.id == config.CHAT:
                log(f"✅ Чат '{dialog.chat.title}' синхронизирован.")
                break
        
        async for msg in app.get_chat_history(config.CHAT, limit=1):
            last_processed_id = msg.id

        await app.send_message(config.CHAT, "🤖 Бот (V13 Авто-выход) онлайн!")
        
        # Настраиваем обработчик событий
        await setup_event_handlers()
        
        await calls.start()
        log("✅ Плеер запущен.")
        
        asyncio.create_task(poll_history())
        await idle()
    except Exception as e:
        log(f"❌ Критическая ошибка: {e}")
        traceback.print_exc()
    finally:
        if app: await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
