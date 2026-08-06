import os
import asyncio
import traceback
import sys
import pyrogram.errors
import pyrogram.raw.types
from pyrogram import Client, filters, idle
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import config

def log(text):
    print(text, flush=True)

# --- ПАТЧИ СОВМЕСТИМОСТИ (ОБЯЗАТЕЛЬНО) ---
error_map = {"GroupcallForbidden": "GroupCallForbidden", "GroupcallInvalid": "GroupCallInvalid"}
for target, source in error_map.items():
    if not hasattr(pyrogram.errors, target):
        err = getattr(pyrogram.errors, source, type(target, (Exception,), {}))
        setattr(pyrogram.errors, target, err)
if not hasattr(pyrogram.raw.types, "InputGroupCallSlug"):
    setattr(pyrogram.raw.types, "InputGroupCallSlug", type("InputGroupCallSlug", (), {"ID": 0x0}))
if not hasattr(pyrogram.raw.types, "PhoneCallDiscardReasonMigrateConferenceCall"):
    setattr(pyrogram.raw.types, "PhoneCallDiscardReasonMigrateConferenceCall", type("PhoneCallDiscardReasonMigrateConferenceCall", (), {"ID": 0x0}))

# --- ИНИЦИАЛИЗАЦИЯ ---
app = Client(
    "railway_final_v8",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING
)

calls = PyTgCalls(app)
last_processed_id = 0  # Чтобы не обрабатывать одно и то же сообщение дважды

# Основная функция обработки сообщения
async def process_msg(message):
    global last_processed_id
    if message.id <= last_processed_id:
        return
    last_processed_id = message.id

    # Получаем текст из сообщения или подписи к видео
    text = (message.text or message.caption or "").lower().strip()
    
    if text.startswith("/play"):
        log(f"[ACTION] Команда /play от {message.from_user.id if message.from_user else 'User'}")
        
        # Проверяем видео в самом сообщении или в реплае
        video_msg = None
        if message.video:
            video_msg = message
        elif message.reply_to_message and message.reply_to_message.video:
            video_msg = message.reply_to_message

        if not video_msg:
            await app.send_message(config.CHAT, "❌ Нужно отправить /play ответом на видео или в описании к видео!")
            return

        status = await app.send_message(config.CHAT, "⏳ Начинаю загрузку видео...")
        path = os.path.join(config.DOWNLOAD_DIR, f"v_{video_msg.id}.mp4")

        try:
            file_path = await app.download_media(video_msg.video, file_name=path)
            log(f"[SUCCESS] Файл скачан: {file_path}")
            
            await status.edit("🚀 Запускаю трансляцию...")
            await calls.play(config.CHAT, MediaStream(file_path))
            await status.edit("✅ Трансляция запущена!")
            
        except Exception as e:
            log(f"[ERROR] {e}")
            await status.edit(f"🔴 Ошибка: {str(e)[:100]}")

    elif text.startswith("/stop"):
        try:
            await calls.leave_call(config.CHAT)
            await app.send_message(config.CHAT, "⏹ Трансляция остановлена.")
        except:
            pass

# Фоновая задача: принудительный опрос чата
async def poll_history():
    global last_processed_id
    log("[SYSTEM] Цикл опроса истории запущен.")
    
    # Сначала узнаем ID последнего сообщения, чтобы не спамить старым
    try:
        async for msg in app.get_chat_history(config.CHAT, limit=1):
            last_processed_id = msg.id
    except:
        pass

    while True:
        try:
            # Берем последние 3 сообщения
            async for message in app.get_chat_history(config.CHAT, limit=3):
                await process_msg(message)
            
            # Помечаем прочитанным (важно для стабильности)
            await app.read_chat_history(config.CHAT)
        except Exception as e:
            log(f"[POLL ERROR] {e}")
        
        await asyncio.sleep(3) # Проверка каждые 3 секунды

# Стандартный хендлер тоже оставляем (вдруг проснется)
@app.on_message(filters.chat(config.CHAT))
async def on_message_handler(client, message):
    await process_msg(message)

async def main():
    log("--- ЗАПУСК СИСТЕМЫ V8 (POLLING MODE) ---")
    try:
        await app.start()
        log("✅ Юзербот подключен.")

        # Синхронизация при старте
        async for dialog in app.get_dialogs(limit=10):
            if dialog.chat.id == config.CHAT:
                log(f"✅ Чат '{dialog.chat.title}' синхронизирован.")
                break
        
        await app.send_message(config.CHAT, "🤖 Бот на Railway в режиме Polling запущен!")

        await calls.start()
        
        # Запускаем фоновый опрос
        asyncio.create_task(poll_history())
        
        await idle()
    except Exception as e:
        log(f"❌ Критическая ошибка: {e}")
        traceback.print_exc()
    finally:
        try: await app.stop()
        except: pass

if __name__ == "__main__":
    asyncio.run(main())
