"""
CLI 대화형 사용자 프로필 입력.
이미 저장된 프로필이 있으면 현재 값을 보여주고 수정 여부를 확인한다.
"""

import db
from models import UserProfile


def _ask(prompt: str, default: str = "") -> str:
    """기본값이 있으면 함께 표시하고 입력받는다. 빈 Enter → 기본값 사용."""
    hint = f" [{default}]" if default else ""
    val = input(f"{prompt}{hint}: ").strip()
    return val if val else default


def _ask_int(prompt: str, default: int | None = None) -> int | None:
    hint = f" [{default}]" if default is not None else ""
    val = input(f"{prompt}{hint}: ").strip()
    if not val and default is not None:
        return default
    try:
        return int(val)
    except ValueError:
        print("  숫자를 입력하세요. 건너뜁니다.")
        return default


def _ask_bool(prompt: str, default: bool = False) -> bool:
    hint = "Y" if default else "N"
    val = input(f"{prompt} (y/n) [{hint}]: ").strip().lower()
    if not val:
        return default
    return val in ("y", "yes")


_CAREER_FIELDS = {
    "1": "사무·행정",
    "2": "IT·개발",
    "3": "연구·분석",
    "4": "영업·마케팅",
    "5": "교육·강의",
    "6": "의료·간호",
    "7": "복지·상담",
    "8": "기술·생산·현장",
    "9": "운전·물류",
    "10": "경비·시설",
    "99": "기타 (직접 입력)",
}


def _ask_career_fields(current: list[dict] | None) -> list[dict]:
    """분야별 경력 입력. 분야는 select, 연수는 숫자 직접 입력."""
    print("\n[분야별 경력] 빈 줄 입력 시 종료.")
    if current:
        for c in current:
            print(f"  현재: {c['field']} {c['years']}년")

    items = []
    while True:
        print("  분야 선택:")
        for k, v in _CAREER_FIELDS.items():
            print(f"    {k}. {v}")
        choice = input("  번호 선택 (없으면 Enter): ").strip()
        if not choice:
            break
        if choice == "99":
            field = input("  직접 입력: ").strip()
        else:
            field = _CAREER_FIELDS.get(choice)
            if not field:
                print("  올바른 번호를 선택하세요.")
                continue
        years_str = input(f"  '{field}' 경력 연수: ").strip()
        try:
            items.append({"field": field, "years": int(years_str)})
        except ValueError:
            print("  숫자를 입력하세요.")
    return items if items else (current or [])


def _ask_languages(current: list[dict] | None) -> list[dict]:
    """어학 성적 목록 입력. 예) TOEIC 850"""
    print("\n[어학 성적] 빈 줄 입력 시 종료.")
    if current:
        print(f"  현재: {current}")
    items = []
    while True:
        entry = input("  어학명 점수 (예: TOEIC 850, 없으면 Enter): ").strip()
        if not entry:
            break
        parts = entry.split()
        if len(parts) >= 2:
            try:
                items.append({"name": parts[0], "score": int(parts[-1])})
                continue
            except ValueError:
                pass
        print("  형식 오류. '어학명 점수' 형식으로 입력하세요.")
    return items if items else (current or [])


def _ask_certificates(current: list[str] | None) -> list[str]:
    """자격증 목록 입력. 쉼표 구분."""
    current_str = ", ".join(current) if current else ""
    val = _ask("자격증 (쉼표 구분, 없으면 Enter)", current_str)
    if not val:
        return []
    return [c.strip() for c in val.split(",") if c.strip()]


