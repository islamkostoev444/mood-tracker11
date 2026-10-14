import logging
import threading
from datetime import date

import telebot
from telebot.types import BotCommand
import analyzer
import db_handler as db
import keyboards as kb
from config import BOT_TOKEN, DEFAULT_TIMEZONE
from reminders import reminder_loop
from validators import local_today, parse_hours, parse_time, parse_timezone

bot = None
answers = {}
HELP = (
    "Привет! Я трекер настроения и продуктивности.\n"
    "/add — записать день\n/stats — статистика и график\n/history — история\n"
    "/settings — напоминания\n/clear — очистка с подтверждением\n"
    "/cancel — отмена ввода\n/help — справка\n\n"
    "Введи настроение 1–5, часы работы/учёбы и сна (0–24), затем комментарий. "
    "Можно писать дроби: 2,5. Комментарий необязателен, до 1000 символов. "
    "Повторная запись дня сохраняет историю исправлений. "
    "После перезапуска незаконченный ввод нужно начать заново. "
    "Напоминания включаются в /settings. Записи хранятся на ПК владельца бота."
)


def send(user_id, text, keyboard=None):
    return bot.send_message(user_id, text, reply_markup=keyboard or kb.main_menu())


def ask(user_id, step):

    answers[user_id]["step"] = step
    if step == "mood":
        text = f"День: {answers[user_id]['date']}\nОцени настроение: 1 — ужасно, 5 — отлично."
        keyboard = kb.mood_keyboard()
    elif step == "work":
        text, keyboard = "Сколько часов полезной работы/учёбы?", kb.hours_keyboard("work")
    elif step == "sleep":
        text, keyboard = "Сколько часов ты спал?", kb.hours_keyboard("sleep")
    elif step == "comment":
        text = "Напиши комментарий (до 1000 символов) или нажми «Пропустить»."
        keyboard = kb.inline([[("Пропустить", "comment:skip")]])
    else:
        text = "Удалить все твои записи и их версии?" if step == "clear" else "День уже записан. Исправить его?"
        keyboard = kb.inline([[("Да", step + ":yes"), ("Отмена", step + ":no")]])
    question = send(user_id, text, keyboard)
    answers[user_id]["message_id"] = question.message_id


def start_add(user_id):
    if answers.get(user_id, {}).get("step") in ("mood", "work", "sleep", "comment"):
        ask(user_id, answers[user_id]["step"])
        return
    today = local_today(db.get_user(user_id)["timezone"])
    answers[user_id] = {"date": today.isoformat()}
    ask(user_id, "overwrite" if db.entries(user_id, today, today) else "mood")


def read_answer(user_id, text):
    data = answers[user_id]
    step = data["step"]
    if step == "mood":
        if text not in ("1", "2", "3", "4", "5"):
            raise ValueError("Выбери настроение от 1 до 5.")
        data["mood"] = int(text)
        ask(user_id, "work")
    elif step in ("work", "sleep"):
        data[step] = parse_hours(text)
        ask(user_id, "sleep" if step == "work" else "comment")
    elif step == "comment":
        if len(text) > 1000:
            raise ValueError("Комментарий слишком длинный: максимум 1000 символов.")
        data["comment"] = text
        db.save_entry(user_id, data)
        answers.pop(user_id)
        send(user_id, f"✅ День {data['date']} сохранён! Статистика: /stats")
    elif step in ("time", "timezone"):
        if step == "time":
            db.set_setting(user_id, "reminder_time", parse_time(text))
        else:
            db.set_setting(user_id, "timezone", parse_timezone(text))
        answers.pop(user_id)
        show_settings(user_id)
    else:
        send(user_id, "Выбери ответ кнопкой или введи /cancel.")


def show_settings(user_id):
    user = db.get_user(user_id)
    status = "включены" if user["reminders_enabled"] else "выключены"
    send(user_id, f"Напоминания {status}\nВремя: {user['reminder_time']:%H:%M}\n"
         f"Часовой пояс: {user['timezone']}", kb.settings_keyboard(user["reminders_enabled"]))


def show_history(user_id, page=0):
    rows = db.entries(user_id, date.min, date.max, limit=6, offset=page * 5)
    if not rows:
        send(user_id, "Записей пока нет.")
        return
    text, buttons = f"История · страница {page + 1}\n", []
    for row in rows[:5]:
        text += (f"\n{row['entry_date']:%d.%m.%Y}: настроение {row['mood']}/5, "
                 f"работа {row['productive_hours']} ч, сон {row['sleep_hours']} ч.\n"
                 f"{row['comment'][:180]}\n")
        buttons.append([(f"Версии {row['entry_date']:%d.%m}", f"revisions:{row['entry_date']}")])
    if page > 0:
        buttons.append([("← Новее", f"history:{page - 1}")])
    if len(rows) > 5:
        buttons.append([("Старее →", f"history:{page + 1}")])
    send(user_id, text, kb.inline(buttons))


def show_analysis(user_id, action, days):
    today = local_today(db.get_user(user_id)["timezone"])
    start, end = analyzer.period(today, days)
    rows = db.entries(user_id, start, end)
    if action == "insights":
        text = analyzer.insights_text(db.insight_data(user_id, start, end),
                                      db.weekday_data(user_id, start, end), start, end)
    elif action == "chart":
        if rows:
            with analyzer.build_chart(rows, start, end) as image:
                bot.send_photo(user_id, image, caption="Пропущенные дни — разрывы линий.")
        else:
            send(user_id, "За этот период записей нет.")
        return
    else:
        summary = db.summary(user_id, start, end)
        best = [row for row in rows if row["mood"] == summary["best_mood"]]
        text = analyzer.summary_text(summary, start, end, best)
    send(user_id, text, kb.stats_keyboard())


