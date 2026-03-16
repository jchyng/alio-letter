"""
Gemini를 사용해 공고 첨부파일(PDF)을 분석하고 결과를 DB(posting_tracks)에 저장.

# 왜 scraper와 분리해서 실행하는가?
#
# 1. 스키마 미확정: 추출 항목이 자주 바뀌는 동안 재분석만 하면 됨.
#    analyzer를 scraper에 묶으면 재분석 시 재크롤링이 필요해진다.
#
# 2. 실패 모드가 다름: 크롤러는 네트워크/사이트 문제, Gemini는 API 한도/과금 문제.
#    묶으면 Gemini 오류가 크롤링을 중단시키거나, 재시도 시 API 비용이 중복 발생한다.
#
# 3. Gemini 업로드 레이턴시: genai.upload_file()은 수초~수십초 걸린다.
#    크롤링 루프에 끼우면 전체 스크래핑 속도가 그만큼 느려진다.
#
# → 오케스트레이션이 필요해지면 scraper/analyzer를 내부에서 합치지 말고
#   main.py 같은 별도 진입점에서 순서를 제어한다.

# Gemini 응답 구조:
# {
#   "bonus_points": "...",   → Posting에 upsert
#   "notes": "...",          → Posting에 upsert
#   "tracks": [              → analyses.jsonl에 트랙 단위로 저장
#     {
#       "track_name": "...",
#       "positions": "...",
#       "total_positions": 79,
#       "eligibility": { "education": "...", ... }
#     },
#     ...
#   ]
# }

사용법:
    python analyzer.py
"""

import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

import db
from models import Posting, PostingTrack

load_dotenv(Path(__file__).parent / ".env")

MODEL_NAME = "gemini-2.5-flash"

PROMPT = """이 채용공고 PDF를 분석하여 아래 JSON 형식으로만 응답하라. 설명 없이 JSON만 출력할 것.

{
  "bonus_points": "가산점 내용 전체를 한 문자열로 요약 (없으면 '해당 없음')",
  "notes": "중요하지만 특정 항목으로 분류하기 어려운 정보 (예: 보수, 근무시간, 특이 조건). 없으면 빈 문자열.",
  "tracks": [
    {
      "track_name": "자격요건이 분리된 채용단위명. 아래 규칙 참고.",
      "positions": "모집분야별 인원 원문 (예: 사무 8, ICT 7, 기계 25)",
      "total_positions": 합계인원(정수),
      "eligibility": {
        "education": "학력 요건 원문",
        "career": "경력 요건 원문 (주요업무·직무내용은 제외. 순수하게 요구되는 경력 연수·분야만)",
        "age": "연령 요건 원문",
        "language": "어학 요건 원문",
        "certificate": "자격증 요건 원문",
        "etc": "기타 요건 원문 (병역, 결격사유 등)"
      }
    }
  ]
}

규칙:
- tracks 배열에 공고 내 모든 채용구분을 빠짐없이 포함할 것
- track_name은 자격요건 표의 '구분' 컬럼 값을 우선 사용. '구분'이 없으면 '채용분야' 컬럼 값 사용
  - 구분(대분류)과 채용분야(세부직종)가 별도 컬럼으로 나뉠 경우: "구분(채용분야)" 형태로 결합 (예: 시니어인턴(조경), 신입(사무행정))
  - 직급명(6급, 4급, 주임 등)은 track_name에 포함하지 않음
- 요건이 '제한 없음'이면 그대로 '제한 없음'으로 기재
- bonus_points는 공고 전체에 적용되는 가산점을 하나의 문자열로 요약
- PDF에 명시된 내용만 기재. 추론하거나 없는 내용을 추가하지 말 것
- JSON 외 다른 텍스트(```json 등 포함) 절대 출력 금지"""


_RETRY_DELAYS = [1, 2, 4]  # 최대 3회 재시도, 초 단위 backoff


def _gemini_call_with_retry(fn):
    """Gemini API 호출을 최대 3회 재시도. 실패 시 마지막 예외를 raise."""
    last_exc = None
    for delay in [0] + _RETRY_DELAYS:
        if delay:
            print(f"  Gemini 재시도 대기 {delay}s...")
            time.sleep(delay)
        try:
            return fn()
        except Exception as e:
            print(f"  Gemini 호출 실패: {e}")
            last_exc = e
    raise last_exc


