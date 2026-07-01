import redis
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
import urllib.parse
from config import REDIS_URL

class Database:
    def __init__(self):
        if REDIS_URL.startswith("rediss://"):
            parsed = urllib.parse.urlparse(REDIS_URL)
            self.r = redis.Redis(
                host=parsed.hostname,
                port=parsed.port or 6379,
                password=parsed.password,
                username=parsed.username or "default",
                ssl=True,
                ssl_cert_reqs=None,
                decode_responses=True
            )
        else:
            self.r = redis.from_url(REDIS_URL, decode_responses=True)

    # ---------- Users ----------
    def add_user(self, user_id: int, username: str, first_name: str):
        key = f"user:{user_id}"
        if not self.r.exists(key):
            self.r.hset(key, mapping={
                "user_id": user_id,
                "username": username or "",
                "first_name": first_name or "",
                "joined_at": datetime.now().isoformat(),
                "is_admin": "0"
            })

    def get_user(self, user_id: int) -> Optional[Dict[str, str]]:
        data = self.r.hgetall(f"user:{user_id}")
        return data if data else None

    def set_admin(self, user_id: int, status: bool = True):
        self.r.hset(f"user:{user_id}", "is_admin", "1" if status else "0")

    def is_admin(self, user_id: int) -> bool:
        val = self.r.hget(f"user:{user_id}", "is_admin")
        return val == "1" or user_id in [int(x) for x in __import__("config").ADMIN_IDS]

    def get_all_users(self) -> List[Dict[str, str]]:
        keys = self.r.keys("user:*")
        return [self.r.hgetall(k) for k in keys]

    # ---------- Groups ----------
    def add_group(self, chat_id: int, title: str, username: str, chat_type: str, added_by: int):
        key = f"group:{chat_id}"
        self.r.hset(key, mapping={
            "chat_id": chat_id,
            "title": title or "",
            "username": username or "",
            "type": chat_type,
            "added_by": added_by,
            "added_at": datetime.now().isoformat()
        })

    def remove_group(self, chat_id: int):
        self.r.delete(f"group:{chat_id}")

    def get_group(self, chat_id: int) -> Optional[Dict[str, str]]:
        return self.r.hgetall(f"group:{chat_id}") or None

    def get_all_groups(self) -> List[Dict[str, str]]:
        keys = self.r.keys("group:*")
        return [self.r.hgetall(k) for k in keys]

    # ---------- Campaigns ----------
    def create_campaign(self, owner_id: int, name: str, text: str, 
                        media_type: str = "", media_file_id: str = "",
                        spintax_enabled: bool = False) -> str:
        cid = str(uuid.uuid4())[:8]
        key = f"campaign:{cid}"
        self.r.hset(key, mapping={
            "campaign_id": cid,
            "owner_id": owner_id,
            "name": name,
            "text": text,
            "media_type": media_type,
            "media_file_id": media_file_id,
            "spintax_enabled": "1" if spintax_enabled else "0",
            "created_at": datetime.now().isoformat(),
            "status": "active"
        })
        self.r.sadd(f"user_campaigns:{owner_id}", cid)
        return cid

    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, str]]:
        return self.r.hgetall(f"campaign:{campaign_id}") or None

    def get_user_campaigns(self, user_id: int) -> List[Dict[str, str]]:
        cids = self.r.smembers(f"user_campaigns:{user_id}")
        campaigns = []
        for cid in cids:
            camp = self.r.hgetall(f"campaign:{cid}")
            if camp:
                campaigns.append(camp)
        return campaigns

    def get_all_campaigns(self) -> List[Dict[str, str]]:
        keys = self.r.keys("campaign:*")
        return [self.r.hgetall(k) for k in keys]

    def delete_campaign(self, campaign_id: str):
        camp = self.get_campaign(campaign_id)
        if camp:
            self.r.srem(f"user_campaigns:{camp['owner_id']}", campaign_id)
        self.r.delete(f"campaign:{campaign_id}")

    # ---------- Schedule ----------
    def add_schedule(self, campaign_id: str, chat_id: int, 
                     days: str, time_str: str, timezone: str = "UTC") -> str:
        sid = str(uuid.uuid4())[:8]
        key = f"schedule:{sid}"
        self.r.hset(key, mapping={
            "schedule_id": sid,
            "campaign_id": campaign_id,
            "chat_id": chat_id,
            "days": days,  # например "mon,wed,fri"
            "time": time_str,  # "14:30"
            "timezone": timezone,
            "status": "active",
            "created_at": datetime.now().isoformat()
        })
        self.r.sadd(f"campaign_schedules:{campaign_id}", sid)
        return sid

    def get_schedule(self, schedule_id: str) -> Optional[Dict[str, str]]:
        return self.r.hgetall(f"schedule:{schedule_id}") or None

    def get_all_schedules(self) -> List[Dict[str, str]]:
        keys = self.r.keys("schedule:*")
        return [self.r.hgetall(k) for k in keys]

    def get_campaign_schedules(self, campaign_id: str) -> List[Dict[str, str]]:
        sids = self.r.smembers(f"campaign_schedules:{campaign_id}")
        return [self.r.hgetall(f"schedule:{sid}") for sid in sids if self.r.exists(f"schedule:{sid}")]

    def delete_schedule(self, schedule_id: str):
        sched = self.get_schedule(schedule_id)
        if sched:
            self.r.srem(f"campaign_schedules:{sched['campaign_id']}", schedule_id)
        self.r.delete(f"schedule:{schedule_id}")

    # ---------- Stats ----------
    def log_post(self, campaign_id: str, chat_id: int, status: str, message_id: int = 0):
        date = datetime.now().strftime("%Y-%m-%d")
        key = f"stats:{campaign_id}:{chat_id}:{date}"
        self.r.hincrby(key, "total", 1)
        self.r.hincrby(key, status, 1)
        if message_id:
            self.r.hset(key, "last_message_id", message_id)
        self.r.expire(key, 60*60*24*90)  # 90 дней

    def get_stats(self, campaign_id: str) -> Dict[str, Any]:
        keys = self.r.keys(f"stats:{campaign_id}:*")
        total = 0
        success = 0
        failed = 0
        for k in keys:
            data = self.r.hgetall(k)
            total += int(data.get("total", 0))
            success += int(data.get("success", 0))
            failed += int(data.get("failed", 0))
        return {"total": total, "success": success, "failed": failed}

    def get_all_stats(self) -> Dict[str, Any]:
        keys = self.r.keys("stats:*")
        total = 0
        success = 0
        for k in keys:
            data = self.r.hgetall(k)
            total += int(data.get("total", 0))
            success += int(data.get("success", 0))
        return {"total_posts": total, "successful": success}

db = Database()
