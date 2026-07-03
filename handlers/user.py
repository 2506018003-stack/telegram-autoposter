import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes
from config import is_admin, MINIAPP_URL
from database import db
from keyboards import main_menu_keyboard, days_keyboard, groups_keyboard, campaigns_keyboard

CAMP_NAME, CAMP_TEXT, CAMP_MEDIA, CAMP_SPINTAX = range(4)
SCHEDULE_TIME = 5

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    text = f"""👋 Привет, {user.first_name}!

🤖 *SMMPilot — Автопостинг в Telegram*

Создавайте кампании, настраивайте расписание публикаций, управляйте группами и отслеживайте статистику."""
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(is_admin(user.id)), parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """📖 *Помощь по SMMPilot*

*Команды:*
/start — Главное меню
/crm — Открыть CRM (Mini App): кампании, расписания, статистика в одном экране
/guide — Пошаговый гайд по работе
/newcampaign — Создать кампанию (пошагово через диалог с ботом)
/mycampaigns — Мои кампании (список + расписание/статистика через кнопки)

*"📅 Расписание" и "📊 Статистика" в главном меню* — это кнопки, не команды. Открой /start и нажми на нужную.

*Команды администратора:*
/admin — Админ-панель (группы, все кампании, рассылка)
/addhere — Добавить текущую группу (отправь прямо в группе)
/setadmin @username — Назначить админа
/removeadmin @username — Снять админа

*Spintax (уникализация текста):*
Используйте `{вариант1|вариант2|вариант3}` в тексте кампании — бот случайно выберет один вариант при каждой публикации, чтобы посты не выглядели как дубликаты.

*CRM (Mini App)* дублирует управление кампаниями и расписанием в удобном веб-интерфейсе прямо в Telegram — доступна по кнопке "🖥 Открыть CRM" в /start или командой /crm. Медиа (фото/видео) к кампании пока добавляется только через диалог с ботом (/newcampaign), CRM — для текстовых кампаний, расписаний и статистики.

*Как это работает:*
1. Добавь бота админом в свою группу/канал
2. Напиши в этой группе /addhere — бот запомнит её
3. Создай кампанию с текстом (и, если нужно, spintax)
4. Настрой расписание: дни недели + время — бот будет публиковать автоматически
5. Следи за статистикой в /mycampaigns или CRM"""
    await update.effective_message.reply_text(text, parse_mode="Markdown")

async def crm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not MINIAPP_URL:
        await update.message.reply_text("⚠️ CRM временно недоступна (не настроен MINIAPP_URL).")
        return
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🖥 Открыть CRM", web_app=WebAppInfo(url=MINIAPP_URL))]])
    await update.message.reply_text("Панель управления кампаниями, расписанием и статистикой:", reply_markup=kb)