def collect() -> None:
    """사용자 프로필을 대화형으로 입력받아 저장한다."""
    existing = db.load_user_profile()

    if existing:
        print("\n저장된 프로필:")
        for k, v in existing.items():
            print(f"  {k}: {v}")
        modify = input("\n수정하시겠습니까? (y/n) [n]: ").strip().lower()
        if modify not in ("y", "yes"):
            print("수정 없이 종료합니다.")
            return

    profile: UserProfile = existing or {}

    print("\n=== 사용자 정보 입력 ===")
    print("(Enter 키로 기존 값 유지 / 처음이면 기본값 사용)\n")

    education_default = profile.get("education", "4년제 대졸")
    profile["education"] = _ask("최종학력 (예: 4년제 대졸, 고졸, 대학원 석사)", education_default)

    career_default = profile.get("career_years", 0)
    profile["career_years"] = _ask_int("총 경력 연수 (신입=0)", career_default) or 0

    profile["career_fields"] = _ask_career_fields(profile.get("career_fields"))

    birth_default = profile.get("birth_year")
    profile["birth_year"] = _ask_int("출생연도 (예: 1995)", birth_default)

    profile["languages"] = _ask_languages(profile.get("languages"))

    profile["certificates"] = _ask_certificates(profile.get("certificates"))

    military_default = profile.get("military", "병역필")
    print("\n병역 구분: 병역필 / 면제 / 미필 / 해당없음(여성)")
    profile["military"] = _ask("병역 구분", military_default)

    # 장애인 등급 — 공고마다 경증 5%, 중증 10% 등 다르게 적용됨
    print("\n장애인 구분:")
    print("  0. 해당없음")
    print("  1. 경증")
    print("  2. 중증")
    _DISABILITY = {"0": "해당없음", "1": "경증", "2": "중증"}
    current_disability = profile.get("disability_grade", "해당없음")
    d_choice = input(f"  선택 (현재: {current_disability}) [Enter=유지]: ").strip()
    profile["disability_grade"] = _DISABILITY.get(d_choice, current_disability)

    # 취업지원대상자 유형 — 유형에 따라 공고별 가산점 %가 다름
    # 가산점 %는 공고 텍스트에서 Gemini가 판단, 여기서는 사용자의 실제 법적 신분만 저장
    print("\n취업지원대상자 유형:")
    print("  0. 해당없음")
    print("  1. 국가유공자 본인 (전상·공상군경 등 — 통상 10% 해당)")
    print("  2. 국가유공자 본인 (그 외 — 통상 5% 해당)")
    print("  3. 국가유공자 유족·가족")
    print("  4. 보훈보상대상자 본인")
    print("  5. 보훈보상대상자 유족·가족")
    print("  6. 5·18민주유공자 본인")
    print("  7. 5·18민주유공자 유족·가족")
    print("  8. 특수임무유공자")
    print("  9. 고엽제후유증환자")
    print("  99. 기타 (직접 입력)")
    _VETERAN = {
        "0": "해당없음",
        "1": "국가유공자 본인(전상·공상군경 등, 10% 해당)",
        "2": "국가유공자 본인(그 외, 5% 해당)",
        "3": "국가유공자 유족·가족",
        "4": "보훈보상대상자 본인",
        "5": "보훈보상대상자 유족·가족",
        "6": "5·18민주유공자 본인",
        "7": "5·18민주유공자 유족·가족",
        "8": "특수임무유공자",
        "9": "고엽제후유증환자",
    }
    current_veteran = profile.get("veteran_type", "해당없음")
    v_choice = input(f"  선택 (현재: {current_veteran}) [Enter=유지]: ").strip()
    if v_choice == "99":
        profile["veteran_type"] = input("  직접 입력: ").strip() or current_veteran
    else:
        profile["veteran_type"] = _VETERAN.get(v_choice, current_veteran)

    # 공공기관 공고에서 별도 가점으로 자주 등장하는 법정 카테고리
    profile["is_low_income"] = _ask_bool("저소득층 여부", profile.get("is_low_income", False))
    profile["is_north_korean_defector"] = _ask_bool("북한이탈주민 여부", profile.get("is_north_korean_defector", False))
    profile["is_independent_youth"] = _ask_bool("자립준비청년(보호종료아동) 여부", profile.get("is_independent_youth", False))
    profile["is_multicultural_child"] = _ask_bool("다문화가족자녀 여부", profile.get("is_multicultural_child", False))

    db.save_user_profile(profile)
    print("\n프로필이 저장되었습니다.")
    for k, v in profile.items():
        print(f"  {k}: {v}")