def _load_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY가 .env에 없습니다.")
        sys.exit(1)
    return genai.Client(api_key=api_key)


def _pdf_path(posting: Posting) -> Path | None:
    """분석할 PDF 경로 결정. attachment_converted 우선, 없으면 ext==pdf인 attachment_path."""
    converted = posting.get("attachment_converted")
    if converted:
        p = Path(converted)
        if p.exists():
            return p

    ext = posting.get("attachment_ext", "").lower()
    path = posting.get("attachment_path")
    if ext == "pdf" and path:
        p = Path(path)
        if p.exists():
            return p

    return None


def _parse_response(idx: int, raw: str) -> tuple[list[PostingTrack], str, str]:
    """
    Gemini 응답 JSON을 파싱하여 (tracks, bonus_points, notes) 반환.
    응답에 ```json 블록이 포함된 경우 자동으로 추출.
    """
    text = raw.strip()
    # Gemini가 ```json ... ``` 으로 감쌀 경우 대비
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()

    data = json.loads(text)
    bonus_points: str = data.get("bonus_points", "")
    notes: str = data.get("notes", "")
    tracks: list[PostingTrack] = []
    for t in data.get("tracks", []):
        eligibility = t.get("eligibility", {})
        # 빈 문자열 → '해당 없음' 정규화 (모델이 간헐적으로 빈 값을 반환하는 경우 대비)
        eligibility = {k: (v if v else "해당 없음") for k, v in eligibility.items()}
        track: PostingTrack = {
            "idx": idx,
            "track_name": t.get("track_name", ""),
            "positions": t.get("positions", ""),
            "total_positions": int(t.get("total_positions", 0)),
            "eligibility": eligibility,
        }
        tracks.append(track)
    return tracks, bonus_points, notes


def analyze_posting(posting: Posting, client: genai.Client) -> tuple[list[PostingTrack], str, str]:
    """
    공고 1건을 Gemini로 분석.
    반환: (tracks, bonus_points, notes)
    """
    pdf_path = _pdf_path(posting)
    if pdf_path is None:
        raise ValueError("분석할 PDF 없음")

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    response = _gemini_call_with_retry(lambda: client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            PROMPT,
        ],
        config=types.GenerateContentConfig(
            # thinking_budget=0: 추출 태스크에서 hallucination 방지.
            # 2.5-flash는 추론(thinking) 모델이라 chain-of-thought 과정에서
            # 다른 섹션(etc의 규정 조항 등)을 참조해 없는 내용을 education 등에 추가함.
            # thinking을 끄면 단순 추출 모드로 동작해 PDF 원문만 그대로 반환.
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            temperature=0.0,  # 응답 일관성 확보 — 같은 PDF에서 매번 동일한 결과 보장
        ),
    ))
    return _parse_response(posting["idx"], response.text)


def analyze_all_postings() -> None:
    client = _load_client()
    postings = db.load_all()

    if not postings:
        print("저장된 공고가 없습니다.")
        return

    total = len(postings)
    analyzed = skipped = failed = 0

    for posting in postings:
        idx = posting.get("idx")

        if db.is_analyzed(idx):
            print(f"[{idx}] 이미 분석됨, 건너뜀")
            skipped += 1
            continue

        pdf_path = _pdf_path(posting)
        if pdf_path is None:
            print(f"[{idx}] PDF 없음, 건너뜀")
            skipped += 1
            continue

        print(f"[{idx}] 분석 중: {pdf_path.name}")
        try:
            tracks, bonus_points, notes = analyze_posting(posting, client)

            db.save_tracks(tracks)

            if bonus_points:
                db.upsert_detail({"idx": idx, "bonus_points": bonus_points})

            if notes:
                db.upsert_detail({"idx": idx, "notes": notes})

            print(f"[{idx}] 저장 완료: 트랙 {len(tracks)}개")
            analyzed += 1
            time.sleep(0.5)  # rate limit 예방
        except Exception as e:
            print(f"[{idx}] 분석 실패: {e}")
            failed += 1

    print(f"\n완료: 전체 {total}건 / 분석 {analyzed}건 / 건너뜀 {skipped}건 / 실패 {failed}건")


if __name__ == "__main__":
    analyze_all_postings()
