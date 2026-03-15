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
from pathlib import Path

from dotenv import load_dotenv
import google.generativeai as genai

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
      "track_name": "채용구분명 (예: 대졸수준-일반, 고졸수준, 별정직-기술담당원)",
      "positions": "모집분야별 인원 원문 (예: 사무 8, ICT 7, 기계 25)",
      "total_positions": 합계인원(정수),
      "eligibility": {
        "education": "학력 요건 원문",
        "career": "경력 요건 원문",
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
- 요건이 '제한 없음'이면 그대로 '제한 없음'으로 기재
- bonus_points는 공고 전체에 적용되는 가산점을 하나의 문자열로 요약
- JSON 외 다른 텍스트(```json 등 포함) 절대 출력 금지"""


def _load_client() -> genai.GenerativeModel:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY가 .env에 없습니다.")
        sys.exit(1)
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(MODEL_NAME)


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
        track: PostingTrack = {
            "idx": idx,
            "track_name": t.get("track_name", ""),
            "positions": t.get("positions", ""),
            "total_positions": int(t.get("total_positions", 0)),
            "eligibility": t.get("eligibility", {}),
        }
        tracks.append(track)
    return tracks, bonus_points, notes


def analyze_posting(posting: Posting, model: genai.GenerativeModel) -> tuple[list[PostingTrack], str, str]:
    """
    공고 1건을 Gemini로 분석.
    반환: (tracks, bonus_points, notes)
    """
    pdf_path = _pdf_path(posting)
    if pdf_path is None:
        raise ValueError("분석할 PDF 없음")

    uploaded = genai.upload_file(str(pdf_path))
    response = model.generate_content([uploaded, PROMPT])
    return _parse_response(posting["idx"], response.text)


def analyze_all_postings() -> None:
    model = _load_client()
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
            tracks, bonus_points, notes = analyze_posting(posting, model)

            db.save_tracks(tracks)

            if bonus_points:
                db.upsert_detail({"idx": idx, "bonus_points": bonus_points})

            if notes:
                db.upsert_detail({"idx": idx, "notes": notes})

            print(f"[{idx}] 저장 완료: 트랙 {len(tracks)}개")
            analyzed += 1
        except Exception as e:
            print(f"[{idx}] 분석 실패: {e}")
            failed += 1

    print(f"\n완료: 전체 {total}건 / 분석 {analyzed}건 / 건너뜀 {skipped}건 / 실패 {failed}건")


if __name__ == "__main__":
    analyze_all_postings()
