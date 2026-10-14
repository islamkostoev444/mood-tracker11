BEGIN;
INSERT INTO users(telegram_id, chat_id, timezone, reminders_enabled)
VALUES (900000000000000001, 900000000000000001, 'UTC', FALSE)
ON CONFLICT (telegram_id) DO NOTHING;

INSERT INTO daily_entries(user_id, entry_date, mood, productive_hours, sleep_hours, comment)
SELECT 900000000000000001,
    (NOW() AT TIME ZONE 'UTC')::date - days_ago,
    mood, productive_hours, sleep_hours, comment
FROM (VALUES
    (14, 2, 7.0, 5.5, 'Много учёбы, мало сна'),
    (13, 3, 5.0, 6.5, 'Обычный день'),
    (12, 4, 4.0, 8.0, 'Выспался'),
    (11, 5, 3.5, 8.5, 'Прогулка после занятий'),
    (10, 3, 6.0, 7.0, 'Подготовка к контрольной'),
    (9,  2, 8.0, 5.0, 'Устал после нагрузки'),
    (8,  4, 4.5, 8.0, 'Ровное настроение'),
    (7,  5, 2.0, 9.0, 'Выходной'),
    (6,  4, 5.0, 8.0, 'Закончил проект'),
    (5,  3, 6.5, 6.0, 'Много заданий'),
    (4,  2, 7.5, 5.5, 'Поздно лёг'),
    (3,  4, 4.0, 8.5, 'Спокойный день'),
    (2,  5, 3.0, 9.0, 'Отдохнул'),
    (1,  3, 6.0, 7.0, 'Учебный день'),
    (0,  4, 4.5, 8.0, 'Хороший сон')
) AS sample(days_ago, mood, productive_hours, sleep_hours, comment)
ON CONFLICT (user_id, entry_date) DO NOTHING;
COMMIT;