async def guide_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """📖 *Пошаговый гайд по работе с ботом*

━━━━━━━━━━━━━━━━━━━━
🔄 *Как работает бот*
━━━━━━━━━━━━━━━━━━━━

*1️⃣ Создание кампании*
   ├ Нажмите 🚀 *Создать кампанию* или `/newcampaign`
   ├ Введите название кампании
   ├ Введите текст поста
   ├ Отправьте фото/видео или напишите *пропустить*
   └ Включите/выключите Spintax

*2️⃣ Настройка расписания*
   ├ Выберите кампанию → 📅 *Добавить расписание*
   ├ Выберите группы для публикации
   ├ Выберите дни недели (Пн, Вт, Ср...)
   └ Введите время, например `14:30`

*3️⃣ Spintax — уникализация текста*
   Используйте `{вариант1|вариант2|вариант3}` в тексте.
   Бот случайно выберет один вариант при каждой публикации.

*Пример:*
```
{Привет|Здравствуй|Добрый день}, {друзья|подписчики|все}!
Сегодня у нас {акция|спецпредложение|скидка}!
```

━━━━━━━━━━━━━━━━━━━━
💡 *Полезные советы*
━━━━━━━━━━━━━━━━━━━━

• Кампании можно редактировать только через удаление и создание новой
• Статистика обновляется в реальном времени
• Для работы бот должен быть администратором в группе/канале
• Расписание проверяется каждые 30 секунд

❓ Есть вопросы? Напишите `/help`"""
    await update.message.reply_text(
        text, 
        reply_markup=main_menu_keyboard(is_admin(update.effective_user.id)),
        parse_mode="Markdown"
    )

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "menu_newcampaign":
        text = """🚀 *Создание кампании*

Введите название кампании:"""
        await query.edit_message_text(text, parse_mode="Markdown")
        context.user_data["state"] = "camp_name"
    elif data == "menu_mycampaigns":
        camps = db.get_user_campaigns(user_id)
        if not camps:
            await query.edit_message_text(
                "У вас пока нет кампаний. Создайте первую!",
                reply_markup=main_menu_keyboard(is_admin(user_id))
            )
            return
        text = """📋 *Ваши кампании:*

"""
        for c in camps:
            name = c.get("name", "")
            cid = c.get("campaign_id", "")
            status = c.get("status", "")
            text = text + f"• *{name}* `(ID: {cid})` — {status}" + chr(10)
        text = text + chr(10) + "Выберите кампанию для управления:"
        await query.edit_message_text(text, reply_markup=campaigns_keyboard(camps, "camp"), parse_mode="Markdown")
    elif data == "menu_schedule":
        camps = db.get_user_campaigns(user_id)
        if not camps:
            await query.edit_message_text("Сначала создайте кампанию.", reply_markup=main_menu_keyboard(is_admin(user_id)))
            return
        context.user_data["scheduling_camp"] = None
        context.user_data["schedule_days"] = []
        context.user_data["schedule_groups"] = []
        text = """📅 *Настройка расписания*

Выберите кампанию:"""
        await query.edit_message_text(
            text,
            reply_markup=campaigns_keyboard(camps, "schedcamp"),
            parse_mode="Markdown"
        )
    elif data == "menu_stats":
        camps = db.get_user_campaigns(user_id)
        if not camps:
            await query.edit_message_text("У вас нет кампаний для статистики.", reply_markup=main_menu_keyboard(is_admin(user_id)))
            return
        text = """📊 *Статистика по кампаниям:*

"""
        for c in camps:
            stats = db.get_stats(c["campaign_id"])
            text = text + f"• *{c['name']}*" + chr(10) + f"  Всего: {stats['total']} | ✅ {stats['success']} | ❌ {stats['failed']}" + chr(10)
        await query.edit_message_text(text, reply_markup=main_menu_keyboard(is_admin(user_id)), parse_mode="Markdown")
    elif data == "menu_guide":
        text = """📖 *Пошаговый гайд по работе с ботом*

━━━━━━━━━━━━━━━━━━━━
🔄 *Как работает бот*
━━━━━━━━━━━━━━━━━━━━

*1️⃣ Создание кампании*
   ├ Нажмите 🚀 *Создать кампанию* или `/newcampaign`
   ├ Введите название кампании
   ├ Введите текст поста
   ├ Отправьте фото/видео или напишите *пропустить*
   └ Включите/выключите Spintax

*2️⃣ Настройка расписания*
   ├ Выберите кампанию → 📅 *Добавить расписание*
   ├ Выберите группы для публикации
   ├ Выберите дни недели (Пн, Вт, Ср...)
   └ Введите время, например `14:30`

*3️⃣ Spintax — уникализация текста*
   Используйте `{вариант1|вариант2|вариант3}` в тексте.
   Бот случайно выберет один вариант при каждой публикации.

*Пример:*
```
{Привет|Здравствуй|Добрый день}, {друзья|подписчики|все}!
Сегодня у нас {акция|спецпредложение|скидка}!
```

━━━━━━━━━━━━━━━━━━━━
💡 *Полезные советы*
━━━━━━━━━━━━━━━━━━━━

• Кампании можно редактировать только через удаление и создание новой
• Статистика обновляется в реальном времени
• Для работы бот должен быть администратором в группе/канале
• Расписание проверяется каждые 30 секунд

❓ Есть вопросы? Напишите `/help`"""
        await query.edit_message_text(
            text,
            reply_markup=main_menu_keyboard(is_admin(user_id)),
            parse_mode="Markdown"
        )
    elif data == "menu_help":
        await help_command(update, context)
    elif data == "menu_back":
        await query.edit_message_text(
            "🏠 *Главное меню*",
            reply_markup=main_menu_keyboard(is_admin(user_id)),
            parse_mode="Markdown"
        )
    elif data == "menu_admin":
        from handlers.admin import admin_panel
        await admin_panel(update, context)

