# pipeline

알리오 공공기관 채용공고 수집·분석 파이프라인.

## 구조

```
pipeline/
  main.py          # 진입점 (대화형 메뉴)
  scraper.py       # 크롤링 (목록 + 상세 + 첨부파일 다운로드)
  analyzer.py      # Gemini PDF 분석 → posting_tracks 저장
  judge.py         # Gemini 자격요건 판정
  db.py            # 저장소 (SQLite 로컬 → D1 전환 예정)
  models.py        # TypedDict 정의
  user_input.py    # CLI 사용자 프로필 입력
  scripts/
    test_gemini.py    # Gemini 파일 업로드·분석 수동 테스트
    test_pipeline.py  # 파이프라인 전체 흐름 N건 테스트
  tests/
    test_convert.py   # hwp/hwpx → pdf 변환 자동화 테스트
  raw/                # 런타임 데이터 (gitignore)
    attachments/      # 다운로드된 첨부파일
    user_profile.json # CLI 사용자 프로필
    judgments.jsonl   # 로컬 판정 결과 검토용
```

## 환경 세팅

### 1. Python 의존성

```bash
cd pipeline
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. LibreOffice 설치 (hwp/hwpx → pdf 변환에 필요)

```bash
sudo apt install libreoffice libreoffice-h2orestart
sudo apt install fonts-nanum fonts-nanum-extra fonts-unfonts-core fonts-baekmuk
fc-cache -fv
```

> `libreoffice-h2orestart`: HWP/HWPX 파일 읽기 필터.
> 폰트 미설치 시 한글이 깨진 PDF가 생성됨. Gemini 분석에는 대체로 지장 없음.

### 3. 환경변수

`pipeline/.env` 파일 생성:

```
GEMINI_API_KEY=your_api_key_here
```

## 실행

```bash
cd pipeline
python main.py
```

메뉴:

```
1. 공고 목록 수집     — 최초 실행 시 전체, 이후엔 오늘 신규만
2. 상세 공고 수집     — 첨부파일 다운로드 포함
3. 분석 (Gemini)     — PDF → 트랙·자격요건 추출
4. 사용자 정보 입력   — 학력·경력·자격증 등 CLI 입력
5. 자격요건 판정      — Gemini로 트랙별 충족 여부·가산점 판정
```

또는 단계별 직접 실행:

```bash
python main.py 1   # 목록 수집
python main.py 2   # 상세 수집
python main.py 3   # 분석
```

## 첨부파일 처리

| 확장자 | 처리 방법 |
|--------|-----------|
| pdf, jpg, png 등 | Gemini API에 직접 업로드 |
| hwp, hwpx | LibreOffice로 pdf 변환 후 업로드 |
