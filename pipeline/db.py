# TODO: MIGRATE TO D1
# 현재: sqlite3 (로컬 파일)
# D1 전환 시: 아래 execute/fetchall을 Cloudflare D1 REST API 호출로 교체
#   POST https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/d1/database/{DB_ID}/query
#   Headers: {"Authorization": "Bearer {API_TOKEN}"}
#   Body:    {"sql": "...", "params": [...]}
# Cloudflare Functions 내부에서는 REST API 대신 env.DB.prepare(...) 바인딩 사용

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "local.db"

SCHEMA_SQL = """
DROP TABLE IF EXISTS user_judgments;
DROP TABLE IF EXISTS posting_tracks;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS postings;

CREATE TABLE postings (
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

CREATE TABLE posting_tracks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    posting_id      INTEGER NOT NULL REFERENCES postings(posting_id),
    track_name      TEXT NOT NULL,
    positions       TEXT,
    total_positions INTEGER,
    eligibility     TEXT   -- JSON {"education":...,"career":...,...}
);

CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    raw_spec_text TEXT,            -- 원문 스펙 입력
    parsed_spec   TEXT,            -- JSON (UserProfile)
    filter_prefs  TEXT,            -- JSON (PostingFilter)
    edit_token    TEXT UNIQUE,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE user_judgments (
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
"""


def init_db():
    """테이블 초기화. D1 전환 시: wrangler d1 execute로 schema.sql 적용."""
    with _connect() as conn:
        conn.executescript(SCHEMA_SQL)


def execute(sql: str, params: tuple = ()) -> None:
    """쓰기 쿼리 실행."""
    with _connect() as conn:
        conn.execute(sql, params)
        conn.commit()


def fetchall(sql: str, params: tuple = ()) -> list[dict]:
    """읽기 쿼리 실행 → dict 리스트 반환."""
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


# ── 공고 ────────────────────────────────────────────────────────────────────

def upsert_posting(posting: dict) -> None:
    """공고 1건 INSERT OR REPLACE. alio_id를 기준으로 덮어쓴다."""
    execute(
        """
        INSERT OR REPLACE INTO postings
            (alio_id, title, org_name, posting_url, deadline, registered,
             ncs, work_field, employment_type, location, education,
             recruit_type, is_substitute, salary_url, preferred,
             attachment_path, attachment_ext, attachment_converted,
             bonus_points, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            str(posting.get("idx", "")),
            posting.get("title", ""),
            posting.get("org", ""),
            posting.get("url", ""),
            posting.get("deadline", ""),
            posting.get("registered"),
            posting.get("ncs"),
            posting.get("work_field"),
            posting.get("employment_type"),
            posting.get("location"),
            posting.get("education"),
            posting.get("recruit_type"),
            posting.get("is_substitute"),
            posting.get("salary_url"),
            posting.get("preferred"),
            posting.get("attachment_path"),
            posting.get("attachment_ext"),
            posting.get("attachment_converted"),
            posting.get("bonus_points"),
            posting.get("notes"),
        ),
    )


# ── 트랙 ────────────────────────────────────────────────────────────────────

def save_tracks(tracks: list[dict]) -> None:
    """트랙 여러 건 INSERT. posting_id는 alio_id로 조회해 연결."""
    for track in tracks:
        rows = fetchall(
            "SELECT posting_id FROM postings WHERE alio_id = ?",
            (str(track.get("idx", "")),),
        )
        if not rows:
            continue
        posting_id = rows[0]["posting_id"]
        eligibility = track.get("eligibility")
        execute(
            """
            INSERT INTO posting_tracks
                (posting_id, track_name, positions, total_positions, eligibility)
            VALUES (?,?,?,?,?)
            """,
            (
                posting_id,
                track.get("track_name", ""),
                track.get("positions"),
                track.get("total_positions"),
                json.dumps(eligibility, ensure_ascii=False) if eligibility else None,
            ),
        )


# ── 사용자 ───────────────────────────────────────────────────────────────────

def save_user(email: str, name: str, raw_spec_text: str,
              parsed_spec: dict | None, filter_prefs: dict | None,
              edit_token: str) -> int:
    """사용자 INSERT OR REPLACE. 생성된 id 반환."""
    execute(
        """
        INSERT OR REPLACE INTO users
            (email, name, raw_spec_text, parsed_spec, filter_prefs, edit_token)
        VALUES (?,?,?,?,?,?)
        """,
        (
            email,
            name,
            raw_spec_text,
            json.dumps(parsed_spec, ensure_ascii=False) if parsed_spec else None,
            json.dumps(filter_prefs, ensure_ascii=False) if filter_prefs else None,
            edit_token,
        ),
    )
    rows = fetchall("SELECT id FROM users WHERE email = ?", (email,))
    return rows[0]["id"]


# ── 판정 결과 ────────────────────────────────────────────────────────────────

def save_judgments(user_id: int, judgments: list[dict]) -> None:
    """판정 결과 INSERT OR REPLACE. posting_track_id는 (alio_id, track_name)으로 조회."""
    for j in judgments:
        rows = fetchall(
            """
            SELECT pt.id
            FROM posting_tracks pt
            JOIN postings p ON pt.posting_id = p.posting_id
            WHERE p.alio_id = ? AND pt.track_name = ?
            """,
            (str(j.get("idx", "")), j.get("track_name", "")),
        )
        if not rows:
            continue
        posting_track_id = rows[0]["id"]
        execute(
            """
            INSERT OR REPLACE INTO user_judgments
                (user_id, posting_track_id, eligible, unmet, bonus_summary, bonus_reasons)
            VALUES (?,?,?,?,?,?)
            """,
            (
                user_id,
                posting_track_id,
                1 if j.get("eligible") else 0,
                json.dumps(j.get("unmet", []), ensure_ascii=False),
                j.get("bonus_summary"),
                json.dumps(j.get("bonus_reasons", []), ensure_ascii=False),
            ),
        )


def _connect() -> sqlite3.Connection:
    """TODO: MIGRATE TO D1 — 이 함수 제거. D1은 영속 커넥션 없이 REST API 호출."""
    return sqlite3.connect(DB_PATH)
