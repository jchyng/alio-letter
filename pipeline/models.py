from typing import TypedDict


class Posting(TypedDict, total=False):
    # 목록 크롤링 시 채워지는 필드
    idx: int
    title: str
    org: str
    url: str
    deadline: str
    registered: str
    # 상세 크롤링 시 채워지는 필드
    ncs: str
    work_field: str
    employment_type: str
    location: str
    education: str
    recruit_type: str
    is_substitute: str
    salary_url: str
    preferred: str
    attachment_path: str
    attachment_ext: str
    attachment_converted: str
    bonus_points: str   # 가산점 원문 (예: "취업지원대상자 10%, 장애인 10%")


class Eligibility(TypedDict, total=False):
    education: str    # 학력 요건 원문 (예: "대졸 이상", "학력 무관")
    career: str       # 경력 요건 원문 (예: "신입", "경력 3년 이상")
    age: str          # 연령 요건 원문 (예: "제한 없음", "만 18세 이상")
    language: str     # 어학 요건 원문 (예: "TOEIC 700점 이상", "해당 없음")
    certificate: str  # 자격증 요건 원문 (예: "정보처리기사", "해당 없음")
    etc: str          # 기타 요건 원문 (예: "병역필 또는 면제자", "결격사유 없는 자")


class PostingTrack(TypedDict, total=False):
    # Gemini 분석 결과 — postings의 alio_id(idx)를 FK로 참조
    # 트랙 1개 = 1행, 1개 공고에 트랙 n개 → 같은 idx를 가진 행 n개
    idx: int            # postings의 alio_id (FK)
    track_name: str     # 채용구분명 (예: "대졸수준-일반")
    positions: str      # 모집분야별 인원 원문 (예: "사무 3, 전기 5") — 이메일 표시용
    total_positions: int  # 해당 트랙 총 채용인원
    eligibility: Eligibility  # 자격요건
