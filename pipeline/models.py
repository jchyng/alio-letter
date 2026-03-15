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
    notes: str          # Gemini 분석 — 중요하지만 특정 필드로 분류하기 어려운 정보 (예: "보수: 시간당 12,000원")


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


class UserProfile(TypedDict, total=False):
    education: str          # 최종학력 (예: "4년제 대졸", "고졸")
    career_years: int       # 총 경력 연수 (0 = 신입) — 자격요건 경력 년수 판단용
    career_fields: list[dict]  # 분야별 경력 [{field: "간호사", years: 3}, ...] — 직종 경력 요건 판단용
    birth_year: int         # 출생연도 (나이 계산용)
    languages: list[dict]   # [{"name": "TOEIC", "score": 850}, ...]
    certificates: list[str] # ["정보처리기사", "한국사1급"]
    military: str           # "필필" | "면제" | "미필" | "해당없음(여성)"

    # 법정 우대 자격 — 사용자의 실제 법적 신분을 저장
    # 가점 %는 공고마다 다르므로 여기서는 신분만 기록, Gemini가 공고 텍스트와 매칭
    #
    # veteran_type 선택지:
    #   "해당없음" | "국가유공자 본인(전상·공상군경 등, 10% 해당)"
    #   | "국가유공자 본인(그 외, 5% 해당)" | "국가유공자 유족·가족"
    #   | "보훈보상대상자 본인" | "보훈보상대상자 유족·가족"
    #   | "5·18민주유공자 본인" | "5·18민주유공자 유족·가족"
    #   | "특수임무유공자" | "고엽제후유증환자"
    veteran_type: str
    #
    # disability_grade 선택지: "해당없음" | "경증" | "중증"
    # 2019년 등급제 폐지 후 경증/중증 2단계. 기관별로 경증 5%, 중증 10% 적용 多
    disability_grade: str

    # 법정 사회배려 대상 — 공공기관 공고에서 별도 가점 카테고리로 자주 등장
    is_low_income: bool             # 저소득층 여부
    is_north_korean_defector: bool  # 북한이탈주민 여부
    is_independent_youth: bool      # 자립준비청년(보호종료아동) 여부
    is_multicultural_child: bool    # 다문화가족자녀 여부


class PostingFilter(TypedDict, total=False):
    # 이미지의 필터 항목 (등록일·상태·키워드 제외)
    ncs: list[str]               # 표준직무(NCS) (예: ["사무원", "IT개발"])
    locations: list[str]         # 근무지 (예: ["서울특별시", "경기도", "해외"])
    work_fields: list[str]       # 근무분야 (예: ["사무직", "전산직"])
    employment_types: list[str]  # 고용형태 (예: ["정규직", "무기계약직"])
    recruit_types: list[str]     # 채용구분 (예: ["신입", "신입+경력"])
    educations: list[str]        # 학력정보 (예: ["대졸(4년)", "석사"])
    education_mode: str          # "AND" | "OR" (단일 또는 중복)
    is_substitute: str           # "예" | "아니오" | "전체"
    org_types: list[str]         # 기관유형 (예: ["공기업", "준정부기관"])
    org_names: list[str]         # 기관명 (예: ["한국전력공사"])


class TrackJudgment(TypedDict, total=False):
    idx: int                # 공고 idx (FK)
    track_name: str
    eligible: bool          # 자격요건 충족 여부
    unmet: list[str]        # 미충족 항목 목록 (충족이면 빈 리스트)
    bonus_summary: str      # 가산점 합계 요약 — 공고마다 단위가 다름 (예: "10%", "5점", "10% + 3점")
    bonus_reasons: list[str]  # 중복 적용 가능한 가산점 항목 각각의 설명
