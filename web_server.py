from aiohttp import web
import json

async def health_handler(request):
    return web.json_response({
        "status": "ok",
        "service": "telegram-autoposter",
        "timestamp": "2026-07-01"
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
