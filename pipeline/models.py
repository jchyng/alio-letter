from typing import TypedDict


class Posting(TypedDict):
    idx: int          # alio 공고 ID (URL의 idx 파라미터)
    title: str        # 공고 제목
    url: str          # 공고 상세 URL
    deadline: str     # 마감일 (예: "26.03.29")
    registered: str   # 등록일 (예: "2026.03.14")
    is_analyzed: bool # AI 분석 완료 여부 (기본값 False)
