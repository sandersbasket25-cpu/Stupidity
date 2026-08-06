import os
import asyncio
import traceback
import sys
import pyrogram.errors
import pyrogram.raw.types

def log(text):
    print(text, flush=True)

# --- ПАТЧИ СОВМЕСТИМОСТИ (ОСТАВЛЯЕМ) ---
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
    "railway_session_v4",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING
)

calls = PyTgCalls(app)

# ОБРАБОТЧИК КОМАНД
@app.on_message(filters.chat(config.CHAT) & filters.command(["play", "stop", "pause", "resume"]))
async def command_handler(client, message):
    # Команды принимает от админов или от самого себя
    if not message.from_user: return
    if message.from_user.id not in config.ADMINS and not message.from_user.is_self:
        return

    cmd = message.command[0].lower()
    log(f"[ACTION] Команда {cmd} получена!")

    if cmd == "play":
        if not message.reply_to_message or not message.reply_to_message.video:
            return await message.reply("❌ Ответь на видео!")

        status = await message.reply("⏳ Загрузка видео...")
        path = os.path.join(config.DOWNLOAD_DIR, f"v_{message.id}.mp4")
        try:
            file_path = await client.download_media(message.reply_to_message, file_name=path)
            await status.edit("🚀 Видео скачано. Запускаю трансляцию...")
            await calls.play(config.CHAT, MediaStream(file_path))
            await status.edit("✅ Видео играет!")
        except Exception as e:
            log(f"[ERROR] {e}")
            await status.edit(f"🔴 Ошибка: {e}")

    elif cmd == "stop":
        await calls.leave_call(config.CHAT)
        await message.reply("⏹ Остановлено.")

async def main():
    log("--- СИСТЕМА ЗАПУСКАЕТСЯ ---")
    try:
        await app.start()
        log("✅ Аккаунт подключен.")

        # --- КРИТИЧЕСКИЙ ШАГ: ПОИСК ЧАТА В ДИАЛОГАХ ---
        log(f"Ищу чат {config.CHAT} в списке диалогов...")
        target_chat = None
        async for dialog in app.get_dialogs(limit=50):
            if dialog.chat.id == config.CHAT:
                target_chat = dialog.chat
                break
        
        if target_chat:
            log(f"✅ Чат '{target_chat.title}' найден и синхронизирован!")
            try:
                await app.send_message(config.CHAT, "🤖 Бот на Railway успешно нашел чат и готов к работе!")
            except Exception as e:
                log(f"⚠️ Чат найден, но отправить сообщение не удалось: {e}")
        else:
            log("❌ ЧАТ НЕ НАЙДЕН!")
            log("Юзербот (Krasavitsa) должен быть участником группы!")
            # Выведем список чатов, чтобы понять, что он вообще видит
            log("Список чатов, которые я вижу:")
            async for dialog in app.get_dialogs(limit=10):
                log(f" - [{dialog.chat.id}] {dialog.chat.title or 'Личка'}")
            return # Останавливаем запуск, если чата нет

        await calls.start()
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
