import logging
from telebot.apihelper import ApiTelegramException

from keyboards import main_menu
import db_handler as db

logger = logging.getLogger(__name__)


def send_due_reminders(bot):
    for user in db.due_reminders():
        user_id, day = user["telegram_id"], user["local_date"]
        try:
            bot.send_message(user["chat_id"], "⏰ Как прошёл день? Запиши настроение, работу/учёбу и сон.",
                             reply_markup=main_menu())
            db.mark_reminded(user_id, day)
        except ApiTelegramException as error:
            if error.error_code == 403:

                db.set_setting(user_id, "reminders_enabled", False)
            logger.warning("Не удалось доставить напоминание (%s).", type(error).__name__)
        except Exception as error:

            logger.warning("Ошибка доставки напоминания (%s); повтор при следующей проверке.", type(error).__name__)


def reminder_loop(bot, stop_event):
    while not stop_event.is_set():
        try:
            send_due_reminders(bot)
        except Exception as error:
            logger.warning("Проверка напоминаний недоступна (%s).", type(error).__name__)
        stop_event.wait(30)
