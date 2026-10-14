from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

ADD = "➕ Записать день"
STATS = "📊 Статистика"
HISTORY = "📚 История"
SETTINGS = "⚙️ Настройки"
HELP = "❓ Справка"
CANCEL = "❌ Отмена"


def main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
    keyboard.row(ADD, STATS)
    keyboard.row(HISTORY, SETTINGS)
    keyboard.row(HELP, CANCEL)
    return keyboard


def inline(rows):
    keyboard = InlineKeyboardMarkup()
    for row in rows:
        keyboard.row(*(InlineKeyboardButton(label, callback_data=data) for label, data in row))
    return keyboard


def mood_keyboard():
    return inline([[(f"{i} {emoji}", f"mood:{i}")
                    for i, emoji in enumerate(("😞", "😐", "🙂", "😊", "🤩"), 1)]])


def hours_keyboard(kind):
    values = (0.5, 1, 2, 4) if kind == "work" else (6, 7, 8, 9)
    return inline([
        [(f"{value} ч", f"{kind}:{value}") for value in values],
        [("Другое…", f"{kind}:other")],
    ])


def stats_keyboard():
    return inline([
        [("📅 За неделю", "stats:7"), ("🗓️ За месяц (30 дней)", "stats:30")],
        [("🔍 Мои инсайты", "insights:30")],
        [("📉 График: неделя", "chart:7"), ("📉 График: месяц", "chart:30")],
    ])


def settings_keyboard(enabled):
    return inline([
        [("⏰ Изменить время", "settings:time")],
        [("🌍 Часовой пояс", "settings:timezone")],
        [("🔕 Выключить напоминания" if enabled else "🔔 Включить напоминания", "settings:toggle")],
    ])
