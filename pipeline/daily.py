"""
데일리 파이프라인 자동화 진입점.

# 실행 흐름
# 1. 신규 공고 수집 (scraper)
# 2. 공고 분석 (analyzer/Gemini)
# 3. 활성 사용자 목록 조회
# 4. 사용자별: 필터 → 트랙 로드 → judge → save_judgments → mailer → mark_sent
# 5. 결과 요약 출력

# 스케줄링 (crontab)
# 08:00 — 수집+분석만:  python daily.py --skip-mail
# 09:00 — 발송만:       python daily.py --skip-scrape

사용법:
    python daily.py               # 전체 실행
    python daily.py --skip-scrape # 수집 건너뜀 (개발·테스트용)
    python daily.py --skip-mail   # 발송 건너뜀 (수집·분석만)
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import db
import scraper
import filter as posting_filter
import mailer

# judge/genai는 실행 시점에 lazy import (google-genai 선택적 의존성)
_judge = None


def _load_gemini():
    """Gemini 클라이언트 로드. google-genai 미설치 또는 API 키 없으면 None 반환."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[daily] GEMINI_API_KEY 없음 — 판정 단계 skip")
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError:
        print("[daily] google-genai 미설치 — 판정 단계 skip")
        return None


def _judge_track(profile, track, bonus_points, model, preferred_work_fields=None):
    """judge 모듈 lazy import 후 단일 트랙 판정."""
    import judge
    return judge.judge_track(profile, track, bonus_points, model, preferred_work_fields)


def run(skip_scrape: bool = False, skip_mail: bool = False) -> None:
    db.init_db()

    # 1. 공고 수집
    if skip_scrape:
        print("[daily] --skip-scrape: 수집 단계 건너뜀")
    else:
        print("[daily] 신규 공고 수집 중...")
        n = scraper.fetch_new_postings()
        print(f"[daily] 수집 완료: {n}건")
        scraper.fetch_detail_postings()

    # 2. 공고 분석 (google-genai lazy import)
    try:
        from analyzer import analyze_all_postings
        analyze_all_postings()
    except ImportError:
        print("[daily] google-genai 미설치 — 분석 단계 skip")

    # 3. 사용자 목록
    users = db.load_all_users()
    if not users:
        print("[daily] 등록된 사용자 없음 — 종료")
        return

    print(f"[daily] 사용자 {len(users)}명 처리 시작")
    # 상세 크롤링 완료된 공고만 필터링·판정 대상 (employment_type NULL인 것 제외)
    all_postings = db.load_fetched()
    # idx → posting_id 매핑 (사용자 루프 밖에서 1회 조회 — N×M 쿼리 방지)
    idx_to_posting_id = db.load_posting_id_map()

    gemini_client = _load_gemini()

    sent_total = 0
    judged_total = 0

    for user in users:
        user_id = user["id"]
        name = user.get("name", "")
        email = user.get("email", "")
        profile = user.get("parsed_spec") or {}
        prefs = user.get("filter_prefs") or {}

        # 4a. 필터링
        matched = posting_filter.filter_postings(all_postings, prefs)
        if not matched:
            print(f"[daily] {name}({email}): 매칭 공고 없음")
            continue

        print(f"[daily] {name}({email}): {len(matched)}건 매칭")

        # 4b-c. 트랙 로드 + 판정 (이미 판정된 트랙은 건너뜀 — 중복 Gemini 호출 방지)
        if gemini_client and profile:
            already_judged = db.load_judged_track_ids(user_id)
            for posting in matched:
                posting_id = idx_to_posting_id.get(posting.get("idx"))
                if not posting_id:
                    continue
                tracks = db.load_tracks_by_posting(posting_id)
                if not tracks:
                    continue

                # 미판정 트랙만 추려서 Gemini 호출
                new_tracks = [t for t in tracks if t.get("id") not in already_judged]
                if not new_tracks:
                    continue

                bonus_points = posting.get("bonus_points", "")
                judgments = []
                preferred_work_fields = prefs.get("work_fields") or None
                for track in new_tracks:
                    try:
                        j = _judge_track(profile, track, bonus_points, gemini_client, preferred_work_fields)
                        j["idx"] = posting.get("idx")
                        judgments.append(j)
                    except Exception as e:
                        print(f"  판정 실패 (idx={posting.get('idx')}, track={track.get('track_name')}): {e}")

                if judgments:
                    db.save_judgments(user_id, judgments)
                    judged_total += len(judgments)

        # 4d. 이메일 발송
        if skip_mail:
            continue

        unsent = db.load_unsent_judgments(user_id)
        if not unsent:
            continue

        # 공고별로 그룹화
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
                    "track_ids": [],
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
            posting_map[idx]["track_ids"].append(row.get("posting_track_id"))

        items = [{"posting": v["posting"], "tracks": v["tracks"]} for v in posting_map.values()]
        edit_token = user.get("edit_token", "")
        html = mailer.build_email_html(name, items, edit_token=edit_token)
        subject = f"[alio-letter] 오늘의 공고 {len(posting_map)}건"

        ok = mailer.send_email(email, name, subject, html)
        if ok:
            # mark_sent for all unsent judgments
            for row in unsent:
                db.mark_sent(user_id, row["posting_track_id"])
            sent_total += 1

    print(f"\n[daily] 완료 — 판정 {judged_total}건, 발송 {sent_total}명")


if __name__ == "__main__":
    skip_scrape = "--skip-scrape" in sys.argv
    skip_mail = "--skip-mail" in sys.argv
    run(skip_scrape=skip_scrape, skip_mail=skip_mail)
