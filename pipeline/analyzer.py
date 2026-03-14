"""
Gemini를 사용해 공고 첨부파일(PDF)을 분석하고 결과를 raw/analyses/{idx}.json에 저장.

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

사용법:
    python analyzer.py
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import google.generativeai as genai

import store
from models import Posting

load_dotenv(Path(__file__).parent / ".env")

ANALYSES_DIR = Path(__file__).parent / "raw" / "analyses"
MODEL_NAME = "gemini-2.5-flash"


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


def analyze_posting(posting: Posting, model: genai.GenerativeModel) -> dict:
    """
    공고 1건을 Gemini로 분석하고 결과 dict를 반환.
    TODO: 추출 항목(스키마) 확정 후 프롬프트 및 반환값 구체화 예정.
    """
    pdf_path = _pdf_path(posting)
    if pdf_path is None:
        raise ValueError("분석할 PDF 없음")

    uploaded = genai.upload_file(str(pdf_path))

    # TODO: 스키마 확정 후 구조화된 프롬프트로 교체
    response = model.generate_content([
        uploaded,
        "이 공고문의 주요 내용을 한국어로 요약해줘. 직무, 자격요건, 지원방법 위주로.",
    ])

    return {
        "idx": posting["idx"],
        "pdf_path": str(pdf_path),
        "raw_text": response.text,
        # TODO: 스키마 확정 후 구조화된 필드 추가
    }


def analyze_all_postings() -> None:
    ANALYSES_DIR.mkdir(parents=True, exist_ok=True)

    model = _load_client()
    postings = store.load_all()

    if not postings:
        print("저장된 공고가 없습니다.")
        return

    total = len(postings)
    analyzed = skipped = failed = 0

    for posting in postings:
        idx = posting.get("idx")
        out_path = ANALYSES_DIR / f"{idx}.json"

        if out_path.exists():
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
            result = analyze_posting(posting, model)
            out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[{idx}] 저장 완료: {out_path}")
            analyzed += 1
        except Exception as e:
            print(f"[{idx}] 분석 실패: {e}")
            failed += 1

    print(f"\n완료: 전체 {total}건 / 분석 {analyzed}건 / 건너뜀 {skipped}건 / 실패 {failed}건")


if __name__ == "__main__":
    analyze_all_postings()
