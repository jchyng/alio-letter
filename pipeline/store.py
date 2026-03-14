# TODO: MIGRATE TO DB
# 현재: JSONL 파일 (raw dump, 스키마 자유)
# 스키마 확정 후 전환 시: save/load_all 구현을 db.py의 execute/fetchall로 교체
# 인터페이스(save, load_all)는 그대로 유지되므로 호출부 코드는 수정 불필요

import json
from pathlib import Path

RAW_DIR = Path(__file__).parent / "raw"
POSTINGS_FILE = RAW_DIR / "postings.jsonl"


def save(record: dict) -> None:
    """공고 1건 저장. 중복 여부는 호출부에서 판단."""
    RAW_DIR.mkdir(exist_ok=True)
    with POSTINGS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def save_batch(records: list[dict]) -> None:
    """공고 여러 건 한꺼번에 저장. 파일을 한 번만 열고 닫는다."""
    if not records:
        return
    RAW_DIR.mkdir(exist_ok=True)
    with POSTINGS_FILE.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_all() -> list[dict]:
    """저장된 공고 전체 반환."""
    if not POSTINGS_FILE.exists():
        return []
    with POSTINGS_FILE.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def is_empty() -> bool:
    """저장된 공고가 없으면 True."""
    return not POSTINGS_FILE.exists() or POSTINGS_FILE.stat().st_size == 0


def clear() -> None:
    """파일 초기화 (테스트용)."""
    if POSTINGS_FILE.exists():
        POSTINGS_FILE.unlink()
