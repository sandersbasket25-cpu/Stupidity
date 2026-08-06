import os
import asyncio
import traceback
import sys
import pyrogram.errors
import pyrogram.raw.types

def log(text):
    print(text, flush=True)

# --- ПАТЧИ (ОСТАВЛЯЕМ) ---
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
    "railway_session_v5", # Новая сессия для сброса кеша обновлений
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING
)

calls = PyTgCalls(app)

# ОБРАБОТЧИК: Ловим ВСЁ в этом чате
@app.on_message(filters.chat(config.CHAT))
async def global_handler(client, message):
    # Логируем в консоль Railway каждое сообщение, которое видит бот
    user_id = message.from_user.id if message.from_user else "System/Unknown"
    text = message.text or ""
    log(f"[RAW LOG] Сообщение от {user_id}: {text}")

    # Ручной разбор команд
    if text.startswith("/play"):
        log(f"[CHECK] Команда /play замечена!")
        
        # Проверка прав (админ или сам юзербот)
        is_admin = (message.from_user and message.from_user.id in config.ADMINS) or (message.from_user and message.from_user.is_self)
        if not is_admin:
            log(f"[CHECK] Отказано: юзер {user_id} не админ")
            return

        if not message.reply_to_message or not message.reply_to_message.video:
            await message.reply("❌ Ответь на видео!")
            return

        status = await message.reply("⏳ Загрузка видео...")
        path = os.path.join(config.DOWNLOAD_DIR, f"v_{message.id}.mp4")
        try:
            # Используем message.reply_to_message напрямую для скачивания
            file_path = await client.download_media(message.reply_to_message, file_name=path)
            log(f"[FILE] Скачано: {file_path}")
            await status.edit("🚀 Видео загружено. Запускаю поток...")
            
            await calls.play(config.CHAT, MediaStream(file_path))
            await status.edit("✅ Трансляция запущена!")
        except Exception as e:
            log(f"[ERROR] {e}")
            await status.edit(f"🔴 Ошибка: {e}")

    elif text.startswith("/stop"):
        if (message.from_user and message.from_user.id in config.ADMINS) or (message.from_user and message.from_user.is_self):
            await calls.leave_call(config.CHAT)
            await message.reply("⏹ Остановлено.")

async def main():
    log("--- ЗАПУСК СИСТЕМЫ ---")
    try:
        await app.start()
        log("✅ Аккаунт подключен.")

        # Синхронизация чата
        log(f"Синхронизация чата {config.CHAT}...")
        async for dialog in app.get_dialogs(limit=20):
            if dialog.chat.id == config.CHAT:
                log(f"✅ Чат '{dialog.chat.title}' синхронизирован.")
                break
        
        await app.send_message(config.CHAT, "🤖 Бот онлайн и слушает КАЖДОЕ сообщение.")

        await calls.start()
        log("--- ВСЁ ГОТОВО. ЖДУ СООБЩЕНИЙ В ГРУППЕ ---")
        await idle()
    except Exception as e:
        log(f"❌ Ошибка: {e}")
        traceback.print_exc()
    finally:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
