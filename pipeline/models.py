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
