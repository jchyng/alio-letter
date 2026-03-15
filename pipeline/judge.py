"""
Gemini를 사용해 사용자 프로필과 트랙 자격요건을 비교하여 충족 여부·가산점을 판정.

# 왜 Gemini 1회 호출로 트랙 전체를 판정하는가?
# 자격요건(eligibility)이 모두 원문 텍스트이므로, 규칙 기반 파싱보다
# Gemini에게 직접 해석하게 하는 것이 더 정확하고 유지보수가 쉽다.
# 트랙별로 호출하면 API 비용이 늘어나므로 1개 트랙 = 1회 호출로 제한.

사용법:
    python judge.py   (직접 실행 시 저장된 프로필로 전체 판정)
"""

import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
import google.generativeai as genai

import store
from models import PostingTrack, TrackJudgment, UserProfile

load_dotenv(Path(__file__).parent / ".env")

MODEL_NAME = "gemini-2.5-flash"

PROMPT_TEMPLATE = """아래 사용자 정보와 채용 트랙 자격요건을 비교하여 JSON으로만 응답하라. 설명 없이 JSON만 출력할 것.

## 사용자 정보
{profile_summary}

## 트랙 자격요건
{eligibility_text}

## 공고 가산점
{bonus_points}

## 응답 형식
{{
  "eligible": true 또는 false,
  "unmet": ["미충족 항목 설명", ...],
  "bonus_summary": "가산점 합계 요약 문자열 (예: '10%', '5점', '10% + 3점', '없음')",
  "bonus_reasons": ["항목1: 내용 및 적용 값", "항목2: 내용 및 적용 값", ...]
}}

규칙:
- eligible: 모든 자격요건을 충족하면 true, 하나라도 미충족이면 false
- unmet: 미충족 항목만 나열. 충족이면 빈 배열 []
- bonus_summary: 공고의 중복 적용 규칙을 반영한 최종 합계. 단위가 혼재하면 그대로 표기 (예: '10% + 3점')
- bonus_reasons: 적용 가능한 가산점 항목을 각각 나열. 중복 불가 항목은 유리한 것 1개만 포함
- 사용자 정보에 없어 판단 불가한 항목은 bonus_reasons에 '확인 필요: [항목명]'으로 표기
- JSON 외 다른 텍스트(```json 등 포함) 절대 출력 금지"""


def _profile_summary(profile: UserProfile) -> str:
    lines = []
    lines.append(f"- 최종학력: {profile.get('education', '미입력')}")
    lines.append(f"- 총 경력: {profile.get('career_years', 0)}년 (0=신입)")
    fields = profile.get("career_fields", [])
    if fields:
        field_str = ", ".join(f"{f['field']} {f['years']}년" for f in fields)
        lines.append(f"- 분야별 경력: {field_str}")

    birth_year = profile.get("birth_year")
    if birth_year:
        age = 2026 - birth_year  # 현재 연도 기준 만 나이 근사
        lines.append(f"- 출생연도: {birth_year}년 (만 {age - 1}~{age}세)")

    langs = profile.get("languages", [])
    if langs:
        lang_str = ", ".join(f"{l['name']} {l['score']}점" for l in langs)
        lines.append(f"- 어학: {lang_str}")
    else:
        lines.append("- 어학: 없음")

    certs = profile.get("certificates", [])
    lines.append(f"- 자격증: {', '.join(certs) if certs else '없음'}")
    lines.append(f"- 병역: {profile.get('military', '미입력')}")

    # 법정 우대 자격 — 사용자의 실제 법적 신분을 그대로 전달
    # Gemini가 공고의 가산점 텍스트와 대조하여 해당 여부와 적용 %를 판단
    lines.append(f"- 장애인 구분: {profile.get('disability_grade', '해당없음')}")
    lines.append(f"- 취업지원대상자 유형: {profile.get('veteran_type', '해당없음')}")
    lines.append(f"- 저소득층: {'예' if profile.get('is_low_income') else '아니오'}")
    lines.append(f"- 북한이탈주민: {'예' if profile.get('is_north_korean_defector') else '아니오'}")
    lines.append(f"- 자립준비청년: {'예' if profile.get('is_independent_youth') else '아니오'}")
    lines.append(f"- 다문화가족자녀: {'예' if profile.get('is_multicultural_child') else '아니오'}")
    return "\n".join(lines)


def _eligibility_text(track: PostingTrack) -> str:
    elig = track.get("eligibility", {})
    labels = [
        ("education", "학력"),
        ("career", "경력"),
        ("age", "연령"),
        ("language", "어학"),
        ("certificate", "자격증"),
        ("etc", "기타"),
    ]
    lines = []
    for key, label in labels:
        val = elig.get(key, "")
        if val:
            lines.append(f"- {label}: {val}")
    return "\n".join(lines) if lines else "자격요건 정보 없음"


def _parse_judgment(idx: int, track_name: str, raw: str) -> TrackJudgment:
    text = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    data = json.loads(text)
    return {
        "idx": idx,
        "track_name": track_name,
        "eligible": bool(data.get("eligible", False)),
        "unmet": data.get("unmet", []),
        "bonus_summary": str(data.get("bonus_summary", "없음")),
        "bonus_reasons": data.get("bonus_reasons", []),
    }


def judge_track(
    profile: UserProfile,
    track: PostingTrack,
    bonus_points: str,
    model: genai.GenerativeModel,
) -> TrackJudgment:
    """트랙 1개의 자격요건·가산점을 Gemini로 판정한다."""
    prompt = PROMPT_TEMPLATE.format(
        profile_summary=_profile_summary(profile),
        eligibility_text=_eligibility_text(track),
        bonus_points=bonus_points or "해당 없음",
    )
    response = model.generate_content(prompt)
    return _parse_judgment(track["idx"], track.get("track_name", ""), response.text)


def judge_all_tracks(profile: UserProfile, model: genai.GenerativeModel) -> list[TrackJudgment]:
    """저장된 모든 트랙을 판정하고 결과를 반환한다."""
    tracks = store.load_all_tracks()
    if not tracks:
        print("분석된 트랙이 없습니다. 먼저 분석(3번)을 실행하세요.")
        return []

    # 공고별 bonus_points를 미리 로드 (트랙마다 postings를 뒤지지 않도록)
    postings = {p["idx"]: p for p in store.load_all() if "idx" in p}

    judgments: list[TrackJudgment] = []
    total = len(tracks)

    for i, track in enumerate(tracks, 1):
        idx = track.get("idx")
        track_name = track.get("track_name", "")
        bonus_points = postings.get(idx, {}).get("bonus_points", "")

        print(f"[{i}/{total}] idx={idx} '{track_name}' 판정 중...")
        try:
            judgment = judge_track(profile, track, bonus_points, model)
            judgments.append(judgment)
            status = "충족" if judgment["eligible"] else "미충족"
            print(f"  → {status}, 가산점 {judgment['bonus_summary']}")
        except Exception as e:
            print(f"  판정 실패: {e}")

    store.save_judgments(judgments)
    print(f"\n완료: {len(judgments)}/{total}건 판정, raw/judgments.jsonl 저장")
    return judgments


def _load_client() -> genai.GenerativeModel:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY가 .env에 없습니다.")
        sys.exit(1)
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(MODEL_NAME)


if __name__ == "__main__":
    profile = store.load_user_profile()
    if not profile:
        print("저장된 프로필이 없습니다. 먼저 사용자 정보를 입력하세요 (메뉴 4번).")
        sys.exit(1)
    model = _load_client()
    judge_all_tracks(profile, model)
