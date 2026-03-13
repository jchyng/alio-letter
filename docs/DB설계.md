# DB 설계

## 기술 선택: SQLite

| 항목 | 내용 |
|------|------|
| DB | SQLite 3 |
| 이유 | 서버리스, 별도 설치 불요, 소규모 데이터(~350기관, 연 수백건 공고)에 적합 |
| 파일 위치 | `data/alio.db` (앱과 같은 서버에 파일로 존재) |
| 주의 | 동시 쓰기 제한 → 수집기 실행 시 write lock 관리 필요 |

**SQLite 타입 규칙:**
- PK: `INTEGER PRIMARY KEY AUTOINCREMENT`
- 날짜: `TEXT` (ISO 8601 형식 `YYYY-MM-DD`)
- 시간: `TEXT` (ISO 8601 형식 `YYYY-MM-DDTHH:MM:SS`)
- JSON 배열/객체: `TEXT` (JSON 문자열로 저장, `json_extract()` / `json_each()`로 조회)
- 불리언: `INTEGER` (0 = false, 1 = true)
- 소수: `REAL`

---

## 설계 원칙

1. PDF의 "선발분야 및 인원" 피벗 테이블을 행 단위로 정규화
2. 같은 공고 안에서 채용구분별로 지원자격·전형방법이 다르므로, `recruitment_sections`을 중간 계층으로 둔다
3. 급여정보는 기관 단위로 분리 (공고와 독립적으로 수집)
4. 사용자 매칭에 필요한 필드를 기준으로 설계

---

## 테이블 관계도

```
institutions (기관)
  ├── salary_info (급여 - 연도별)
  └── job_postings (채용공고)
        └── recruitment_sections (채용구분 섹션)
              ├── recruitment_units (직무별 채용인원) ⭐ 핵심
              ├── selection_stages (전형 단계)
              ├── bonus_points (가점 항목)
              └── qualification_requirements (지원자격)

users (사용자)
  ├── user_profiles (스펙 정보)
  ├── user_certificates (자격증)
  └── user_preferences (희망조건)
```

---

## 공고 데이터 테이블

### 1. institutions (기관)

기관은 알리오 기준 약 350개 공공기관. 공고와 독립적으로 미리 수집해둔다.

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| id | INTEGER PK | 자동 증가 | |
| name | TEXT NOT NULL | 기관명 | 한국남부발전(주) |
| alio_id | TEXT UNIQUE | 알리오 기관 식별자 | |
| category | TEXT | 기관 유형 | 공기업, 준정부기관, 기타공공기관 |
| headquarters | TEXT | 본사 소재지 | 부산 |
| website_url | TEXT | 기관 홈페이지 | |
| created_at | TEXT | ISO 8601 | |

---

### 2. salary_info (급여정보)

알리오 공시 데이터 기반. 기관별 + 연도별로 저장. 수집 봇이 공고 상세 페이지의 '연봉보러가기' 버튼을 클릭하여 DB에 없는 경우 실시간으로 수집하여 중복 없이 저장한다.

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| id | INTEGER PK | | |
| institution_id | INTEGER FK | 기관 | |
| fiscal_year | INTEGER | 결산 연도 | 2024 |
| employment_type | TEXT | 고용형태 | 정규직(일반정규직) |
| base_salary | INTEGER | 기본급 (천원/월) | 60095 |
| fixed_allowance | INTEGER | 고정수당 | 11074 |
| performance_allowance | INTEGER | 실적수당 | 5346 |
| bonus | INTEGER | 성과상여금 | 23128 |
| avg_annual_salary | INTEGER | 1인당 평균 보수액 | 99777 |
| avg_salary_male | INTEGER | 남성 평균 | 103233 |
| avg_salary_female | INTEGER | 여성 평균 | 80573 |
| headcount | REAL | 상시 종업원수 | 2652.49 |
| avg_tenure_months | INTEGER | 평균 근속연수(개월) | 193 |
| source_url | TEXT | 출처 URL | |
| created_at | TEXT | ISO 8601 | |

> UNIQUE(institution_id, fiscal_year, employment_type)

---

### 3. job_postings (채용공고)

잡알리오에서 수집한 공고 1건 = 1행

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| id | INTEGER PK | | |
| institution_id | INTEGER FK | 기관 | |
| posting_number | TEXT | 공고번호 | 채용공고 2026-01호 |
| title | TEXT | 공고 제목 | 2026년 상반기 신입사원 및 별정직 채용공고 |
| posted_date | TEXT | 공고일 (YYYY-MM-DD) | 2026-02-23 |
| application_start | TEXT | 접수 시작일 | |
| application_end | TEXT | 접수 마감일 | |
| total_headcount | INTEGER | 총 채용인원 | 102 |
| source_url | TEXT | 잡알리오 원문 링크 | |
| pdf_url | TEXT | 첨부 PDF 링크 | |
| ai_summary | TEXT | AI가 생성한 전체 요약 | |
| status | TEXT | 상태 | active / closed / upcoming |
| raw_extracted_data | TEXT | LLM이 추출한 원본 JSON 문자열 | |
| created_at | TEXT | ISO 8601 | |

