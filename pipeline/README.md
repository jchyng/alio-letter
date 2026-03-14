# pipeline

알리오 공공기관 채용공고 수집 파이프라인.

## 구조

```
pipeline/
  scraper.py       # 크롤링 (목록 + 상세 + 첨부파일)
  store.py         # JSONL 저장/로드
  models.py        # Posting TypedDict
  db.py            # SQLite 인터페이스 (DB 전환 시 활성화)
  test_gemini.py   # Gemini API 테스트
  raw/
    postings.jsonl        # 공고 목록 + 상세 데이터
    attachments/          # 다운로드된 첨부파일
```

## 환경 세팅

### 1. Python 의존성

```bash
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
pip install google-generativeai python-dotenv
```

### 2. LibreOffice 설치 (hwp/hwpx → pdf 변환에 필요)

```bash
sudo apt install libreoffice
sudo apt install libreoffice-h2orestart
sudo apt install fonts-nanum fonts-nanum-extra fonts-unfonts-core fonts-baekmuk
fc-cache -fv
```

> `libreoffice-h2orestart`: HWP/HWPX 파일 읽기 필터.
> 폰트 미설치 시 한글이 깨진 PDF가 생성됨. HY 폰트 등 상업용 폰트가 쓰인 문서는 일부 깨질 수 있으나 Gemini 분석에는 지장 없음.

### 3. 환경변수

`pipeline/.env` 파일 생성:

```
GEMINI_API_KEY=...
```

## 실행

```bash
cd pipeline
python scraper.py
```

- `postings.jsonl`이 없으면 전체 크롤링, 있으면 오늘 등록된 공고만 수집
- 수집 후 미분석 공고 상세페이지 크롤링 + 첨부파일 다운로드 자동 실행

## 첨부파일 처리

| 확장자 | 처리 방법 |
|--------|-----------|
| pdf, jpg, png 등 | Gemini API에 직접 업로드 |
| hwp | LibreOffice로 pdf 변환 후 업로드 |
| hwpx | LibreOffice로 pdf 변환 후 업로드 |