async def camp_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("camp_"):
        cid = data.replace("camp_", "")
        camp = db.get_campaign(cid)
        if not camp:
            await query.edit_message_text("Кампания не найдена.")
            return
        text = f"""📢 *{camp['name']}*

Текст: `{camp['text'][:100]}...`
Spintax: {'Да' if camp['spintax_enabled'] == '1' else 'Нет'}
Медиа: {camp['media_type'] or 'Нет'}
Статус: {camp['status']}

Выберите действие:"""
        buttons = [
            [InlineKeyboardButton("📅 Добавить расписание", callback_data=f"addsched_{cid}")],
            [InlineKeyboardButton("📊 Статистика", callback_data=f"campstats_{cid}")],
            [InlineKeyboardButton("🗑 Удалить", callback_data=f"delcamp_{cid}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_mycampaigns")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    elif data.startswith("addsched_"):
        cid = data.replace("addsched_", "")
        context.user_data["scheduling_camp"] = cid
        context.user_data["schedule_days"] = []
        context.user_data["schedule_groups"] = []
        groups = db.get_all_groups()
        if not groups:
            await query.edit_message_text("Нет доступных групп. Обратитесь к администратору.", reply_markup=main_menu_keyboard(is_admin(user_id)))
            return
        await query.edit_message_text(
            "📅 Выберите группы для публикации:",
            reply_markup=groups_keyboard(groups, "schedgroup", [])
        )
    elif data.startswith("campstats_"):
        cid = data.replace("campstats_", "")
        stats = db.get_stats(cid)
        text = f"📊 *Статистика кампании*" + chr(10) + chr(10) + f"Всего: {stats['total']}" + chr(10) + f"✅ Успешно: {stats['success']}" + chr(10) + f"❌ Ошибок: {stats['failed']}"
        await query.edit_message_text(text, reply_markup=main_menu_keyboard(is_admin(user_id)), parse_mode="Markdown")
    elif data.startswith("delcamp_"):
        cid = data.replace("delcamp_", "")
        db.delete_campaign(cid)
        await query.edit_message_text("🗑 Кампания удалена.", reply_markup=main_menu_keyboard(is_admin(user_id)))

async def schedule_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("schedcamp_"):
        cid = data.replace("schedcamp_", "")
        context.user_data["scheduling_camp"] = cid
        context.user_data["schedule_days"] = []
        context.user_data["schedule_groups"] = []
        groups = db.get_all_groups()
        if not groups:
            await query.edit_message_text("Нет доступных групп.", reply_markup=main_menu_keyboard(is_admin(user_id)))
            return
        await query.edit_message_text(
            "📅 Выберите группы для публикации:",
            reply_markup=groups_keyboard(groups, "schedgroup", [])
        )
    elif data.startswith("schedgroup_"):
        if data == "schedgroup_done":
            if not context.user_data.get("schedule_groups"):
                await query.answer("Выберите хотя бы одну группу!")
                return
            await query.edit_message_text(
                "📅 Выберите дни недели:",
                reply_markup=days_keyboard(context.user_data.get("schedule_days", []))
            )
            return
        chat_id = data.replace("schedgroup_", "")
        selected = context.user_data.get("schedule_groups", [])
        if chat_id in selected:
            selected.remove(chat_id)
        else:
            selected.append(chat_id)
        context.user_data["schedule_groups"] = selected
        groups = db.get_all_groups()
        await query.edit_message_text(
            "📅 Выберите группы для публикации:",
            reply_markup=groups_keyboard(groups, "schedgroup", selected)
        )
    elif data.startswith("day_"):
        if data == "days_done":
            if not context.user_data.get("schedule_days"):
                await query.answer("Выберите хотя бы один день!")
                return
            await query.edit_message_text(
                "⏰ Введите время публикации в формате `HH:MM` (например, `14:30`):",
                parse_mode="Markdown"
            )
            context.user_data["state"] = "schedule_time"
            return
        day = data.replace("day_", "")
        selected = context.user_data.get("schedule_days", [])
        if day in selected:
            selected.remove(day)
        else:
            selected.append(day)
        context.user_data["schedule_days"] = selected
        await query.edit_message_text(
            "📅 Выберите дни недели:",
            reply_markup=days_keyboard(selected)
        )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    state = context.user_data.get("state")

    if state == "camp_name":
        context.user_data["camp_name"] = update.message.text
        context.user_data["state"] = "camp_text"
        await update.message.reply_text("📝 Введите текст поста:")
    elif state == "camp_text":
        context.user_data["camp_text"] = update.message.text
        context.user_data["state"] = "camp_media"
        await update.message.reply_text(
            "📎 Отправьте фото или видео (или напишите 'пропустить'):"
        )
    elif state == "schedule_time":
        time_str = update.message.text.strip()
        if not re.match(r"^\\d{2}:\\d{2}$", time_str):
            await update.message.reply_text("❌ Неверный формат. Используйте HH:MM (например, 14:30)")
            return
        camp_id = context.user_data.get("scheduling_camp")
        days = context.user_data.get("schedule_days", [])
        groups = context.user_data.get("schedule_groups", [])
        for chat_id in groups:
            db.add_schedule(camp_id, int(chat_id), ",".join(days), time_str)
        context.user_data["state"] = None
        context.user_data["scheduling_camp"] = None
        context.user_data["schedule_days"] = []
        context.user_data["schedule_groups"] = []
        await update.message.reply_text(
            f"✅ Расписание сохранено!" + chr(10) + f"Дни: {', '.join(days)}" + chr(10) + f"Время: {time_str}",
            reply_markup=main_menu_keyboard(is_admin(user.id))
        )
    elif state == "broadcast":
        from handlers.admin import broadcast_message
        await broadcast_message(update, context)

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    if state == "camp_media":
        file_id = update.message.photo[-1].file_id
        context.user_data["camp_media_type"] = "photo"
        context.user_data["camp_media_file_id"] = file_id
        await ask_spintax(update, context)

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    if state == "camp_media":
        file_id = update.message.video.file_id
        context.user_data["camp_media_type"] = "video"
        context.user_data["camp_media_file_id"] = file_id
        await ask_spintax(update, context)

async def ask_spintax(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = "camp_spintax"
    await update.message.reply_text(
        "🔄 Использовать Spintax для уникализации текста?" + chr(10) + "(Пример: `{Привет|Здравствуй|Добрый день}, {мир|друзья}!`)",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да", callback_data="spintax_yes"),
             InlineKeyboardButton("❌ Нет", callback_data="spintax_no")]
        ])
    )

