"""
이메일 HTML 렌더링 테스트 스크립트.

흐름:
    1. 테스트 사용자 등록
    2. DB 공고 전체 로드 → 판정
    3. mailer.build_email_html() 호출
    4. /tmp/email_preview.html 저장 (이메일 발송 없음)

사용법:
    cd pipeline && python test_email.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import db
import filter as posting_filter
import judge
import mailer

# ── 1. DB 초기화 ─────────────────────────────────────────────────────────────
db.init_db()

# ── 2. 테스트 사용자 등록 ────────────────────────────────────────────────────
TEST_EMAIL = "test@alio-letter.dev"
TEST_NAME = "홍길동"
TEST_TOKEN = "test-token-1234"
TEST_PARSED_SPEC = {
    "education": "학력무관",
    "career_years": 2,
    "career_fields": [],
    "birth_year": 1995,
    "languages": [],
    "certificates": [],
    "military": "병역필",
    "disability_grade": "해당없음",
    "veteran_type": "해당없음",
    "is_low_income": False,
    "is_north_korean_defector": False,
    "is_independent_youth": False,
    "is_multicultural_child": False,
}

user_id = db.save_user(
    email=TEST_EMAIL,
    name=TEST_NAME,
    raw_spec_text="테스트용 프로필",
    parsed_spec=TEST_PARSED_SPEC,
    filter_prefs={},  # 빈 객체 → 모든 공고 매칭
    edit_token=TEST_TOKEN,
)
print(f"테스트 사용자 등록: user_id={user_id}")

# ── 3. 공고 로드 → 필터링 ────────────────────────────────────────────────────
all_postings = db.load_fetched()
matched = posting_filter.filter_postings(all_postings, {})
print(f"공고 매칭: {len(matched)}건")

if not matched:
    print("매칭된 공고가 없습니다. DB를 확인하세요.")
    sys.exit(1)

# ── 4. 트랙 판정 ─────────────────────────────────────────────────────────────
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("GEMINI_API_KEY가 .env에 없습니다.")
    sys.exit(1)

from google import genai
client = genai.Client(api_key=api_key)

# posting_id 맵 (alio_id → posting_id)
posting_id_map = db.load_posting_id_map()

# 이미 판정된 트랙 ID (중복 판정 방지)
judged_ids = db.load_judged_track_ids(user_id)

judgments = []
for posting in matched:
    idx = posting.get("idx")
    posting_id = posting_id_map.get(idx)
    if posting_id is None:
        continue

    tracks = db.load_tracks_by_posting(posting_id)
    bonus_points = posting.get("bonus_points", "")

    for track in tracks:
        if track.get("id") in judged_ids:
            continue
        track_name = track.get("track_name", "")
        print(f"  판정 중: idx={idx} '{track_name}'")
        try:
            j = judge.judge_track(TEST_PARSED_SPEC, track, bonus_points, client)
            judgments.append(j)
            status = "충족" if j["eligible"] else "미충족"
            print(f"    → {status}, 가산점 {j['bonus_summary']}")
        except Exception as e:
            print(f"    판정 실패: {e}")

if judgments:
    db.save_judgments(user_id, judgments)
    print(f"\n판정 저장: {len(judgments)}건")

# ── 5. 이메일 HTML 생성 ──────────────────────────────────────────────────────
unsent = db.load_unsent_judgments(user_id)
if not unsent:
    print("발송할 판정 결과가 없습니다.")
    sys.exit(1)

# daily.py와 동일한 posting_map 그룹화
posting_map: dict[int, dict] = {}
for row in unsent:
    idx = row.get("idx")
    if idx not in posting_map:
        posting_map[idx] = {
            "posting": {
                "title": row.get("title"),
                "org_name": row.get("org_name"),
                "deadline": row.get("deadline"),
                "posting_url": row.get("posting_url"),
                "salary_url": row.get("salary_url"),
            },
            "tracks": [],
        }
    posting_map[idx]["tracks"].append({
        "track": {
            "track_name": row.get("track_name"),
            "positions": row.get("positions"),
            "total_positions": row.get("total_positions"),
        },
        "judgment": {
            "eligible": bool(row.get("eligible")),
            "unmet": row.get("unmet", []),
            "bonus_summary": row.get("bonus_summary", "없음"),
            "bonus_reasons": row.get("bonus_reasons", []),
        },
    })

items = [{"posting": v["posting"], "tracks": v["tracks"]} for v in posting_map.values()]
html = mailer.build_email_html(TEST_NAME, items, edit_token=TEST_TOKEN)

# ── 6. HTML 파일 저장 ────────────────────────────────────────────────────────
out_path = Path("/tmp/email_preview.html")
out_path.write_text(html, encoding="utf-8")
print(f"\nHTML 저장 완료: {out_path}")
print(f"공고 {len(posting_map)}건 포함")
