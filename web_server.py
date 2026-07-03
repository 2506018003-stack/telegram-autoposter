from aiohttp import web
from datetime import datetime, timezone
import json
import os

from database import db
from webapp_auth import validate_init_data

MINIAPP_INDEX = os.path.join(os.path.dirname(__file__), "miniapp", "index.html")

async def miniapp_index_handler(request):
    return web.FileResponse(MINIAPP_INDEX)

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
            "webhook": "/webhook",
            "miniapp": "/miniapp"
        }
    })


def _authenticate(request):
    """Достаёт и валидирует Telegram initData из заголовка X-Init-Data."""
    init_data = request.headers.get("X-Init-Data", "")
    try:
        return validate_init_data(init_data)
    except ValueError as e:
        raise web.HTTPForbidden(text=json.dumps({"error": str(e)}), content_type="application/json")


async def api_me(request):
    auth = _authenticate(request)
    return web.json_response(auth)


async def api_campaigns_list(request):
    auth = _authenticate(request)
    show_all = auth["is_admin"] and request.query.get("all") == "1"
    campaigns = db.get_all_campaigns() if show_all else db.get_user_campaigns(auth["user_id"])
    for c in campaigns:
        c["schedules"] = db.get_campaign_schedules(c["campaign_id"])
    return web.json_response(campaigns)


async def api_campaigns_create(request):
    auth = _authenticate(request)
    body = await request.json()
    name = (body.get("name") or "").strip()
    text = (body.get("text") or "").strip()
    if not name or not text:
        raise web.HTTPBadRequest(text=json.dumps({"error": "name и text обязательны"}), content_type="application/json")
    cid = db.create_campaign(
        owner_id=auth["user_id"],
        name=name,
        text=text,
        spintax_enabled=bool(body.get("spintax_enabled", False))
    )
    return web.json_response({"campaign_id": cid})


async def api_campaign_delete(request):
    auth = _authenticate(request)
    cid = request.match_info["id"]
    campaign = db.get_campaign(cid)
    if not campaign:
        raise web.HTTPNotFound()
    if not auth["is_admin"] and int(campaign.get("owner_id", 0)) != auth["user_id"]:
        raise web.HTTPForbidden()
    db.delete_campaign(cid)
    return web.json_response({"ok": True})


async def api_schedule_create(request):
    auth = _authenticate(request)
    cid = request.match_info["id"]
    campaign = db.get_campaign(cid)
    if not campaign:
        raise web.HTTPNotFound()
    if not auth["is_admin"] and int(campaign.get("owner_id", 0)) != auth["user_id"]:
        raise web.HTTPForbidden()
    body = await request.json()
    days = body.get("days") or []
    time_str = body.get("time") or ""
    chat_id = body.get("chat_id")
    if not days or not time_str or chat_id is None:
        raise web.HTTPBadRequest(text=json.dumps({"error": "chat_id, days и time обязательны"}), content_type="application/json")
    sid = db.add_schedule(cid, int(chat_id), ",".join(days), time_str)
    return web.json_response({"schedule_id": sid})


async def api_schedule_delete(request):
    auth = _authenticate(request)
    sid = request.match_info["id"]
    sched = db.get_schedule(sid)
    if not sched:
        raise web.HTTPNotFound()
    campaign = db.get_campaign(sched.get("campaign_id", ""))
    if campaign and not auth["is_admin"] and int(campaign.get("owner_id", 0)) != auth["user_id"]:
        raise web.HTTPForbidden()
    db.delete_schedule(sid)
    return web.json_response({"ok": True})


async def api_groups_list(request):
    _authenticate(request)
    return web.json_response(db.get_all_groups())


async def api_stats(request):
    auth = _authenticate(request)
    if auth["is_admin"] and request.query.get("all") == "1":
        return web.json_response(db.get_all_stats())
    campaigns = db.get_user_campaigns(auth["user_id"])
    totals = {"total": 0, "success": 0, "failed": 0}
    per_campaign = []
    for c in campaigns:
        s = db.get_stats(c["campaign_id"])
        totals["total"] += s["total"]
        totals["success"] += s["success"]
        totals["failed"] += s["failed"]
        per_campaign.append({"campaign_id": c["campaign_id"], "name": c["name"], **s})
    return web.json_response({"totals": totals, "per_campaign": per_campaign})


def create_web_app():
    app = web.Application()
    app.router.add_get("/", root_handler)
    app.router.add_get("/health", health_handler)

    app.router.add_get("/api/me", api_me)
    app.router.add_get("/api/campaigns", api_campaigns_list)
    app.router.add_post("/api/campaigns", api_campaigns_create)
    app.router.add_delete("/api/campaigns/{id}", api_campaign_delete)
    app.router.add_post("/api/campaigns/{id}/schedules", api_schedule_create)
    app.router.add_delete("/api/schedules/{id}", api_schedule_delete)
    app.router.add_get("/api/groups", api_groups_list)
    app.router.add_get("/api/stats", api_stats)

    app.router.add_get("/miniapp", miniapp_index_handler)
    app.router.add_get("/miniapp/", miniapp_index_handler)
    app.router.add_static("/miniapp", path="miniapp", name="miniapp")
    return app
