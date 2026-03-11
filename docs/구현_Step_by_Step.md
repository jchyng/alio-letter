# Alio-Letter 구현 Step-by-Step 계획서 (v2.0)

> 잡알리오 채용공고 자동 분석 & 맞춤 알림 서비스
> 기술 스택: Cloudflare Pages/Functions + MySQL (라즈베리파이) + Gemini API + Email API
> 상세 스펙: `UI설계.md` 참조 | DB 스키마: `schema.sql` 참조 | 프롬프트: `LLM추출_프롬프트설계.md` 참조

---

## 인프라 환경

| 항목             | 값                                                        |
| ---------------- | --------------------------------------------------------- |
| 호스트           | Raspberry Pi                                              |
| DB               | Docker 컨테이너 (MySQL 8), DB명 `alio_letter`             |
| 보안 연결        | Cloudflare Tunnel (`cloudflared`)                         |
| 프론트엔드       | Cloudflare Pages (정적 사이트)                            |
| 백엔드           | Cloudflare Functions (Gemini API + MySQL 직접 연결)       |
| 스크래퍼         | Python/Node.js (라즈베리파이 Cron)                        |

### AI 호출 정책

| 시점 | AI 호출 | 설명 |
|------|---------|------|
| 사용자 등록/수정 | O (1회) | CF Functions에서 직접 Gemini API 호출 |
| 공고 수집 | O (공고당 1회) | Scraper Script에서 직접 Gemini API 호출 |
| 매칭/검증/분석 | X | 순수 SQL 쿼리로 처리 |
| 이메일 생성 | X | HTML 템플릿 기반 발송 |

---

## Phase 0: 환경 셋업

### Step 0-1. MySQL DB + 유저 생성

- [ ] `alio_letter` DB 생성 (utf8mb4)
- [ ] `alio` 유저 생성 + 권한 부여 (외부 접속 허용 설정 필요)

### Step 0-2. Cloudflare Tunnel 설정

- [ ] 라즈베리파이에 `cloudflared` 설치
- [ ] MySQL 포트(3306)를 터널로 연결 (예: `db.yourdomain.com`)
- [ ] Cloudflare Access 설정을 통해 Worker IP만 허용하도록 보안 강화

### Step 0-3. 스키마 생성

- [ ] `schema.sql` 실행하여 테이블 생성

---

## Phase 1: 사용자 등록 시스템

### 전체 흐름

```
[사용자] → 폼 작성
    ↓
[Cloudflare Pages] 정적 HTML
    ↓ fetch('/api/register')
[Cloudflare Functions] 입력값 검증 + Gemini API 호출 (파싱)
    ↓
[MySQL] 직접 UPSERT (via Cloudflare Tunnel)
    ↓
[Email API] 등록 확인 + 수정 링크 이메일 발송
```

### Step 1-1. Cloudflare Pages 프로젝트 생성

- [ ] `wrangler.toml` 설정 (Gemini API Key, DB 접속 정보 등)

### Step 1-2. Cloudflare Functions 구현

- [ ] `POST /api/register`: Gemini API 호출 및 MySQL 저장 로직
- [ ] `GET /api/profile/:token`: MySQL에서 사용자 정보 조회 로직
- [ ] `POST /api/profile/:token`: 정보 수정 및 DB 업데이트 로직

---

## Phase 2: 공고 수집 파이프라인 (Scraper)

- [ ] 라즈베리파이에서 동작할 크롤링 스크립트 작성 (Python/Node.js)
- [ ] 잡알리오 공고 목록 수집 -> PDF 다운로드 -> Gemini API 분석
- [ ] 결과를 라즈베리파이 내부 MySQL에 직접 저장

---

## Phase 3: 매칭 엔진 + 이메일 알림

- [ ] 신규 공고 발생 시 사용자 매칭 쿼리 실행
- [ ] 매칭된 사용자들에게 이메일 발송 (Cloudflare Functions 또는 Scraper Script에서 처리)

---

## Phase 4: 통합 테스트 + 배포

- [ ] E2E 테스트: 가입 -> 수정 -> 공고 매칭 -> 이메일 수신 전체 과정 확인
- [ ] Cloudflare Tunnel 보안 설정 최종 점검
