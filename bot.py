import asyncio
import logging
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from config import BOT_TOKEN, WEBHOOK_URL, PORT
from scheduler import PostScheduler
from web_server import create_web_app
from aiohttp import web
import threading

# Импорт хендлеров
from handlers.user import (
    start, help_command, guide_command, crm_command, menu_callback, camp_callback, schedule_callback,
    text_handler, photo_handler, video_handler, spintax_callback,
    skip_media, newcampaign_command, mycampaigns_command
)
from handlers.admin import (
    admin_panel, admin_callback_handler, add_here_command,
    set_admin_command, remove_admin_command, forward_handler, broadcast_message
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальный планировщик
scheduler = None

async def post_init(app: Application):
    global scheduler
    scheduler = PostScheduler(app.bot)
    asyncio.create_task(scheduler.run())
    logger.info("Планировщик запущен")

def main():
    # Явное создание event loop для Python 3.12+
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # --- Команды пользователя ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("guide", guide_command))
    application.add_handler(CommandHandler("newcampaign", newcampaign_command))
    application.add_handler(CommandHandler("mycampaigns", mycampaigns_command))
    application.add_handler(CommandHandler("crm", crm_command))

    # --- Команды администратора ---
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("addhere", add_here_command))
    application.add_handler(CommandHandler("setadmin", set_admin_command))
    application.add_handler(CommandHandler("removeadmin", remove_admin_command))

    # --- Callback'и ---
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_"))
    application.add_handler(CallbackQueryHandler(camp_callback, pattern="^camp_|^addsched_|^campstats_|^delcamp_"))
    application.add_handler(CallbackQueryHandler(schedule_callback, pattern="^schedcamp_|^schedgroup_|^day_|^days_"))
    application.add_handler(CallbackQueryHandler(spintax_callback, pattern="^spintax_"))
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^admin_|^rmgroup_|^menu_back$"))

    # --- Сообщения ---
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, photo_handler))
    application.add_handler(MessageHandler(filters.VIDEO & ~filters.COMMAND, video_handler))
    application.add_handler(MessageHandler(filters.FORWARDED & ~filters.COMMAND, forward_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # --- Запуск ---
    if WEBHOOK_URL:
        logger.info(f"Запуск в режиме Webhook: {WEBHOOK_URL}")
        # Создаём aiohttp приложение для веб-эндпоинтов
        web_app = create_web_app()

        # Добавляем webhook endpoint
        webhook_path = "/webhook"
        web_app.router.add_post(webhook_path, lambda request: handle_webhook(request, application))

        # Запускаем aiohttp сервер
        runner = web.AppRunner(web_app)
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        loop.run_until_complete(site.start())

        # Устанавливаем webhook в Telegram
        loop.run_until_complete(application.bot.set_webhook(f"{WEBHOOK_URL}{webhook_path}"))

        # Запускаем PTB
        loop.run_until_complete(application.initialize())
        loop.run_until_complete(application.start())

        logger.info(f"Сервер запущен на порту {PORT}")

        # Держим сервер активным
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.run_until_complete(application.stop())
            loop.run_until_complete(runner.cleanup())
    else:
        logger.info("Запуск в режиме Polling")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

async def handle_webhook(request, application):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response()

if __name__ == "__main__":
    main()
