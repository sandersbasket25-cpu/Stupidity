import os
import asyncio
import traceback
import sys
import pyrogram.errors
import pyrogram.raw.types

def log(text):
    print(text, flush=True)

# --- ПАТЧИ (БЕЗ ИЗМЕНЕНИЙ) ---
error_map = {"GroupcallForbidden": "GroupCallForbidden", "GroupcallInvalid": "GroupCallInvalid"}
for target, source in error_map.items():
    if not hasattr(pyrogram.errors, target):
        err = getattr(pyrogram.errors, source, type(target, (Exception,), {}))
        setattr(pyrogram.errors, target, err)
if not hasattr(pyrogram.raw.types, "InputGroupCallSlug"):
    setattr(pyrogram.raw.types, "InputGroupCallSlug", type("InputGroupCallSlug", (), {"ID": 0x0}))
if not hasattr(pyrogram.raw.types, "PhoneCallDiscardReasonMigrateConferenceCall"):
    setattr(pyrogram.raw.types, "PhoneCallDiscardReasonMigrateConferenceCall", type("PhoneCallDiscardReasonMigrateConferenceCall", (), {"ID": 0x0}))

from pyrogram import Client, filters, idle
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import config

app = Client(
    "railway_session_v3", # Новое имя сессии для чистоты
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING,
    sleep_threshold=600
)

calls = PyTgCalls(app)

# 1. МОНИТОРИНГ ВСЕХ СООБЩЕНИЙ (Для отладки)
@app.on_message(filters.chat(config.CHAT))
async def monitor_all(client, message):
    user_info = message.from_user.id if message.from_user else "System"
    log(f"[DEBUG] Новое сообщение в группе от {user_info}: {message.text or '[Медиа]'}")

# 2. ОБРАБОТКА КОМАНД
@app.on_message(filters.chat(config.CHAT) & filters.command(["play", "stop", "pause", "resume"]))
async def command_handler(client, message):
    if not message.from_user: return
    # Проверяем админа или самого себя (filters.me)
    is_admin = message.from_user.id in config.ADMINS or message.from_user.is_self
    if not is_admin: return

    cmd = message.command[0].lower()
    log(f"[ACTION] Команда {cmd} принята!")

    if cmd == "play":
        if not message.reply_to_message or not message.reply_to_message.video:
            return await message.reply("❌ Ответь на видео!")

        status = await message.reply("⏳ Railway скачивает видео...")
        path = os.path.join(config.DOWNLOAD_DIR, f"v_{message.id}.mp4")
        try:
            file_path = await client.download_media(message.reply_to_message.video, file_name=path)
            log(f"[FILE] Скачано: {file_path}")
            await status.edit("🚀 Видео загружено. Запускаю поток...")
            await calls.play(config.CHAT, MediaStream(file_path))
            await status.edit("✅ Трансляция запущена!")
        except Exception as e:
            log(f"[ERROR] {e}")
            await status.edit(f"🔴 Ошибка: {str(e)[:100]}")

    elif cmd == "stop":
        await calls.leave_call(config.CHAT)
        await message.reply("⏹ Остановлено.")

async def main():
    log("--- ЗАПУСК СИСТЕМЫ ---")
    try:
        await app.start()
        log("✅ Аккаунт подключен.")
        
        # Пытаемся "пробудить" сессию
        log("Шаг: Отправка тестового сообщения в группу...")
        try:
            test_msg = await app.send_message(config.CHAT, "🤖 Видео-бот на Railway запущен и слушает команды!")
            log(f"✅ Тестовое сообщение отправлено! (ID: {test_msg.id})")
        except Exception as e:
            log(f"⚠️ Не удалось отправить сообщение в группу: {e}")

        await calls.start()
        log(f"✅ Плеер активен в чате {config.CHAT}")
        
        log("--- ВСЁ ГОТОВО. ЖДУ КОМАНД ---")
        await idle()
    except Exception as e:
        log(f"❌ Критическая ошибка: {e}")
        traceback.print_exc()
    finally:
        try: await app.stop()
        except: pass

if __name__ == "__main__":
    asyncio.run(main())
