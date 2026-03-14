import re
from datetime import date
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

# TODO: MIGRATE TO DB
# 스키마 확정 후 store.py 구현을 db.py 기반으로 교체하면 이 import는 그대로 유지됨
import store
from models import Posting

BASE_URL = "https://job.alio.go.kr"
LIST_URL = f"{BASE_URL}/recruit.do?ing=2"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


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

        registered = tds[6].get_text(strip=True)  # "2026.03.14"
        deadline_raw = tds[7].get_text(strip=True)
        deadline = re.sub(r"D-\d+", "", deadline_raw).strip()

        results.append(Posting(
            idx=idx,
            title=title,
            url=url,
            deadline=deadline,
            registered=registered,
            is_analyzed=False,
        ))

    return results


def fetch_all() -> int:
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


if __name__ == "__main__":
    if store.is_empty():
        total = fetch_all()
    else:
        total = fetch_new_postings()
    print(f"저장 완료: {total}건")
