"""
파이프라인 전체 흐름 N건 테스트.

사용법:
    python test_pipeline.py
"""

import json
from pathlib import Path

import scraper
import store
from analyzer import analyze_posting, _load_client

RAW_DIR = Path(__file__).parent / "raw"
TARGET_COUNT = 5  # 수집할 PDF 공고 수 (Gemini 무료 분당 5회 제한)


def main() -> None:
    # 기존 데이터 초기화
    store.clear()
    analyses = RAW_DIR / "analyses.jsonl"
    if analyses.exists():
        analyses.unlink()

    # 1단계: PDF 첨부파일이 있는 공고 N건 찾기
    print(f"=== 1단계: 목록 수집 (PDF 공고 {TARGET_COUNT}건 탐색) ===")
    targets = []
    for page in range(1, 20):
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
                targets.append(detail)
                store.save(detail)
                print(f"  [{len(targets)}] [{detail['idx']}] {detail['title']}")
            if len(targets) >= TARGET_COUNT:
                break
        if len(targets) >= TARGET_COUNT:
            break

    if not targets:
        print("PDF 첨부파일이 있는 공고를 찾지 못했습니다.")
        return

    print(f"\n총 {len(targets)}건 수집 완료")

    # 2단계: Gemini 분석
    print(f"\n=== 2단계: Gemini 분석 ({len(targets)}건) ===")
    model = _load_client()
    analyzed = failed = 0

    for posting in targets:
        idx = posting["idx"]
        print(f"\n[{idx}] {posting['title']}")
        try:
            tracks, bonus_points, notes = analyze_posting(posting, model)

            store.save_tracks(tracks)
            if bonus_points:
                store.upsert_detail({"idx": idx, "bonus_points": bonus_points})
            if notes:
                store.upsert_detail({"idx": idx, "notes": notes})

            print(f"  bonus_points: {bonus_points[:60]}...")
            if notes:
                print(f"  notes: {notes[:60]}...")
            print(f"  트랙 수: {len(tracks)}")
            for t in tracks:
                print(f"    - {t['track_name']}: {t['total_positions']}명 / {t['positions']}")
            analyzed += 1
        except Exception as e:
            print(f"  실패: {e}")
            failed += 1

    print(f"\n=== 결과 요약 ===")
    print(f"분석 완료: {analyzed}건 / 실패: {failed}건")

    all_tracks = store.load_all_tracks()
    total_positions = sum(t.get("total_positions", 0) for t in all_tracks)
    print(f"총 트랙 수: {len(all_tracks)}")
    print(f"총 채용인원: {total_positions}명")
    if analyzed > 0:
        print(f"공고당 평균 트랙: {len(all_tracks) / analyzed:.1f}개")
        print(f"공고당 평균 채용인원: {total_positions / analyzed:.1f}명")

    print("\n=== analyses.jsonl ===")
    for t in all_tracks:
        print(json.dumps(t, ensure_ascii=False))


if __name__ == "__main__":
    main()
