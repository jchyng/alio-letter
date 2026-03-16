# 파이프라인 단일 저장소.
#
# 로컬: SQLite (local.db) — main.py 시작 시 init_db() 한 번 호출.
# D1 전환 시: _connect() 제거, execute/fetchall을 D1 REST API 호출로 교체.
#   POST https://api.cloudflare.com/client/v4/accounts/{ID}/d1/database/{DB_ID}/query
#   Body: {"sql": "...", "params": [...]}
#
# 로컬 전용 파일 (gitignore: pipeline/raw/):
#   raw/user_profile.json  — CLI 사용자 프로필
#   raw/judgments.jsonl    — 로컬 판정 결과 검토용

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "local.db"
RAW_DIR = Path(__file__).parent / "raw"

SCHEMA_SQL = """
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
    raw_spec_text TEXT,
    parsed_spec   TEXT,            -- JSON (UserProfile)
    filter_prefs  TEXT,            -- JSON (PostingFilter)
    edit_token    TEXT UNIQUE,
    is_active     INTEGER NOT NULL DEFAULT 1,  -- 1=구독중, 0=구독중단
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
    sent_at          TEXT,              -- 이메일 발송 시각 (NULL = 미발송)
    UNIQUE(user_id, posting_track_id)
);
"""


def init_db() -> None:
    """테이블이 없으면 생성. 시작 시 항상 안전하게 호출 가능."""
    with _connect() as conn:
        conn.executescript(SCHEMA_SQL)
        # 기존 DB 컬럼 마이그레이션 (이미 있으면 무시)
        for sql in [
            "ALTER TABLE user_judgments ADD COLUMN sent_at TEXT",
            "ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1",
        ]:
            try:
                conn.execute(sql)
                conn.commit()
            except Exception:
                pass


def reset_db() -> None:
    """테이블 전체 삭제 후 재생성. 개발·테스트 초기화용."""
    drop_sql = """
    DROP TABLE IF EXISTS user_judgments;
    DROP TABLE IF EXISTS posting_tracks;
    DROP TABLE IF EXISTS users;
    DROP TABLE IF EXISTS postings;
    """
    with _connect() as conn:
        conn.executescript(drop_sql + SCHEMA_SQL)


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
    """공고 1건 INSERT OR REPLACE. alio_id(=idx)를 기준으로 덮어쓴다."""
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


def save_batch(records: list[dict]) -> None:
    """공고 여러 건 한꺼번에 upsert."""
    for r in records:
        upsert_posting(r)


def upsert_detail(posting: dict) -> None:
    """상세 크롤링 결과를 alio_id 기준으로 UPDATE.
    posting에는 idx와 변경할 필드만 담아 전달한다."""
    # Posting TypedDict 키 → DB 컬럼명 변환
    col_map = {"org": "org_name", "url": "posting_url"}
    fields = {k: v for k, v in posting.items() if k != "idx"}
    if not fields:
        return
    set_parts, params = [], []
    for k, v in fields.items():
        set_parts.append(f"{col_map.get(k, k)} = ?")
        params.append(v)
    params.append(str(posting.get("idx", "")))
    execute(
        f"UPDATE postings SET {', '.join(set_parts)} WHERE alio_id = ?",
        tuple(params),
    )


def load_all() -> list[dict]:
    """저장된 공고 전체를 Posting-compatible dict 리스트로 반환."""
    return [_row_to_posting(r) for r in fetchall("SELECT * FROM postings")]


def load_fetched() -> list[dict]:
    """상세 크롤링 완료된 공고만 반환 (employment_type NOT NULL). 필터링·판정 대상."""
    return [_row_to_posting(r)
            for r in fetchall("SELECT * FROM postings WHERE employment_type IS NOT NULL")]


def load_unfetched() -> list[dict]:
    """상세 크롤링 미완료 공고만 반환 (employment_type NULL)."""
    return [_row_to_posting(r)
            for r in fetchall("SELECT * FROM postings WHERE employment_type IS NULL")]


def is_empty() -> bool:
    """저장된 공고가 없으면 True."""
    rows = fetchall("SELECT COUNT(*) AS cnt FROM postings")
    return rows[0]["cnt"] == 0 if rows else True


def _row_to_posting(row: dict) -> dict:
    """DB row → Posting TypedDict-compatible dict (컬럼명 역변환)."""
    d = dict(row)
    try:
        d["idx"] = int(d.pop("alio_id", 0))
    except (ValueError, TypeError):
        d["idx"] = d.pop("alio_id", 0)
    d["org"] = d.pop("org_name", "")
    d["url"] = d.pop("posting_url", "")
    d.pop("posting_id", None)  # DB 내부 ID 제거
    return d


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


def load_all_tracks() -> list[dict]:
    """저장된 트랙 전체를 PostingTrack-compatible dict 리스트로 반환 (idx 포함)."""
    rows = fetchall(
        "SELECT pt.*, p.alio_id FROM posting_tracks pt "
        "JOIN postings p ON pt.posting_id = p.posting_id"
    )
    result = []
    for row in rows:
        d = dict(row)
        try:
            d["idx"] = int(d.pop("alio_id", 0))
        except (ValueError, TypeError):
            d["idx"] = d.pop("alio_id", 0)
        d.pop("posting_id", None)
        if isinstance(d.get("eligibility"), str):
            try:
                d["eligibility"] = json.loads(d["eligibility"])
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(d)
    return result