def process_message(message):
    if message.chat.type != "private":
        send(message.chat.id, "Открой личный чат со мной и отправь /start.")
        return
    user_id = message.from_user.id
    db.ensure_user(user_id, message.chat.id, DEFAULT_TIMEZONE)
    text = message.text.strip()
    commands = {kb.ADD: "/add", kb.STATS: "/stats", kb.HISTORY: "/history",
                kb.SETTINGS: "/settings", kb.HELP: "/help", kb.CANCEL: "/cancel"}
    command = commands.get(text, text.split("@")[0])
    if command in ("/start", "/help"):
        send(user_id, HELP)
    elif command == "/add":
        start_add(user_id)
    elif command == "/stats":
        send(user_id, "Что хочешь узнать? Месяц — последние 30 дней.", kb.stats_keyboard())
    elif command == "/history":
        show_history(user_id)
    elif command == "/settings":
        answers.pop(user_id, None)
        show_settings(user_id)
    elif command == "/clear":
        answers[user_id] = {}
        ask(user_id, "clear")
    elif command == "/cancel":
        answers.pop(user_id, None)
        send(user_id, "Ввод отменён. Сохранённые записи остались.")
    elif text.startswith("/"):
        send(user_id, "Неизвестная команда. Справка: /help")
    elif user_id in answers:
        read_answer(user_id, text)
    else:
        send(user_id, "Начни запись через /add или выбери кнопку меню.")


def process_callback(call):
    if not call.message or call.message.chat.type != "private" or call.from_user.id != call.message.chat.id:
        bot.answer_callback_query(call.id, "Используй личный чат.")
        return
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    db.ensure_user(user_id, call.message.chat.id, DEFAULT_TIMEZONE)
    action, value = call.data.split(":", 1)
    if action in ("stats", "insights", "chart"):
        show_analysis(user_id, action, int(value))
    elif action == "history":
        page = int(value)
        if not 0 <= page <= 10000:
            raise ValueError("Некорректная страница.")
        show_history(user_id, page)
    elif action == "revisions":
        rows = db.revisions(user_id, date.fromisoformat(value))
        text = "Последние 5 версий дня:\n"
        for row in rows:
            text += (f"\n{row['changed_at']:%d.%m.%Y %H:%M} UTC: настроение {row['mood']}, "
                     f"работа {row['productive_hours']} ч, сон {row['sleep_hours']} ч\n{row['comment'][:180]}\n")
        send(user_id, text if rows else "Версий нет.")
    elif action == "settings":
        answers.pop(user_id, None)
        if value == "toggle":
            db.set_setting(user_id, "reminders_enabled", not db.get_user(user_id)["reminders_enabled"])
            show_settings(user_id)
        elif value in ("time", "timezone"):
            answers[user_id] = {"step": value}
            send(user_id, "Введи время ЧЧ:ММ." if value == "time" else "Введи пояс, например Europe/Moscow или UTC.")
    else:
        data = answers.get(user_id, {})

        if data.get("step") != action or data.get("message_id") != call.message.message_id:
            send(user_id, "Кнопка устарела. Продолжить: /add, отменить: /cancel.")
        elif action in ("clear", "overwrite") and value in ("yes", "no"):
            if value == "no":
                answers.pop(user_id)
                send(user_id, "Действие отменено.")
            elif action == "clear":
                db.clear_entries(user_id)
                answers.pop(user_id)
                send(user_id, "✅ Твои записи и версии удалены.")
            else:
                ask(user_id, "mood")
        elif value == "other" and action in ("work", "sleep"):
            send(user_id, "Введи число часов от 0 до 24, например 7,5.")
        else:
            read_answer(user_id, "" if action == "comment" and value == "skip" else value)


def handle_message(message):
    try:
        process_message(message)
    except ValueError as error:
        send(message.chat.id, str(error))
    except Exception as error:
        report_error(message.chat.id, error)


def handle_callback(call):
    try:
        process_callback(call)
    except ValueError as error:
        if call.message:
            send(call.message.chat.id, str(error))
    except Exception as error:
        if call.message:
            report_error(call.message.chat.id, error)


def report_error(user_id, error):

    print("Ошибка:", type(error).__name__)
    try:
        send(user_id, "Сервис временно недоступен. Попробуй позже.")
    except Exception:
        pass


def setup_handlers():

    bot.register_message_handler(handle_message, func=lambda message: True, content_types=["text"])
    bot.register_callback_query_handler(handle_callback, func=lambda call: True)


def main():
    global bot
    telebot.logger.handlers = [logging.NullHandler()]
    telebot.logger.propagate = False
    stop = threading.Event()
    try:
        db.initialize()
        bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
        setup_handlers()
        bot.get_me()
        bot.set_my_commands([BotCommand(name, text) for name, text in (
            ("start", "Начать"), ("add", "Записать день"), ("stats", "Статистика"),
            ("history", "История"), ("settings", "Настройки"), ("clear", "Очистка"),
            ("help", "Справка"), ("cancel", "Отмена"))])
        bot.delete_webhook(drop_pending_updates=False)
        threading.Thread(target=reminder_loop, args=(bot, stop), daemon=True).start()
        print("Бот запущен. Отправь /start в Telegram.", flush=True)
        bot.infinity_polling(timeout=20, long_polling_timeout=20, allowed_updates=["message", "callback_query"])
    except Exception as error:
        print("Не удалось запустить бот:", type(error).__name__)
        return 1
    finally:
        stop.set()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
