"""Валидация Telegram Mini App initData (HMAC-SHA256, см. https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)."""
import hmac
import hashlib
import json
import urllib.parse
from config import BOT_TOKEN, is_admin


def validate_init_data(init_data: str) -> dict:
    """Возвращает {"user_id": int, "first_name": str, "is_admin": bool} или бросает ValueError."""
    if not init_data:
        raise ValueError("initData отсутствует")

    parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise ValueError("Отсутствует hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError("Неверная подпись initData")

    user_raw = parsed.get("user", "{}")
    user = json.loads(user_raw)
    user_id = int(user.get("id"))

    return {
        "user_id": user_id,
        "first_name": user.get("first_name", ""),
        "username": user.get("username", ""),
        "is_admin": is_admin(user_id),
    }
