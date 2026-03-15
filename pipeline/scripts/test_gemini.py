"""
Gemini API로 첨부파일(hwp/hwpx/pdf/이미지) 분석 가능 여부 테스트.

사용법:
    python scripts/test_gemini.py <파일경로>
    python scripts/test_gemini.py raw/attachments/297947_3034885.hwpx
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv(Path(__file__).parent.parent / ".env")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("GEMINI_API_KEY가 .env에 없습니다.")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-pro")


def test_file(path: str) -> None:
    p = Path(path)
    if not p.exists():
        print(f"파일 없음: {path}")
        sys.exit(1)

    print(f"파일: {p.name} ({p.stat().st_size // 1024}KB)")
    print("업로드 중...")

    try:
        uploaded = genai.upload_file(str(p))
        print(f"업로드 완료: {uploaded.uri}")
    except Exception as e:
        print(f"업로드 실패: {e}")
        sys.exit(1)

    print("분석 요청 중...")
    try:
        response = model.generate_content([
            uploaded,
            "이 공고문의 주요 내용을 한국어로 요약해줘. 직무, 자격요건, 지원방법 위주로.",
        ])
        print("\n=== 응답 ===")
        print(response.text)
    except Exception as e:
        print(f"분석 실패: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # 인자 없으면 raw/attachments/ 에서 첫 번째 파일 자동 선택
        attachments = list((Path(__file__).parent.parent / "raw" / "attachments").iterdir())
        attachments = [f for f in attachments if f.is_file() and not f.name.endswith(".txt")]
        if not attachments:
            print("raw/attachments/ 에 파일이 없습니다.")
            sys.exit(1)
        target = str(attachments[0])
        print(f"자동 선택: {target}")
    else:
        target = sys.argv[1]

    test_file(target)
