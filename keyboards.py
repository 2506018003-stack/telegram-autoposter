from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_keyboard(is_admin: bool = False):
    buttons = [
        [InlineKeyboardButton("🚀 Создать кампанию", callback_data="menu_newcampaign")],
        [InlineKeyboardButton("📋 Мои кампании", callback_data="menu_mycampaigns")],
        [InlineKeyboardButton("📅 Расписание", callback_data="menu_schedule")],
        [InlineKeyboardButton("📊 Статистика", callback_data="menu_stats")],
        [InlineKeyboardButton("❓ Помощь", callback_data="menu_help")],
    ]
    if is_admin:
        buttons.insert(0, [InlineKeyboardButton("🔐 Админ-панель", callback_data="menu_admin")])
    return InlineKeyboardMarkup(buttons)

def admin_menu_keyboard():
    buttons = [
        [InlineKeyboardButton("➕ Добавить группу", callback_data="admin_addgroup")],
        [InlineKeyboardButton("➖ Удалить группу", callback_data="admin_removegroup")],
        [InlineKeyboardButton("📋 Список групп", callback_data="admin_listgroups")],
        [InlineKeyboardButton("📢 Все кампании", callback_data="admin_allcampaigns")],
        [InlineKeyboardButton("📊 Общая статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📣 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👤 Управление админами", callback_data="admin_admins")],
        [InlineKeyboardButton("🔙 Назад", callback_data="menu_back")],
    ]
    return InlineKeyboardMarkup(buttons)

def yes_no_keyboard(prefix: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Да", callback_data=f"{prefix}_yes"),
         InlineKeyboardButton("❌ Нет", callback_data=f"{prefix}_no")]
    ])

def days_keyboard(selected_days: list = None):
    if selected_days is None:
        selected_days = []
    days = [("Пн", "mon"), ("Вт", "tue"), ("Ср", "wed"), ("Чт", "thu"), 
            ("Пт", "fri"), ("Сб", "sat"), ("Вс", "sun")]
    buttons = []
    row = []
    for label, val in days:
        mark = "✅" if val in selected_days else ""
        row.append(InlineKeyboardButton(f"{mark}{label}", callback_data=f"day_{val}"))
    buttons.append(row)
    buttons.append([InlineKeyboardButton("✔️ Готово", callback_data="days_done")])
    return InlineKeyboardMarkup(buttons)

def groups_keyboard(groups: list, prefix: str, selected: list = None):
    if selected is None:
        selected = []
    buttons = []
    for g in groups:
        chat_id = g.get("chat_id", "")
        title = g.get("title", "Unknown")
        mark = "✅ " if str(chat_id) in selected else ""
        buttons.append([InlineKeyboardButton(f"{mark}{title}", callback_data=f"{prefix}_{chat_id}")])
    buttons.append([InlineKeyboardButton("✔️ Готово", callback_data=f"{prefix}_done")])
    return InlineKeyboardMarkup(buttons)

def campaigns_keyboard(campaigns: list, prefix: str):
    buttons = []
    for c in campaigns:
        cid = c.get("campaign_id", "")
        name = c.get("name", "Unknown")
        buttons.append([InlineKeyboardButton(name, callback_data=f"{prefix}_{cid}")])
    buttons.append([InlineKeyboardButton("🔙 Отмена", callback_data="menu_back")])
    return InlineKeyboardMarkup(buttons)
