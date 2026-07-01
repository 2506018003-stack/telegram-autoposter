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

# Импорт хендлеров
from handlers.user import (
    start, help_command, guide_command, menu_callback, camp_callback, schedule_callback,
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
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # --- Команды пользователя ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("guide", guide_command))
    application.add_handler(CommandHandler("newcampaign", newcampaign_command))
    application.add_handler(CommandHandler("mycampaigns", mycampaigns_command))

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
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=WEBHOOK_URL,
        )
    else:
        logger.info("Запуск в режиме Polling")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
