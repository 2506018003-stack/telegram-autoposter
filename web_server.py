from aiohttp import web
from datetime import datetime, timezone
import json

async def health_handler(request):
    return web.json_response({
        "status": "ok",
        "service": "telegram-autoposter",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

async def root_handler(request):
    return web.json_response({
        "message": "SMMPilot — Автопостинг в Telegram",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "webhook": "/webhook"
        }
    })

def create_web_app():
    app = web.Application()
    app.router.add_get("/", root_handler)
    app.router.add_get("/health", health_handler)
    return app
