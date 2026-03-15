"""
파이프라인 진입점.

사용법:
    python main.py          # 대화형 메뉴
    python main.py 1        # 공고 목록 수집
    python main.py 2        # 상세 공고 수집
    python main.py 3        # 분석
"""

import sys

import db
import scraper
import user_input
import judge
from analyzer import analyze_all_postings

MENU = """
=== alio-letter 파이프라인 ===
1. 공고 목록 수집
2. 상세 공고 수집
3. 분석 (Gemini)
4. 사용자 정보 입력/수정
5. 자격요건 판정
0. 종료
"""


def run(choice: str) -> None:
    if choice == "1":
        if db.is_empty():
            print("전체 목록 수집 시작...")
            n = scraper.fetch_all_postings()
        else:
            print("신규 공고 수집 시작...")
            n = scraper.fetch_new_postings()
        print(f"저장 완료: {n}건")

    elif choice == "2":
        scraper.fetch_detail_postings()

    elif choice == "3":
        analyze_all_postings()

    elif choice == "4":
        user_input.collect()

    elif choice == "5":
        profile = db.load_user_profile()
        if not profile:
            print("저장된 프로필이 없습니다. 먼저 사용자 정보를 입력하세요 (4번).")
            return
        model = judge._load_client()
        judge.judge_all_tracks(profile, model)

    else:
        print(f"알 수 없는 선택: {choice}")


def main() -> None:
    db.init_db()

    if len(sys.argv) > 1:
        run(sys.argv[1])
        return

    while True:
        print(MENU)
        choice = input("선택 > ").strip()
        if choice == "0":
            break
        run(choice)


if __name__ == "__main__":
    main()
