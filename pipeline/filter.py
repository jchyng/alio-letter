"""
공고 필터링 모듈.

# 매칭 규칙 (FLOW 2 기반)
# - 빈 배열/None → "전체" (해당 항목 필터 미적용)
# - 교집합 존재 시 매칭 (부분 문자열 포함 비교)
# - is_substitute: 값이 "전체"가 아닐 때만 일치 비교
# - org_type: DB 컬럼 없으므로 미구현 (필터 항목 무시)
"""

from models import Posting, PostingFilter


def _has_overlap(posting_val: str | None, filter_list: list[str] | None) -> bool:
    """공고 단일 문자열 값과 필터 목록 간 부분 문자열 교집합 여부.
    filter_list가 비어 있거나 None이면 항상 True (전체 허용).
    posting_val이 None이면 필터가 있어도 매칭 불가 → False.
    """
    if not filter_list:
        return True
    if not posting_val:
        return False
    for f in filter_list:
        if f in posting_val or posting_val in f:
            return True
    return False


def _org_match(org_name: str | None, org_names: list[str] | None) -> bool:
    """기관명 완전 포함 여부 (부분 문자열). 빈 목록이면 전체 허용."""
    if not org_names:
        return True
    if not org_name:
        return False
    for name in org_names:
        if name in org_name or org_name in name:
            return True
    return False


def _substitute_match(posting_val: str | None, filter_val: str | None) -> bool:
    """is_substitute 일치 비교. filter_val이 '전체' 또는 None이면 전체 허용."""
    if not filter_val or filter_val == "전체":
        return True
    if not posting_val:
        return False
    return posting_val == filter_val


def _ncs_match(posting_val: str | None, filter_list: list[str] | None) -> bool:
    """NCS는 공고에 여러 항목이 콤마로 이어진 문자열로 저장될 수 있어 교집합 비교."""
    return _has_overlap(posting_val, filter_list)


def matches(posting: Posting, prefs: PostingFilter) -> bool:
    """공고 1건이 사용자 필터 조건을 모두 만족하는지 반환."""
    if not _has_overlap(posting.get("location"), prefs.get("locations")):
        return False
    if not _has_overlap(posting.get("work_field"), prefs.get("work_fields")):
        return False
    if not _has_overlap(posting.get("employment_type"), prefs.get("employment_types")):
        return False
    if not _has_overlap(posting.get("recruit_type"), prefs.get("recruit_types")):
        return False
    if not _has_overlap(posting.get("education"), prefs.get("educations")):
        return False
    if not _org_match(posting.get("org"), prefs.get("org_names")):
        return False
    if not _ncs_match(posting.get("ncs"), prefs.get("ncs")):
        return False
    if not _substitute_match(posting.get("is_substitute"), prefs.get("is_substitute")):
        return False
    return True


def filter_postings(postings: list[Posting], prefs: PostingFilter) -> list[Posting]:
    """필터 조건에 맞는 공고만 추려 반환."""
    if not prefs:
        return list(postings)
    return [p for p in postings if matches(p, prefs)]
