# Запуск

1. Установи Python 3.12 и PostgreSQL. При установке PostgreSQL запомни пароль пользователя `postgres`.
2. Скачай репозиторий: **Code → Download ZIP**, распакуй. Открой терминал в папке проекта.
3. Установи зависимости:

   ```sh
   pip install -r requirements.txt
   ```

4. В pgAdmin создай базу `mood_tracker`: **Databases → Create → Database**.
5. В папке проекта создай файл `.env` (без расширения `.txt`):

   ```dotenv
   BOT_TOKEN=токен_от_BotFather
   DATABASE_URL=postgresql://postgres:пароль@localhost:5432/mood_tracker
   DEFAULT_TIMEZONE=Europe/Moscow
   ```

   Замени токен и пароль своими значениями. Если пароль содержит `@`, `:`, `/`, `#` или `%`, закодируй эти символы для URL. `.env` в GitHub не загружай.

6. Запусти:

   ```sh
   python bot.py
   ```

7. Открой бота в Telegram и отправь `/start`. `/add` запрашивает настроение, часы работы и сна, затем необязательный комментарий. `/stats` — статистика, `/history` — история, `/settings` — напоминания, `/help` — справка. Остановка: `Ctrl+C`.

Таблицы создаются автоматически из `schema.sql`. Для 15 тестовых записей открой базу в pgAdmin → **Query Tool** и выполни `test_data.sql`. Записи относятся к отдельному тестовому пользователю.

[Схема базы данных](schema.png)