---

### 4. recruitment_sections (채용구분 섹션) ⭐

**PDF 분석 핵심 발견: 하나의 공고 안에 여러 채용구분이 있고, 각각 지원자격·전형방법이 다르다.**

한국남부발전 PDF 기준 섹션:
- II. 신입사원 (대졸수준-일반)
- III. 신입사원 (대졸수준-장애)
- IV. 신입사원 (대졸수준-보훈)
- V. 신입사원 (고졸수준)
- VI. 별정직 (기술담당원)

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| id | INTEGER PK | | |
| posting_id | INTEGER FK | 공고 | |
| section_name | TEXT | 섹션명 | 신입사원 (대졸수준-일반) |
| recruitment_type | TEXT | 채용구분 | 일반, 장애, 보훈, 고졸, 별정직 |
| education_level | TEXT | 학력수준 | 대졸수준, 고졸수준 |
| grade | TEXT | 채용직급 | 4직급(나), 4직급(다), 6직급 |
| probation_months | INTEGER | 수습기간(월) | 3 |
| work_locations | TEXT | 근무지역 (JSON 배열) | ["부산","하동","인천","제주","영월","안동","삼척","세종"] |
| work_type | TEXT | 근무형태 | 통상근무 혹은 교대근무 |
| section_order | INTEGER | 섹션 순서 | 1, 2, 3... |
| created_at | TEXT | ISO 8601 | |

---

### 5. recruitment_units (채용 단위 - 직무별 인원) ⭐⭐ 핵심

PDF "선발분야 및 인원" 피벗 테이블의 **각 셀**이 1행이 된다.

**변환 예시:**
```
PDF 피벗:        사무  ICT  기계  전기  화학  토목  건축
대졸-일반:        8    7    25   21    7    4    7

DB 행 변환:
section=대졸-일반 | job_field=사무     | headcount=8
section=대졸-일반 | job_field=ICT      | headcount=7
section=대졸-일반 | job_field=발전-기계  | headcount=25
section=대졸-일반 | job_field=발전-전기  | headcount=21
section=대졸-일반 | job_field=화학      | headcount=7
section=대졸-일반 | job_field=토목      | headcount=4
section=대졸-일반 | job_field=건축      | headcount=7
```

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| id | INTEGER PK | | |
| section_id | INTEGER FK | 채용구분 섹션 | |
| posting_id | INTEGER FK | 공고 (빠른 조회용) | |
| job_field | TEXT NOT NULL | 직무 분야 | 사무, ICT, 발전-기계, 발전-전기, 화학, 토목, 건축 |
| headcount | INTEGER NOT NULL | 채용 인원 | 25 |
| note | TEXT | 비고 | 하동 (별정직 근무지 특정) |

---

### 6. qualification_requirements (지원자격)

**채용구분마다 다르다!** 대졸-일반은 학력 무관인데, 고졸은 고졸만 가능. 별정직은 특정 자격증 필수.

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| id | INTEGER PK | | |
| section_id | INTEGER FK | 채용구분 섹션 | |
| age_limit | TEXT | 연령 | 제한 없음 (정년 만60세) |
| education_req | TEXT | 학력 | 제한 없음 / 고졸 졸업 또는 졸업예정 |
| certificate_req | TEXT | 자격 요건 | 제한 없음 / 폐기물처리기술사... |
| language_req | TEXT | 어학 | 제한 없음 |
| military_req | TEXT | 병역 | 불이행자 제외 |
| disability_req | TEXT | 장애 요건 | 장애인 등록자 (장애 채용 시) |
| veteran_req | TEXT | 보훈 요건 | 취업지원대상자 (보훈 채용 시) |
| other_req | TEXT | 기타 | 하동 출퇴근 가능자 (별정직) |
| preferred_certs | TEXT | 우대 자격증 (JSON 배열) | ["폐기물처리기사","수질환경기사",...] |

---

### 7. selection_stages (전형 단계)

