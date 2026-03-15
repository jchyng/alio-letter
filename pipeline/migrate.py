"""
JSONL → D1 데이터 이전 스크립트
실행: python migrate.py

postings.jsonl  → D1 postings 테이블
analyses.jsonl  → D1 posting_tracks 테이블
judgments.jsonl → skip (user_id 없으므로 익명 판정은 이전 불가)

D1 전환 전까지는 SQLite(local.db)에 먼저 쓰고
`wrangler d1 export` / REST API로 D1에 업로드한다.
"""

import store
import db


def migrate_postings() -> int:
    postings = store.load_all()
    for p in postings:
        db.upsert_posting(p)
    return len(postings)


def migrate_tracks() -> int:
    tracks = store.load_all_tracks()
    # posting_tracks는 alio_id FK가 필요하므로 postings 먼저 있어야 함
    db.save_tracks(tracks)
    return len(tracks)


if __name__ == "__main__":
    db.init_db()
    n_postings = migrate_postings()
    print(f"postings 이전: {n_postings}건")
    n_tracks = migrate_tracks()
    print(f"posting_tracks 이전: {n_tracks}건")
    print("judgments: user_id 없음 → skip")
