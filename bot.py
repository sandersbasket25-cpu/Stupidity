import os
import asyncio
import traceback
import sys
import pyrogram.errors
import pyrogram.raw.types
import pyrogram.raw.functions.phone as phone_funcs

def log(text):
    print(text, flush=True)

# --- УЛЬТРА-ПАТЧИ СОВМЕСТИМОСТИ (Senior Fix) ---
log("[SYSTEM] Применение патчей...")

# 1. Исправляем конструктор JoinGroupCall (удаляем лишний public_key)
# В Pyrogram это класс, поэтому мы патчим его конструктор
original_join_class = phone_funcs.JoinGroupCall
def patched_join_constructor(*args, **kwargs):
    kwargs.pop("public_key", None)
    return original_join_class(*args, **kwargs)
phone_funcs.JoinGroupCall = patched_join_constructor

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

# 3. Патчим Raw API типы
if not hasattr(pyrogram.raw.types, "InputGroupCallSlug"):
    setattr(pyrogram.raw.types, "InputGroupCallSlug", type("InputGroupCallSlug", (), {"ID": 0x0}))
if not hasattr(pyrogram.raw.types, "PhoneCallDiscardReasonMigrateConferenceCall"):
    setattr(pyrogram.raw.types, "PhoneCallDiscardReasonMigrateConferenceCall", type("PhoneCallDiscardReasonMigrateConferenceCall", (), {"ID": 0x0}))

log("[SYSTEM] Патчи применены.")
# -----------------------------------------------

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
            file_path = await app.download_media(video_msg.video, file_name=path)
            await status.edit("🚀 Запускаю трансляцию...")
            await calls.play(config.CHAT, MediaStream(file_path))
            await status.edit("✅ Трансляция активна!")
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
    
    app = Client(
        "railway_v12",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        session_string=config.SESSION_STRING
    )
    
    calls = PyTgCalls(app)

    try:
        await app.start()
        log("✅ Аккаунт подключен.")

        # --- КРИТИЧЕСКИЙ ШАГ: ПРОГРЕВ ПИРОВ ---
        log(f"Прогрев чата {config.CHAT}...")
        found = False
        async for dialog in app.get_dialogs(limit=100):
            if dialog.chat.id == config.CHAT:
                log(f"✅ Чат '{dialog.chat.title}' найден в диалогах и кеширован.")
                found = True
                break
        
        if not found:
            log("⚠️ Чат не найден в последних 100 диалогах. Пытаюсь получить напрямую...")
            await app.get_chat(config.CHAT)

        # Теперь get_chat_history не выдаст Peer id invalid
        async for msg in app.get_chat_history(config.CHAT, limit=1):
            last_processed_id = msg.id

        await app.send_message(config.CHAT, "🤖 Бот (V12) онлайн!")
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
