import math
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def parse_hours(text):

    try:
        value = float(text.strip().replace(",", "."))
    except ValueError as error:
        raise ValueError("Введите число часов, например 7,5.") from error
    if not math.isfinite(value) or not 0 <= value <= 24:
        raise ValueError("Часы должны быть числом от 0 до 24.")
    if value != round(value, 2):
        raise ValueError("Укажите не более двух знаков после запятой.")
    return value


def parse_time(text):
    value = text.strip()
    if len(value) != 5 or value[2] != ":" or not value[:2].isdigit() or not value[3:].isdigit():
        raise ValueError("Введите время в формате ЧЧ:ММ, например 21:30.")
    if int(value[:2]) > 23 or int(value[3:]) > 59:
        raise ValueError("Введите время в формате ЧЧ:ММ, например 21:30.")
    return value


def parse_timezone(text):
    name = text.strip()
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("Неизвестный пояс. Пример: Europe/Moscow, Asia/Yekaterinburg, UTC.") from error
    return name


def local_today(timezone: str):

    return datetime.now(ZoneInfo(timezone)).date()
