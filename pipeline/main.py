"""
파이프라인 진입점.

사용법:
    python main.py          # 대화형 메뉴
    python main.py 1        # 공고 목록 수집
    python main.py 2        # 상세 공고 수집
    python main.py 3        # 분석
"""

import sys

import scraper
import store
from analyzer import analyze_all_postings

MENU = """
=== alio-letter 파이프라인 ===
1. 공고 목록 수집
2. 상세 공고 수집
3. 분석 (Gemini)
0. 종료
"""


def run(choice: str) -> None:
    if choice == "1":
        if store.is_empty():
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

    else:
        print(f"알 수 없는 선택: {choice}")


def main() -> None:
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