async def spintax_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "spintax_yes":
        spintax_enabled = True
    else:
        spintax_enabled = False

    name = context.user_data.get("camp_name", "")
    text = context.user_data.get("camp_text", "")
    media_type = context.user_data.get("camp_media_type", "")
    media_file_id = context.user_data.get("camp_media_file_id", "")

    cid = db.create_campaign(user_id, name, text, media_type, media_file_id, spintax_enabled)

    context.user_data["state"] = None
    context.user_data["camp_name"] = None
    context.user_data["camp_text"] = None
    context.user_data["camp_media_type"] = None
    context.user_data["camp_media_file_id"] = None

    await query.edit_message_text(
        f"✅ Кампания *{name}* создана!" + chr(10) + f"ID: `{cid}`" + chr(10) + chr(10) + "Теперь настройте расписание публикаций.",
        reply_markup=main_menu_keyboard(is_admin(user_id)),
        parse_mode="Markdown"
    )

async def skip_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    if state == "camp_media" and update.message.text.lower() in ["пропустить", "skip", "нет"]:
        context.user_data["camp_media_type"] = ""
        context.user_data["camp_media_file_id"] = ""
        await ask_spintax(update, context)

async def newcampaign_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = "camp_name"
    await update.message.reply_text("🚀 *Создание кампании*" + chr(10) + chr(10) + "Введите название кампании:", parse_mode="Markdown")

async def mycampaigns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    camps = db.get_user_campaigns(user_id)
    if not camps:
        await update.message.reply_text("У вас пока нет кампаний.")
        return
    text = """📋 *Ваши кампании:*

"""
    for c in camps:
        text = text + f"• *{c['name']}* `(ID: {c['campaign_id']})` — {c['status']}" + chr(10)
    await update.message.reply_text(text, parse_mode="Markdown")
