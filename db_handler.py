from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from config import DATABASE_URL

def connect():


    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=10)

def initialize():
    with connect() as connection:
        connection.execute(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))

def ensure_user(user_id, chat_id, timezone):
    with connect() as connection:
        connection.execute(
            """INSERT INTO users(telegram_id, chat_id, timezone) VALUES (%s, %s, %s)
            ON CONFLICT (telegram_id) DO UPDATE SET chat_id = EXCLUDED.chat_id""",
            (user_id, chat_id, timezone),
        )
        return connection.execute("SELECT * FROM users WHERE telegram_id = %s", (user_id,)).fetchone()

def get_user(user_id):
    with connect() as connection:
        return connection.execute("SELECT * FROM users WHERE telegram_id = %s", (user_id,)).fetchone()

def set_setting(user_id, field, value):

    queries = {
        "timezone": "UPDATE users SET timezone = %s WHERE telegram_id = %s",
        "reminder_time": "UPDATE users SET reminder_time = %s WHERE telegram_id = %s",
        "reminders_enabled": "UPDATE users SET reminders_enabled = %s WHERE telegram_id = %s",
    }
    with connect() as connection:
        connection.execute(queries[field], (value, user_id))

def save_entry(user_id, entry):
    with connect() as connection:

        saved = connection.execute(
            """INSERT INTO daily_entries
            (user_id, entry_date, mood, productive_hours, sleep_hours, comment)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, entry_date) DO UPDATE SET
                mood = EXCLUDED.mood, productive_hours = EXCLUDED.productive_hours,
                sleep_hours = EXCLUDED.sleep_hours, comment = EXCLUDED.comment,
                updated_at = NOW() RETURNING id""",
            (user_id, entry["date"], entry["mood"], entry["work"], entry["sleep"], entry["comment"]),
        ).fetchone()


        connection.execute(
            """INSERT INTO entry_revisions(entry_id, mood, productive_hours, sleep_hours, comment)
            VALUES (%s, %s, %s, %s, %s)""",
            (saved["id"], entry["mood"], entry["work"], entry["sleep"], entry["comment"]),
        )

def entries(user_id, start, end, limit = 31, offset = 0):
    with connect() as connection:
        return connection.execute(
            """SELECT * FROM daily_entries WHERE user_id = %s AND entry_date BETWEEN %s AND %s
            ORDER BY entry_date DESC LIMIT %s OFFSET %s""",
            (user_id, start, end, limit, offset),
        ).fetchall()

def revisions(user_id, entry_date):
    with connect() as connection:
        return connection.execute(
            """SELECT r.* FROM entry_revisions r JOIN daily_entries e ON e.id = r.entry_id
            WHERE e.user_id = %s AND e.entry_date = %s ORDER BY r.id DESC LIMIT 5""",
            (user_id, entry_date),
        ).fetchall()

def summary(user_id, start, end):
    with connect() as connection:
        return connection.execute(
            """SELECT COUNT(*) AS n, AVG(mood) AS mood,
            AVG(productive_hours) AS work, SUM(productive_hours) AS total_work,
            AVG(sleep_hours) AS sleep, MAX(mood) AS best_mood
            FROM daily_entries WHERE user_id = %s AND entry_date BETWEEN %s AND %s""",
            (user_id, start, end),
        ).fetchone()

def insight_data(user_id, start, end):
    with connect() as connection:

        return connection.execute(
            """SELECT COUNT(*) AS n,
            CORR(sleep_hours::float8, productive_hours::float8) AS sleep_work_corr,
            CORR(productive_hours::float8, mood::float8) AS work_mood_corr,
            COUNT(*) FILTER (WHERE sleep_hours >= 8) AS long_sleep_n,
            COUNT(*) FILTER (WHERE sleep_hours < 8) AS short_sleep_n,
            AVG(mood) FILTER (WHERE sleep_hours >= 8) AS long_sleep_mood,
            AVG(mood) FILTER (WHERE sleep_hours < 8) AS short_sleep_mood,
            COUNT(*) FILTER (WHERE productive_hours >= 6) AS long_work_n,
            COUNT(*) FILTER (WHERE productive_hours < 6) AS short_work_n,
            AVG(mood) FILTER (WHERE productive_hours >= 6) AS long_work_mood,
            AVG(mood) FILTER (WHERE productive_hours < 6) AS short_work_mood
            FROM daily_entries WHERE user_id = %s AND entry_date BETWEEN %s AND %s""",
            (user_id, start, end),
        ).fetchone()

def weekday_data(user_id, start, end):
    with connect() as connection:
        return connection.execute(
            """SELECT EXTRACT(ISODOW FROM entry_date)::int AS weekday,
            COUNT(*) AS n, AVG(mood) AS mood FROM daily_entries
            WHERE user_id = %s AND entry_date BETWEEN %s AND %s
            GROUP BY weekday HAVING COUNT(*) >= 2 ORDER BY mood DESC, weekday""",
            (user_id, start, end),
        ).fetchall()

def clear_entries(user_id):
    with connect() as connection:

        connection.execute("DELETE FROM daily_entries WHERE user_id = %s", (user_id,))

def due_reminders():
    with connect() as connection:
        return connection.execute(
            """SELECT u.*, (NOW() AT TIME ZONE u.timezone)::date AS local_date FROM users u
            WHERE reminders_enabled
                AND (NOW() AT TIME ZONE u.timezone)::time >= reminder_time
                AND NOT EXISTS (SELECT 1 FROM daily_entries e WHERE e.user_id = u.telegram_id
                    AND e.entry_date = (NOW() AT TIME ZONE u.timezone)::date)
                AND (last_reminded_on IS NULL
                    OR last_reminded_on <> (NOW() AT TIME ZONE u.timezone)::date)"""
        ).fetchall()

def mark_reminded(user_id, day):
    with connect() as connection:
        connection.execute(
            "UPDATE users SET last_reminded_on = %s WHERE telegram_id = %s",
            (day, user_id),
        )
