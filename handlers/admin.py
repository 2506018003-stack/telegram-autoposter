import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import is_admin
from database import db
from keyboards import admin_menu_keyboard, groups_keyboard

ADMIN_BROADCAST = 1

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        user_id = query.from_user.id
    else:
        user_id = update.message.from_user.id

    if not is_admin(user_id):
        if query:
            await query.edit_message_text("⛔ Доступ запрещён.")
        else:
            await update.message.reply_text("⛔ Доступ запрещён.")
        return

    text = """🔐 *Админ-панель*

Выберите действие:"""
    if query:
        await query.edit_message_text(text, reply_markup=admin_menu_keyboard(), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=admin_menu_keyboard(), parse_mode="Markdown")

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.edit_message_text("⛔ Доступ запрещён.")
        return

    if data == "admin_addgroup":
        await query.edit_message_text(
            """📋 *Добавление группы*

1. Добавьте бота в группу/канал администратором
2. Отправьте в группу команду `/addhere`

Или перешлите мне любое сообщение из группы/канала.""",
            parse_mode="Markdown"
        )
    elif data == "admin_removegroup":
        groups = db.get_all_groups()
        if not groups:
            await query.edit_message_text("Групп пока нет.", reply_markup=admin_menu_keyboard())
            return
        await query.edit_message_text(
            "Выберите группу для удаления:",
            reply_markup=groups_keyboard(groups, "rmgroup")
        )
    elif data == "admin_listgroups":
        groups = db.get_all_groups()
        if not groups:
            text = "Групп пока нет."
        else:
            text = "📋 *Список групп:*

"
            for g in groups:
                title = g.get("title", "Unknown")
                chat_id = g.get("chat_id", "")
                username = g.get("username", "")
                uname = f"@{username}" if username else ""
                text += f"• {title} {uname} `(ID: {chat_id})`
"
        await query.edit_message_text(text, reply_markup=admin_menu_keyboard(), parse_mode="Markdown")
    elif data == "admin_allcampaigns":
        camps = db.get_all_campaigns()
        if not camps:
            text = "Кампаний пока нет."
        else:
            text = "📢 *Все кампании:*

"
            for c in camps:
                name = c.get("name", "")
                cid = c.get("campaign_id", "")
                owner = c.get("owner_id", "")
                status = c.get("status", "")
                text += f"• *{name}* `(ID: {cid})` — Владелец: `{owner}` — {status}
"
        await query.edit_message_text(text, reply_markup=admin_menu_keyboard(), parse_mode="Markdown")
    elif data == "admin_stats":
        stats = db.get_all_stats()
        users = db.get_all_users()
        groups = db.get_all_groups()
        camps = db.get_all_campaigns()
        text = f"""📊 *Общая статистика*

👤 Пользователей: {len(users)}
👥 Групп: {len(groups)}
📢 Кампаний: {len(camps)}
📨 Всего постов: {stats['total_posts']}
✅ Успешно: {stats['successful']}"""
        await query.edit_message_text(text, reply_markup=admin_menu_keyboard(), parse_mode="Markdown")
    elif data == "admin_broadcast":
        await query.edit_message_text(
            "📣 *Рассылка*

Отправьте сообщение для рассылки всем пользователям.",
            parse_mode="Markdown"
        )
        context.user_data["admin_state"] = "broadcast"
    elif data == "admin_admins":
        users = db.get_all_users()
        admins = [u for u in users if u.get("is_admin") == "1"]
        text = "👤 *Администраторы:*

"
        for a in admins:
            text += f"• `{a.get('user_id', '')}` — {a.get('first_name', '')} @{a.get('username', '')}
"
        text += "
Для назначения админом: `/setadmin @username`"
        await query.edit_message_text(text, reply_markup=admin_menu_keyboard(), parse_mode="Markdown")
    elif data.startswith("rmgroup_"):
        chat_id = data.replace("rmgroup_", "")
        db.remove_group(int(chat_id))
        await query.edit_message_text("✅ Группа удалена.", reply_markup=admin_menu_keyboard())
    elif data == "menu_back":
        await admin_panel(update, context)

async def add_here_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Только админ.")
        return
    db.add_group(chat.id, chat.title or "", chat.username or "", chat.type, user.id)
    await update.message.reply_text(f"✅ Группа *{chat.title}* добавлена в базу!", parse_mode="Markdown")

async def set_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Только супер-админ.")
        return
    if not context.args:
        await update.message.reply_text("Использование: `/setadmin @username` или `/setadmin 123456`")
        return
    target = context.args[0]
    users = db.get_all_users()
    found = None
    for u in users:
        if u.get("username", "").lower() == target.replace("@", "").lower() or u.get("user_id") == target:
            found = u
            break
    if found:
        db.set_admin(int(found["user_id"]), True)
        await update.message.reply_text(f"✅ Пользователь `{found['first_name']}` назначен админом.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Пользователь не найден. Сначала пусть напишет боту /start.")

async def remove_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not context.args:
        await update.message.reply_text("Использование: `/removeadmin @username`")
        return
    target = context.args[0].replace("@", "").lower()
    users = db.get_all_users()
    for u in users:
        if u.get("username", "").lower() == target:
            db.set_admin(int(u["user_id"]), False)
            await update.message.reply_text(f"✅ Админ-права сняты у {u['first_name']}.")
            return
    await update.message.reply_text("❌ Пользователь не найден.")

async def forward_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if update.message.forward_from_chat:
        chat = update.message.forward_from_chat
        db.add_group(chat.id, chat.title or "", chat.username or "", chat.type, user.id)
        await update.message.reply_text(f"✅ Группа/канал *{chat.title}* добавлена!", parse_mode="Markdown")

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("admin_state") != "broadcast":
        return
    del context.user_data["admin_state"]
    users = db.get_all_users()
    sent = 0
    failed = 0
    msg = await update.message.reply_text("📣 Начинаю рассылку...")
    for u in users:
        try:
            await update.message.copy(chat_id=int(u["user_id"]))
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await msg.edit_text(f"✅ Рассылка завершена!
Отправлено: {sent}
Не удалось: {failed}", parse_mode="Markdown")
