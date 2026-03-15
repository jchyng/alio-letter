-- Alio-Letter D1 스키마
-- 적용: wrangler d1 execute alio-letter --file=schema.sql

CREATE TABLE IF NOT EXISTS postings (
    posting_id          INTEGER PRIMARY KEY,
    alio_id             TEXT NOT NULL UNIQUE,
    title               TEXT NOT NULL,
    org_name            TEXT,
    posting_url         TEXT NOT NULL,
    deadline            TEXT NOT NULL,
    registered          TEXT,
    ncs                 TEXT,
    work_field          TEXT,
    employment_type     TEXT,
    location            TEXT,
    education           TEXT,
    recruit_type        TEXT,
    is_substitute       TEXT,
    salary_url          TEXT,
    preferred           TEXT,
    attachment_path     TEXT,
    attachment_ext      TEXT,
    attachment_converted TEXT,
    bonus_points        TEXT,
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS posting_tracks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    posting_id      INTEGER NOT NULL REFERENCES postings(posting_id),
    track_name      TEXT NOT NULL,
    positions       TEXT,
    total_positions INTEGER,
    eligibility     TEXT   -- JSON {"education":...,"career":...,...}
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    raw_spec_text TEXT,            -- 원문 스펙 입력
    parsed_spec   TEXT,            -- JSON (UserProfile)
    filter_prefs  TEXT,            -- JSON (PostingFilter)
    edit_token    TEXT UNIQUE,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_judgments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL REFERENCES users(id),
    posting_track_id INTEGER NOT NULL REFERENCES posting_tracks(id),
    eligible         INTEGER NOT NULL,  -- 0/1
    unmet            TEXT,              -- JSON list
    bonus_summary    TEXT,
    bonus_reasons    TEXT,              -- JSON list
    judged_at        TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, posting_track_id)
);