def is_analyzed(idx) -> bool:
    """해당 공고(idx=alio_id)가 이미 분석됐는지 확인."""
    rows = fetchall(
        "SELECT COUNT(*) AS cnt FROM posting_tracks pt "
        "JOIN postings p ON pt.posting_id = p.posting_id "
        "WHERE p.alio_id = ?",
        (str(idx),),
    )
    return rows[0]["cnt"] > 0 if rows else False


# ── 사용자 (웹 등록) ──────────────────────────────────────────────────────────

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


def load_all_users() -> list[dict]:
    """구독 중인(is_active=1) 사용자 전체 로드. daily.py에서 순회에 사용."""
    rows = fetchall("SELECT * FROM users WHERE is_active = 1")
    result = []
    for row in rows:
        d = dict(row)
        for field in ("parsed_spec", "filter_prefs"):
            if isinstance(d.get(field), str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        result.append(d)
    return result


def load_tracks_by_posting(posting_id: int) -> list[dict]:
    """특정 공고의 트랙만 로드. daily.py 매칭 후 트랙 조회 최적화용."""
    rows = fetchall(
        "SELECT pt.*, p.alio_id FROM posting_tracks pt "
        "JOIN postings p ON pt.posting_id = p.posting_id "
        "WHERE pt.posting_id = ?",
        (posting_id,),
    )
    result = []
    for row in rows:
        d = dict(row)
        try:
            d["idx"] = int(d.pop("alio_id", 0))
        except (ValueError, TypeError):
            d["idx"] = d.pop("alio_id", 0)
        d.pop("posting_id", None)
        if isinstance(d.get("eligibility"), str):
            try:
                d["eligibility"] = json.loads(d["eligibility"])
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(d)
    return result


def mark_sent(user_id: int, posting_track_id: int) -> None:
    """user_judgments.sent_at에 현재 시각 기록."""
    execute(
        "UPDATE user_judgments SET sent_at = datetime('now') "
        "WHERE user_id = ? AND posting_track_id = ?",
        (user_id, posting_track_id),
    )


def load_unsent_judgments(user_id: int) -> list[dict]:
    """sent_at IS NULL인 판정 결과 조회. 이메일 발송 대상 추출용."""
    rows = fetchall(
        """
        SELECT uj.*, pt.track_name, pt.positions, pt.total_positions,
               pt.eligibility, pt.posting_id,
               p.alio_id, p.title, p.org_name, p.posting_url,
               p.deadline, p.salary_url, p.bonus_points
        FROM user_judgments uj
        JOIN posting_tracks pt ON uj.posting_track_id = pt.id
        JOIN postings p ON pt.posting_id = p.posting_id
        WHERE uj.user_id = ? AND uj.sent_at IS NULL
        """,
        (user_id,),
    )
    result = []
    for row in rows:
        d = dict(row)
        for field in ("unmet", "bonus_reasons", "eligibility"):
            if isinstance(d.get(field), str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        try:
            d["idx"] = int(d.pop("alio_id", 0))
        except (ValueError, TypeError):
            d["idx"] = d.pop("alio_id", 0)
        result.append(d)
    return result


# ── 판정 결과 (웹 사용자) ──────────────────────────────────────────────────────

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


# ── 로컬 개발 전용 (pipeline/raw/ — gitignore 적용) ──────────────────────────

_PROFILE_FILE = RAW_DIR / "user_profile.json"
_JUDGMENTS_FILE = RAW_DIR / "judgments.jsonl"


def save_user_profile(profile: dict) -> None:
    """사용자 프로필을 JSON 파일로 저장 (CLI 개발 전용)."""
    RAW_DIR.mkdir(exist_ok=True)
    with _PROFILE_FILE.open("w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


def load_user_profile() -> dict | None:
    """저장된 사용자 프로필 반환 (CLI 개발 전용). 없으면 None."""
    if not _PROFILE_FILE.exists():
        return None
    with _PROFILE_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def save_judgments_local(judgments: list[dict]) -> None:
    """판정 결과를 JSONL 파일로 저장 (CLI 검토용). 재실행 시 덮어씀."""
    if not judgments:
        return
    RAW_DIR.mkdir(exist_ok=True)
    with _JUDGMENTS_FILE.open("w", encoding="utf-8") as f:
        for j in judgments:
            f.write(json.dumps(j, ensure_ascii=False) + "\n")


def clear() -> None:
    """postings 전체 삭제 (테스트 초기화용). 연관 tracks도 CASCADE 삭제."""
    execute("DELETE FROM posting_tracks WHERE posting_id IN (SELECT posting_id FROM postings)")
    execute("DELETE FROM postings")


def _connect() -> sqlite3.Connection:
    """TODO: MIGRATE TO D1 — 이 함수 제거. D1은 영속 커넥션 없이 REST API 호출."""
    return sqlite3.connect(DB_PATH)