**채용구분마다 전형이 다르다!**
- 대졸-일반 1단계: 서류(30배수) — 외국어성적(50점) + 자격증가점(50점)
- 대졸-장애 1단계: 서류면제
- 고졸 1단계: 서류(30배수) — 자격증가점(20점)만
- 별정직 1단계: 서류(30배수) — 직무능력기반 지원서 심사

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| id | INTEGER PK | | |
| section_id | INTEGER FK | 채용구분 섹션 | |
| stage_number | INTEGER | 단계 | 1, 2, 3, 4, 5 |
| stage_name | TEXT | 단계명 | 서류심사, 필기전형, 면접전형, 합격예정자결정, 신체검사 |
| details | TEXT | 세부사항 | 외국어성적(50점) + 자격증가점(최대50점) |
| pass_ratio | TEXT | 선발배수 | 30배수, 3배수, 적부판정 |
| max_score | INTEGER | 배점 (있을 경우) | 400 |
| sub_items | TEXT | 하위 평가 항목 (JSON 배열) | 아래 참고 |

**sub_items 예시 (대졸-일반 1단계 서류심사):**
```json
[
  {"name": "외국어성적", "max_score": 50, "formula": "(토익환산점수÷850)×50, 850점 이상 50점 만점"},
  {"name": "자격증가점", "max_score": 50, "note": "별첨 6 참고"}
]
```

**sub_items 예시 (대졸-일반 2단계 필기):**
```json
[
  {"name": "직무능력평가(K-JAT)", "max_score": 100, "note": "직무수행+직업기초능력"},
  {"name": "전공기초-사무(상경분야)", "max_score": 100, "note": "경제학,회계학,경영학 50문항"},
  {"name": "전공기초-기술", "max_score": 100, "note": "지원분야 기사 수준 50문항"}
]
```

---

### 8. bonus_points (가점 항목)

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| id | INTEGER PK | | |
| posting_id | INTEGER FK | 공고 단위 (대부분 공고 전체 공통) | |
| bonus_type | TEXT | 가산유형 | 등록장애인, 취업지원대상자, 고급자격증... |
| description | TEXT | 유형 정의 | 장애인고용촉진법에 의한 등록자 |
| document_effect | TEXT | 서류 가점 | 면제, 배점의10%, 배점의5%, null |
| written_effect | TEXT | 필기 가점 | 배점의10%, 관련법령, null |
| interview_effect | TEXT | 면접 가점 | 배점의10%, 관련법령, null |
| max_cumulative_pct | INTEGER | 전형별 한도(%) | 10 |
| required_docs | TEXT | 증빙서류 | 장애인 증빙서류 |

---

### 9. recruitment_targets (채용목표제)

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| id | INTEGER PK | | |
| posting_id | INTEGER FK | | |
| target_type | TEXT | 목표제 유형 | 이전지역인재, 이공계양성평등 |
| description | TEXT | 상세 설명 | 부산광역시 소재 학교 졸업자 |
| target_rate_pct | INTEGER | 목표 비율(%) | 30 |
| applicable_fields | TEXT | 적용 모집단위 (JSON 배열) | ["발전-기계","발전-전기"] |
| conditions | TEXT | 적용 조건 | 분야별 연 채용모집인원 6인 이상 |

---

## 사용자 데이터 (Google Sheets → SQLite 동기화)

사용자 데이터의 원본은 Google Form → Google Sheets이며, n8n 워크플로우가 매칭용으로 SQLite에 동기화한다.

### 10. users (사용자 — Sheets 동기화)

Google Sheets의 폼 응답 + 결제 관리 시트를 합쳐서 하나의 테이블로 동기화.

| 컬럼 | 타입 | 설명 | Sheets 원본 |
|------|------|------|------------|
| id | INTEGER PK | | 자동 생성 |
| email | TEXT UNIQUE NOT NULL | 이메일 | Form: 이메일 |
| name | TEXT | 이름 | Form: 이름 |
| is_active | INTEGER | 활성 사용자 (0/1) | 관리시트: 결제상태=완료 AND 만료일 미도래 |
| education_level | TEXT | 최종학력 | Form: 최종학력 |
| military_status | TEXT | 병역 상태 | Form: 병역 상태 |
| is_disabled | INTEGER | 장애인 (0/1) | Form: 가점 항목 체크박스 |
| is_veteran_family | INTEGER | 취업지원대상자 (0/1) | Form: 가점 항목 체크박스 |
| is_low_income | INTEGER | 저소득층 (0/1) | Form: 가점 항목 체크박스 |
| is_north_defector | INTEGER | 북한이탈주민 (0/1) | Form: 가점 항목 체크박스 |
| is_multicultural | INTEGER | 다문화가족 (0/1) | Form: 가점 항목 체크박스 |
| is_self_reliance | INTEGER | 자립준비청년 (0/1) | Form: 가점 항목 체크박스 |
| residence_region | TEXT | 거주 지역 | Form: 거주 지역 |
| toeic_score | INTEGER | 토익 점수 | Form: 토익 점수 |
| toeic_speaking_level | TEXT | 토익스피킹 레벨 | Form: 토익스피킹 |
| opic_level | TEXT | OPIc 레벨 | Form: OPIc |
| certificates | TEXT | 보유 자격증 (JSON 배열) | Form: 자격증 (쉼표 구분 → 파싱) |
| preferred_fields | TEXT | 희망 직무 (JSON 배열) | Form: 희망 직무 체크박스 |
| preferred_regions | TEXT | 희망 지역 (JSON 배열) | Form: 희망 지역 체크박스 |
| preferred_types | TEXT | 희망 채용구분 (JSON 배열) | Form: 희망 채용구분 체크박스 |
| preferred_institutions | TEXT | 관심 기관 (JSON 배열) | Form: 관심 기관 (쉼표 구분 → 파싱) |
| synced_at | TEXT | 마지막 동기화 시각 | n8n이 기록 |

