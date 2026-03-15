# TODO: MIGRATE TO DB
# 현재: JSONL 파일 (raw dump, 스키마 자유)
# 스키마 확정 후 전환 시: save/load_all 구현을 db.py의 execute/fetchall로 교체
# 인터페이스(save, load_all)는 그대로 유지되므로 호출부 코드는 수정 불필요

import json
from pathlib import Path

from models import Posting, PostingFilter, PostingTrack, UserProfile, TrackJudgment

RAW_DIR = Path(__file__).parent / "raw"
POSTINGS_FILE = RAW_DIR / "postings.jsonl"
ANALYSES_FILE = RAW_DIR / "analyses.jsonl"
USER_PROFILE_FILE = RAW_DIR / "user_profile.json"
JUDGMENTS_FILE = RAW_DIR / "judgments.jsonl"
FILTER_FILE = RAW_DIR / "filter.json"


def save(record: Posting) -> None:
    """공고 1건 저장. 중복 여부는 호출부에서 판단."""
    RAW_DIR.mkdir(exist_ok=True)
    with POSTINGS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def save_batch(records: list[Posting]) -> None:
    """공고 여러 건 한꺼번에 저장. 파일을 한 번만 열고 닫는다."""
    if not records:
        return
    RAW_DIR.mkdir(exist_ok=True)
    with POSTINGS_FILE.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_all() -> list[Posting]:
    """저장된 공고 전체 반환."""
    if not POSTINGS_FILE.exists():
        return []
    with POSTINGS_FILE.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_unfetched() -> list[Posting]:
    """상세 크롤링 미완료 공고만 반환 (employment_type 필드 없는 것)."""
    return [p for p in load_all() if "employment_type" not in p]


def is_empty() -> bool:
    """저장된 공고가 없으면 True."""
    return not POSTINGS_FILE.exists() or POSTINGS_FILE.stat().st_size == 0


def upsert_detail(posting: Posting) -> None:
    """상세 크롤링 결과를 JSONL에 머지."""
    # TODO: MIGRATE TO DB — db.execute(UPDATE postings SET ncs=?, ... WHERE alio_id=?)
    records = load_all()
    for r in records:
        if r["idx"] == posting["idx"]:
            r.update({k: v for k, v in posting.items() if k != "idx"})
    with POSTINGS_FILE.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def save_tracks(tracks: list[PostingTrack]) -> None:
    """분석된 트랙 여러 건 저장. 트랙 1개 = 1행."""
    if not tracks:
        return
    RAW_DIR.mkdir(exist_ok=True)
    with ANALYSES_FILE.open("a", encoding="utf-8") as f:
        for track in tracks:
            f.write(json.dumps(track, ensure_ascii=False) + "\n")


def load_all_tracks() -> list[PostingTrack]:
    """저장된 트랙 전체 반환."""
    if not ANALYSES_FILE.exists():
        return []
    with ANALYSES_FILE.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def is_analyzed(idx: int) -> bool:
    """해당 공고(idx)가 이미 분석됐는지 확인."""
    return any(t.get("idx") == idx for t in load_all_tracks())


def clear() -> None:
    """파일 초기화 (테스트용)."""
    if POSTINGS_FILE.exists():
        POSTINGS_FILE.unlink()


def save_user_profile(profile: UserProfile) -> None:
    """사용자 프로필을 단일 JSON 파일로 저장. 덮어쓴다."""
    RAW_DIR.mkdir(exist_ok=True)
    with USER_PROFILE_FILE.open("w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


def load_user_profile() -> UserProfile | None:
    """저장된 사용자 프로필 반환. 없으면 None."""
    if not USER_PROFILE_FILE.exists():
        return None
    with USER_PROFILE_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def save_judgments(judgments: list[TrackJudgment]) -> None:
    """판정 결과 전체를 덮어쓴다 (재실행 시 최신 결과로 갱신)."""
    if not judgments:
        return
    RAW_DIR.mkdir(exist_ok=True)
    with JUDGMENTS_FILE.open("w", encoding="utf-8") as f:
        for j in judgments:
            f.write(json.dumps(j, ensure_ascii=False) + "\n")


def load_judgments() -> list[TrackJudgment]:
    """저장된 판정 결과 전체 반환."""
    if not JUDGMENTS_FILE.exists():
        return []
    with JUDGMENTS_FILE.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def save_filter(f: PostingFilter) -> None:
    """필터 조건을 단일 JSON 파일로 저장. 덮어쓴다."""
    RAW_DIR.mkdir(exist_ok=True)
    with FILTER_FILE.open("w", encoding="utf-8") as fp:
        json.dump(f, fp, ensure_ascii=False, indent=2)


def load_filter() -> PostingFilter | None:
    """저장된 필터 조건 반환. 없으면 None."""
    if not FILTER_FILE.exists():
        return None
    with FILTER_FILE.open(encoding="utf-8") as fp:
        return json.load(fp)
