"""
파이프라인 전체 흐름 1건 테스트.

사용법:
    python test_pipeline.py
"""

import json
from pathlib import Path

import scraper
import store
from analyzer import analyze_posting, _load_client

RAW_DIR = Path(__file__).parent / "raw"


def main() -> None:
    # 기존 데이터 초기화
    store.clear()
    analyses = RAW_DIR / "analyses.jsonl"
    if analyses.exists():
        analyses.unlink()

    # 1단계: PDF 첨부파일이 있는 공고 1건 찾기
    print("=== 1단계: 목록 수집 (PDF 공고 1건 탐색) ===")
    target = None
    for page in range(1, 6):
        rows = scraper._fetch_page(page)
        if not rows:
            break
        for row in rows:
            detail = scraper._fetch_detail(row)
            ext = detail.get("attachment_ext", "")
            converted = detail.get("attachment_converted", "")
            path = detail.get("attachment_path", "")
            has_pdf = ext == "pdf" and path or converted
            if has_pdf:
                target = detail
                break
        if target:
            break

    if not target:
        print("PDF 첨부파일이 있는 공고를 찾지 못했습니다.")
        return

    store.save(target)
    print(f"저장: [{target['idx']}] {target['title']}")
    print(f"attachment_ext: {target.get('attachment_ext')}")
    print(f"attachment_path: {target.get('attachment_path')}")
    print(f"attachment_converted: {target.get('attachment_converted')}")

    # 3단계: Gemini 분석
    print("\n=== 3단계: Gemini 분석 ===")
    posting = target
    model = _load_client()
    tracks, bonus_points = analyze_posting(posting, model)

    store.save_tracks(tracks)
    if bonus_points:
        store.upsert_detail({"idx": posting["idx"], "bonus_points": bonus_points})

    print(f"\n[결과]")
    print(f"bonus_points: {bonus_points[:80]}...")
    print(f"트랙 수: {len(tracks)}")
    for t in tracks:
        print(f"  - {t['track_name']}: {t['total_positions']}명 / {t['positions']}")

    print("\n=== analyses.jsonl ===")
    for t in store.load_all_tracks():
        print(json.dumps(t, ensure_ascii=False))


if __name__ == "__main__":
    main()
