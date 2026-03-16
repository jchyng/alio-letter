"""
filter.py 단위 테스트.

실행:
    cd pipeline
    pytest tests/test_filter.py -v
"""

import pytest
from filter import filter_postings, matches


def posting(**kwargs):
    """테스트용 최소 Posting dict 생성."""
    base = {
        "idx": 1, "title": "테스트", "org": "한국전력공사",
        "location": "서울특별시", "work_field": "사무직",
        "employment_type": "정규직", "recruit_type": "신입",
        "education": "대졸(4년)", "ncs": "사무원",
        "is_substitute": "아니오",
    }
    base.update(kwargs)
    return base


def prefs(**kwargs):
    """테스트용 PostingFilter dict 생성."""
    return kwargs


# ── 빈 필터 ─────────────────────────────────────────────────────────────────

def test_empty_prefs_matches_all():
    postings = [posting(idx=1), posting(idx=2, location="부산광역시")]
    result = filter_postings(postings, {})
    assert len(result) == 2


def test_none_filter_list_means_all():
    p = posting()
    assert matches(p, prefs(locations=None)) is True
    assert matches(p, prefs(locations=[])) is True


# ── location 필터 ────────────────────────────────────────────────────────────

def test_location_exact_match():
    p = posting(location="서울특별시")
    assert matches(p, prefs(locations=["서울특별시"])) is True


def test_location_partial_match():
    """공고가 "서울특별시 강남구"이고 필터가 "서울특별시"이면 매칭."""
    p = posting(location="서울특별시 강남구")
    assert matches(p, prefs(locations=["서울특별시"])) is True


def test_location_no_match():
    p = posting(location="부산광역시")
    assert matches(p, prefs(locations=["서울특별시"])) is False


def test_location_none_posting_val_with_filter():
    p = posting(location=None)
    assert matches(p, prefs(locations=["서울특별시"])) is False


# ── employment_type 필터 ─────────────────────────────────────────────────────

def test_employment_type_match():
    p = posting(employment_type="정규직")
    assert matches(p, prefs(employment_types=["정규직", "무기계약직"])) is True


def test_employment_type_no_match():
    p = posting(employment_type="기간제")
    assert matches(p, prefs(employment_types=["정규직"])) is False


# ── org_names 필터 ──────────────────────────────────────────────────────────

def test_org_exact_match():
    p = posting(org="한국전력공사")
    assert matches(p, prefs(org_names=["한국전력공사"])) is True


def test_org_partial_match():
    p = posting(org="한국전력공사 서울본부")
    assert matches(p, prefs(org_names=["한국전력공사"])) is True


def test_org_no_match():
    p = posting(org="한국수자원공사")
    assert matches(p, prefs(org_names=["한국전력공사"])) is False


# ── is_substitute 필터 ──────────────────────────────────────────────────────

def test_is_substitute_match():
    p = posting(is_substitute="아니오")
    assert matches(p, prefs(is_substitute="아니오")) is True


def test_is_substitute_no_match():
    p = posting(is_substitute="예")
    assert matches(p, prefs(is_substitute="아니오")) is False


def test_is_substitute_전체_always_matches():
    p = posting(is_substitute="예")
    assert matches(p, prefs(is_substitute="전체")) is True
    p2 = posting(is_substitute="아니오")
    assert matches(p2, prefs(is_substitute="전체")) is True


def test_is_substitute_none_filter_allows_all():
    p = posting(is_substitute="예")
    assert matches(p, prefs(is_substitute=None)) is True


# ── 복합 필터 ────────────────────────────────────────────────────────────────

def test_multiple_conditions_all_match():
    p = posting(location="서울특별시", employment_type="정규직", recruit_type="신입")
    assert matches(p, prefs(
        locations=["서울특별시"],
        employment_types=["정규직"],
        recruit_types=["신입"],
    )) is True


def test_multiple_conditions_one_fails():
    p = posting(location="서울특별시", employment_type="기간제", recruit_type="신입")
    assert matches(p, prefs(
        locations=["서울특별시"],
        employment_types=["정규직"],  # 불일치
    )) is False


# ── filter_postings ──────────────────────────────────────────────────────────

def test_filter_postings_returns_matching_only():
    postings = [
        posting(idx=1, location="서울특별시"),
        posting(idx=2, location="부산광역시"),
        posting(idx=3, location="서울특별시 강남구"),
    ]
    result = filter_postings(postings, prefs(locations=["서울특별시"]))
    assert len(result) == 2
    assert all("서울특별시" in p["location"] for p in result)


def test_filter_postings_empty_input():
    assert filter_postings([], prefs(locations=["서울특별시"])) == []
