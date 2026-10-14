CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'Europe/Moscow',
    reminder_time TIME NOT NULL DEFAULT '21:00',
    reminders_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    last_reminded_on DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS daily_entries (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    entry_date DATE NOT NULL,
    mood SMALLINT NOT NULL CHECK (mood BETWEEN 1 AND 5),
    productive_hours NUMERIC(4,2) NOT NULL CHECK (productive_hours BETWEEN 0 AND 24),
    sleep_hours NUMERIC(4,2) NOT NULL CHECK (sleep_hours BETWEEN 0 AND 24),
    comment TEXT NOT NULL DEFAULT '' CHECK (char_length(comment) <= 1000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT one_entry_per_day UNIQUE (user_id, entry_date)
);

CREATE TABLE IF NOT EXISTS entry_revisions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entry_id BIGINT NOT NULL REFERENCES daily_entries(id) ON DELETE CASCADE,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    mood SMALLINT NOT NULL CHECK (mood BETWEEN 1 AND 5),
    productive_hours NUMERIC(4,2) NOT NULL CHECK (productive_hours BETWEEN 0 AND 24),
    sleep_hours NUMERIC(4,2) NOT NULL CHECK (sleep_hours BETWEEN 0 AND 24),
    comment TEXT NOT NULL DEFAULT '' CHECK (char_length(comment) <= 1000)
);
CREATE INDEX IF NOT EXISTS revisions_entry_idx ON entry_revisions(entry_id, changed_at);