> 기존 4개 테이블(users, user_profiles, user_certificates, user_preferences)을 1개로 통합.
> 원본은 Google Sheets, SQLite는 매칭 쿼리용 사본.
> n8n Google Sheets Trigger가 변경 감지 → UPSERT (email 기준).

---

## 매칭 쿼리 예시

**특정 사용자에게 맞는 신규 공고 찾기 (n8n Code 노드에서 실행):**

```sql
-- 사용자의 희망 직무/지역에 매칭되는 공고 조회
SELECT
  u.email,
  u.name,
  p.title,
  p.id AS posting_id,
  i.name AS institution_name,
  rs.recruitment_type,
  rs.grade,
  ru.job_field,
  ru.headcount,
  rs.work_locations,
  p.source_url
FROM users u, recruitment_units ru
JOIN recruitment_sections rs ON ru.section_id = rs.id
JOIN job_postings p ON ru.posting_id = p.id
JOIN institutions i ON p.institution_id = i.id
WHERE u.is_active = 1
  AND p.status = 'active'
  AND p.id = ?  -- 신규 공고 ID
  AND EXISTS (
    SELECT 1 FROM json_each(u.preferred_fields) uf
    WHERE uf.value = ru.job_field
  )
  AND EXISTS (
    SELECT 1 FROM json_each(u.preferred_regions) ur,
                  json_each(rs.work_locations) wl
    WHERE ur.value = wl.value
  )
ORDER BY u.email, ru.job_field;
```

> **SQLite JSON 조회 참고:** `json_each()` 테이블 반환 함수로 JSON 배열을 행으로 풀어서 비교한다.
> 배열에 특정 값이 있는지 확인: `EXISTS (SELECT 1 FROM json_each(컬럼) WHERE json_each.value = '값')`

**결과 예시:**
```
user@email.com | 홍길동 | 한국남부발전(주) | 일반 | 4직급(나) | 발전-전기 | 21명 | ["부산","하동",...]
user@email.com | 홍길동 | 한국남부발전(주) | 장애 | 4직급(나) | 발전-전기 | 2명  | ["부산","하동",...]
user@email.com | 홍길동 | 한국남부발전(주) | 보훈 | 4직급(나) | 발전-전기 | 1명  | ["부산","하동",...]
```

---

## PDF → DB 매핑 검증

한국남부발전 PDF의 102명이 recruitment_units에 빠짐없이 들어가는지 확인:

| section (채용구분) | job_field | headcount | ✅ |
|-------------------|-----------|-----------|-----|
| 대졸-일반 | 사무 | 8 | ✅ |
| 대졸-일반 | ICT | 7 | ✅ |
| 대졸-일반 | 발전-기계 | 25 | ✅ |
| 대졸-일반 | 발전-전기 | 21 | ✅ |
| 대졸-일반 | 화학 | 7 | ✅ |
| 대졸-일반 | 토목 | 4 | ✅ |
| 대졸-일반 | 건축 | 7 | ✅ |
| 대졸-지역전문 | 발전-기계 | 2 | ✅ |
| 대졸-지역전문 | 발전-전기 | 2 | ✅ |
| 대졸-장애 | 사무 | 1 | ✅ |
| 대졸-장애 | 발전-기계 | 2 | ✅ |
| 대졸-장애 | 발전-전기 | 2 | ✅ |
| 대졸-장애 | 화학 | 1 | ✅ |
| 대졸-보훈 | ICT | 1 | ✅ |
| 대졸-보훈 | 발전-기계 | 1 | ✅ |
| 대졸-보훈 | 발전-전기 | 1 | ✅ |
| 대졸-보훈 | 화학 | 1 | ✅ |
| 고졸 | 발전-기계 | 4 | ✅ |
| 고졸 | 발전-전기 | 4 | ✅ |
| 별정직 | 기술담당원 | 1 | ✅ |
| **합계** | | **102** | ✅ |

> 20행, 합계 102명 — PDF와 정확히 일치
