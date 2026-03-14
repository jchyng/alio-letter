# TODO: MIGRATE TO D1
# 현재: sqlite3 (로컬 파일)
# D1 전환 시: 아래 execute/fetchall을 Cloudflare D1 REST API 호출로 교체
#   POST https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/d1/database/{DB_ID}/query
#   Headers: {"Authorization": "Bearer {API_TOKEN}"}
#   Body:    {"sql": "...", "params": [...]}
# Cloudflare Functions 내부에서는 REST API 대신 env.DB.prepare(...) 바인딩 사용

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "local.db"

SCHEMA_SQL = """
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
    attachment_converted TEXT
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


def _connect() -> sqlite3.Connection:
    """TODO: MIGRATE TO D1 — 이 함수 제거. D1은 영속 커넥션 없이 REST API 호출."""
    return sqlite3.connect(DB_PATH)
