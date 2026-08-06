import os
import asyncio
import traceback
import sys
import pyrogram.errors
import pyrogram.raw.types
import pyrogram.raw.functions.phone as phone_funcs

# --- ХИРУРГИЧЕСКИЙ ПАТЧ (Senior Hotfix) ---
def apply_ultra_patches():
    log("[SYSTEM] Применение патчей совместимости...")
    
    # 1. Исправляем конструктор JoinGroupCall (лечит ошибку с public_key)
    original_join = phone_funcs.JoinGroupCall
    def patched_join_group_call(*args, **kwargs):
        # Удаляем public_key, если он прилетел из ntgcalls
        kwargs.pop("public_key", None)
        return original_chat_join(*args, **kwargs) if 'original_chat_join' in globals() else original_join(*args, **kwargs)
    
    phone_funcs.JoinGroupCall = patched_join_group_call

    # 2. Патчим отсутствующие классы ошибок
    error_map = {
        "GroupcallForbidden": "GroupCallForbidden", 
        "GroupcallInvalid": "GroupCallInvalid",
        "GroupcallAlreadyJoined": "GroupCallAlreadyJoined"
    }
    for target, source in error_map.items():
        if not hasattr(pyrogram.errors, target):
            err = getattr(pyrogram.errors, source, type(target, (Exception,), {}))
            setattr(pyrogram.errors, target, err)

    # 3. Патчим отсутствующие типы Raw API
    missing_types = ["InputGroupCallSlug", "PhoneCallDiscardReasonMigrateConferenceCall"]
    for t in missing_types:
        if not hasattr(pyrogram.raw.types, t):
            setattr(pyrogram.raw.types, t, type(t, (), {"ID": 0x0}))
    
    log("[SYSTEM] Патчи применены успешно.")

def log(text):
    print(text, flush=True)

# ----------------------------------------

from pyrogram import Client, idle
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import config

app = None
calls = None
last_processed_id = 0

async def process_msg(message):
    global last_processed_id
    if message.id <= last_processed_id:
        return
    
    last_processed_id = message.id
    text = (message.text or message.caption or "").lower().strip()
    
    # Мы убрали фильтр админов, ловим всё
    if text.startswith("/play"):
        log(f"[POLL] Команда /play от {message.from_user.id if message.from_user else 'User'}")
        
        video_msg = None
        if message.video:
            video_msg = message
        elif message.reply_to_message and message.reply_to_message.video:
            video_msg = message.reply_to_message

        if not video_msg:
            await app.send_message(config.CHAT, "❌ Ответь на видео этой командой!")
            return

        status = await app.send_message(config.CHAT, "⏳ Качаю видео на Railway...")
        path = os.path.join(config.DOWNLOAD_DIR, f"v_{video_msg.id}.mp4")

        try:
            file_path = await app.download_media(video_msg.video, file_name=path)
            await status.edit("🚀 Запускаю трансляцию...")
            
            # В v2.x API py-tgcalls
            await calls.play(config.CHAT, MediaStream(file_path))
            await status.edit("✅ Трансляция запущена!")
            
        except Exception as e:
            err = traceback.format_exc()
            log(f"[ERROR] {err}")
            await status.edit(f"🔴 Ошибка: {str(e)[:100]}")

    elif text.startswith("/stop"):
        try:
            await calls.leave_call(config.CHAT)
            await app.send_message(config.CHAT, "⏹ Остановлено.")
        except: pass

async def poll_history():
    global last_processed_id
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
    apply_ultra_patches()
    
    app = Client(
        "railway_v11",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        session_string=config.SESSION_STRING,
        sleep_threshold=300
    )
    
    calls = PyTgCalls(app)

    try:
        await app.start()
        log("✅ Аккаунт подключен.")

        async for msg in app.get_chat_history(config.CHAT, limit=1):
            last_processed_id = msg.id

        await app.send_message(config.CHAT, "🤖 Бот (V11 Fixed) запущен!")
        await calls.start()
        
        asyncio.create_task(poll_history())
        await idle()
    except Exception as e:
        log(f"❌ Критическая ошибка: {e}")
        traceback.print_exc()
    finally:
        if app: await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
