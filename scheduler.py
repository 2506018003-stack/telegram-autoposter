import asyncio
import spintax
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
from database import db

class PostScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.running = False

    def spin_text(self, text: str) -> str:
        try:
            return spintax.spin(text)
        except Exception:
            return text

    async def check_and_post(self):
        now = datetime.now()
        current_day = now.strftime("%a").lower()[:3]  # mon, tue, wed...
        current_time = now.strftime("%H:%M")

        schedules = db.get_all_schedules()
        for sched in schedules:
            if sched.get("status") != "active":
                continue
            days = sched.get("days", "").split(",")
            time_str = sched.get("time", "")
            if current_day not in days or time_str != current_time:
                continue

            # Проверяем, не постили ли уже в эту минуту
            last_key = f"last_post:{sched['schedule_id']}:{current_time}"
            if db.r.exists(last_key):
                continue
            db.r.setex(last_key, 60, "1")

            campaign = db.get_campaign(sched.get("campaign_id", ""))
            if not campaign:
                continue

            chat_id = int(sched.get("chat_id", 0))
            text = campaign.get("text", "")
            if campaign.get("spintax_enabled") == "1":
                text = self.spin_text(text)

            media_type = campaign.get("media_type", "")
            media_file_id = campaign.get("media_file_id", "")

            try:
                if media_type == "photo" and media_file_id:
                    msg = await self.bot.send_photo(chat_id=chat_id, photo=media_file_id, caption=text)
                elif media_type == "video" and media_file_id:
                    msg = await self.bot.send_video(chat_id=chat_id, video=media_file_id, caption=text)
                else:
                    msg = await self.bot.send_message(chat_id=chat_id, text=text)
                db.log_post(campaign["campaign_id"], chat_id, "success", msg.message_id)
            except TelegramError as e:
                db.log_post(campaign["campaign_id"], chat_id, "failed")
                print(f"Ошибка отправки в {chat_id}: {e}")

    async def run(self):
        self.running = True
        while self.running:
            await self.check_and_post()
            await asyncio.sleep(30)  # Проверка каждые 30 секунд

    def stop(self):
        self.running = False
