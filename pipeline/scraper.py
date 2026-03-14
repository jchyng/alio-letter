import hashlib
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

import store
from models import Posting

BASE_URL = "https://job.alio.go.kr"
LIST_URL = f"{BASE_URL}/recruit.do?ing=2"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

ATTACHMENTS_DIR = Path(__file__).parent / "raw" / "attachments"


def _fetch_page(page: int) -> list[Posting]:
    """단일 페이지 크롤링."""
    url = f"{LIST_URL}&pageNo={page}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    html = resp.content.decode("utf-8")

    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 3:
        return []
    tbody = tables[2].find("tbody")
    if not tbody:
        return []

    results = []
    for tr in tbody.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 8:
            continue

        link_tag = tds[2].find("a", href=True)
        if not link_tag:
            continue
        title = tds[2].get_text(strip=True)
        url = BASE_URL + link_tag["href"]
        qs = parse_qs(urlparse(url).query)
        if "idx" not in qs:
            continue
        idx = int(qs["idx"][0])

        org = tds[3].get_text(strip=True)
        registered = tds[6].get_text(strip=True)  # "2026.03.14"
        deadline_raw = tds[7].get_text(strip=True)
        deadline = re.sub(r"D-\d+", "", deadline_raw).strip()

        results.append(Posting(
            idx=idx,
            title=title,
            org=org,
            url=url,
            deadline=deadline,
            registered=registered,
        ))

    return results


def fetch_all_postings() -> int:
    """전체 크롤링 + 페이지별 즉시 저장. 최초 실행 시 사용."""
    total = 0
    page = 1
    while True:
        print(f"\r페이지 {page} 크롤링 중... (저장: {total}건)", end="", flush=True)
        rows = _fetch_page(page)
        if not rows:
            break
        store.save_batch(rows)
        total += len(rows)
        page += 1
    print()
    return total


def fetch_new_postings() -> int:
    """오늘 등록된 공고만 수집. 매일 23:59 실행."""
    today = date.today().strftime("%Y.%m.%d")
    total = 0
    page = 1
    while True:
        print(f"\r페이지 {page} 크롤링 중... (저장: {total}건)", end="", flush=True)
        rows = _fetch_page(page)
        if not rows:
            break

        page_rows = []
        done = False
        for row in rows:
            if row["registered"] < today:
                done = True
                break
            page_rows.append(row)

        store.save_batch(page_rows)
        total += len(page_rows)

        if done:
            print()
            return total
        page += 1
    print()
    return total


def _download_announcement(idx: int, soup) -> tuple[str, str]:
    """공고문 첨부파일 1건 다운로드. (path, ext) 반환. 실패 시 ('', '')."""
    tables = soup.find_all("table")
    if len(tables) < 3:
        return "", ""

    for tr in tables[2].find_all("tr"):
        th = tr.find("th")
        a = tr.find("a", href=True)
        if not th or not a or "공고문" not in th.get_text():
            continue

        href = a["href"]
        original_name = a.get_text(strip=True)
        ext = Path(original_name).suffix.lstrip(".").lower()

        qs = parse_qs(urlparse(href).query)
        file_no = qs.get("fileNo", [None])[0]
        prefix = file_no if file_no else hashlib.md5(href.encode()).hexdigest()[:8]

        ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
        dest = ATTACHMENTS_DIR / f"{idx}_{prefix}.{ext}"

        if not dest.exists():
            try:
                r = requests.get(href, headers=HEADERS, timeout=30)
                r.raise_for_status()
                dest.write_bytes(r.content)
                time.sleep(0.3)
            except Exception as e:
                print(f"  파일 다운로드 실패: {e}")
                return "", ""

        return str(dest), ext

    return "", ""


def hwp_to_pdf(path: str, ext: str) -> str:
    """hwp/hwpx → pdf 변환 (LibreOffice). 변환 불필요하거나 실패 시 '' 반환."""
    import subprocess
    import shutil
    import tempfile
    if ext not in ("hwp", "hwpx"):
        return ""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_src = Path(tmp) / Path(path).name
        shutil.copy2(path, tmp_src)
        result = subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", tmp, str(tmp_src)],
            capture_output=True, timeout=120,
        )
        tmp_pdf = tmp_src.with_suffix(".pdf")
        if result.returncode == 0 and tmp_pdf.exists():
            dest = Path(path).with_suffix(".pdf")
            shutil.move(str(tmp_pdf), dest)
            return str(dest)
    print(f"  변환 실패: {Path(path).name}")
    return ""


def _fetch_detail(posting: Posting) -> Posting:
    """상세페이지 1건 크롤링. 첨부파일 다운로드 및 변환 포함."""
    resp = requests.get(posting["url"], headers=HEADERS, timeout=10)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    # table[0]: 상세 정보 테이블
    detail_table = soup.find("table")
    fields: dict[str, str] = {}
    salary_url = ""
    if detail_table:
        for tr in detail_table.find_all("tr"):
            ths = tr.find_all("th")
            tds = tr.find_all("td")
            for th, td in zip(ths, tds):
                key = th.get_text(strip=True)
                if key == "급여정보":
                    a = td.find("a")
                    salary_url = a["href"] if a else ""
                    fields[key] = td.get_text(strip=True)
                else:
                    fields[key] = td.get_text(strip=True)

    attachment_path, attachment_ext = _download_announcement(posting["idx"], soup)
    attachment_converted = hwp_to_pdf(attachment_path, attachment_ext) if attachment_path else ""

    return Posting(
        **posting,
        ncs=fields.get("표준직무(NCS)", ""),
        work_field=fields.get("근무분야", ""),
        employment_type=fields.get("고용형태", ""),
        location=fields.get("근무지", ""),
        education=fields.get("학력정보", ""),
        recruit_type=fields.get("채용구분", ""),
        is_substitute=fields.get("대체인력여부", ""),
        salary_url=salary_url,
        preferred=fields.get("우대조건", ""),
        attachment_path=attachment_path,
        attachment_ext=attachment_ext,
        attachment_converted=attachment_converted,
    )


def fetch_detail_postings() -> int:
    """미분석 공고의 상세페이지 크롤링."""
    unanalyzed = store.load_unfetched()
    total = len(unanalyzed)
    print(f"미완료 공고 {total}건 처리 시작")

    for i, posting in enumerate(unanalyzed, 1):
        print(f"[{i}/{total}] {posting['url']}")
        detail = _fetch_detail(posting)
        store.upsert_detail(detail)

    print(f"완료: {total}건")
    return total


if __name__ == "__main__":
    if store.is_empty():
        total = fetch_all_postings()
    else:
        total = fetch_new_postings()
    print(f"저장 완료: {total}건")
    fetch_detail_postings()
