import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = list(map(int, filter(None, os.getenv("ADMIN_IDS", "").split(","))))
REDIS_URL = os.getenv("REDIS_URL", "")
UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT = int(os.getenv("PORT", "10000"))
# По умолчанию Mini App живёт на том же сервисе, на /miniapp
MINIAPP_URL = os.getenv("MINIAPP_URL", f"{WEBHOOK_URL}/miniapp" if WEBHOOK_URL else "")

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
