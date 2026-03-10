# Alio-Letter 구현 Step-by-Step 계획서

> 잡알리오 채용공고 자동 분석 & 맞춤 알림 서비스
> 기술 스택: n8n (라즈베리파이) + Google Form/Sheets + MySQL + Gemini API + Gmail

---

## 인프라 환경

| 항목       | 값                                                              |
| ---------- | --------------------------------------------------------------- |
| 호스트     | Raspberry Pi                                                    |
| n8n        | Docker 컨테이너, Named Volume `n8n_data`                        |
| MySQL      | 기존 `gitea_mysql` 컨테이너 (MySQL 8), DB명 `alio_letter`      |
| n8n → MySQL 접속 | Host: `gitea_mysql`, Port: `3306`, User: `alio`           |
| Assets     | `/home/node/.n8n/assets/`                                       |
| 파일 복사  | `docker cp <파일> n8n:/home/node/.n8n/assets/`                  |

### n8n Docker 실행 (확정)

```bash
docker run -d \
  --name n8n \
  --restart always \
  -p 5678:5678 \
  -e N8N_SECURE_COOKIE=false \
  -e GENERIC_TIMEZONE=Asia/Seoul \
  -e TZ=Asia/Seoul \
  -v n8n_data:/home/node/.n8n \
  n8nio/n8n
```

> npm install, 외부 모듈 허용 등 추가 설정 불필요. n8n 내장 MySQL 노드만 사용.

---

## Phase 0: 환경 셋업

### Step 0-1. MySQL DB + 유저 생성

```bash
# n8n과 gitea_mysql이 같은 네트워크에 있는지 확인
docker network ls
docker inspect gitea_mysql --format='{{range .NetworkSettings.Networks}}{{.NetworkName}} {{end}}'

# 같은 네트워크에 n8n 연결 (필요한 경우)
docker network connect <네트워크이름> n8n
```

```bash
# DB 및 유저 생성
docker exec -it gitea_mysql mysql -u root -p -e "
CREATE DATABASE IF NOT EXISTS alio_letter
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'alio'@'%' IDENTIFIED BY '원하는비밀번호';
GRANT ALL PRIVILEGES ON alio_letter.* TO 'alio'@'%';
FLUSH PRIVILEGES;
"
```

**확인 사항:**

- `docker exec gitea_mysql mysql -u alio -p -e "SHOW DATABASES"` → `alio_letter` 확인
- n8n Credentials → MySQL 추가 (Host: `gitea_mysql`, Port: 3306, DB: `alio_letter`, User: `alio`)
- n8n MySQL 노드에서 `SELECT 1` 테스트 성공

### Step 0-2. 스키마 생성

n8n MySQL 노드 또는 CLI에서 아래 SQL을 실행한다.

```sql
-- 1. institutions (기관)
CREATE TABLE IF NOT EXISTS institutions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  alio_id VARCHAR(50) UNIQUE,
  category VARCHAR(100),
  headquarters VARCHAR(100),
  website_url VARCHAR(500),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. salary_info (급여정보)
CREATE TABLE IF NOT EXISTS salary_info (
  id INT AUTO_INCREMENT PRIMARY KEY,
  institution_id INT,
  fiscal_year INT,
  employment_type VARCHAR(50),
  base_salary INT,
  fixed_allowance INT,
  performance_allowance INT,
  bonus INT,
  avg_annual_salary INT,
  avg_salary_male INT,
  avg_salary_female INT,
  headcount DECIMAL(10,1),
  avg_tenure_months INT,
  source_url VARCHAR(500),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_salary (institution_id, fiscal_year, employment_type),
  FOREIGN KEY (institution_id) REFERENCES institutions(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. job_postings (채용공고)
CREATE TABLE IF NOT EXISTS job_postings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  institution_id INT,
  posting_number VARCHAR(100),
  title VARCHAR(500),
  posted_date DATE,
  application_start DATE,
  application_end DATE,
  total_headcount INT,
  source_url VARCHAR(500),
  pdf_url VARCHAR(500),
  ai_summary TEXT,
  status VARCHAR(20) DEFAULT 'active',
  raw_extracted_data JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (institution_id) REFERENCES institutions(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. recruitment_sections (채용구분 섹션)
CREATE TABLE IF NOT EXISTS recruitment_sections (
  id INT AUTO_INCREMENT PRIMARY KEY,
  posting_id INT,
  section_name VARCHAR(200),
  recruitment_type VARCHAR(50),
  education_level VARCHAR(50),
  grade VARCHAR(50),
  probation_months INT,
  work_locations JSON,
  work_type VARCHAR(50),
  section_order INT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (posting_id) REFERENCES job_postings(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. recruitment_units (직무별 채용인원)
CREATE TABLE IF NOT EXISTS recruitment_units (
  id INT AUTO_INCREMENT PRIMARY KEY,
  section_id INT,
  posting_id INT,
  job_field VARCHAR(100) NOT NULL,
  headcount INT NOT NULL,
  note TEXT,
  FOREIGN KEY (section_id) REFERENCES recruitment_sections(id),
  FOREIGN KEY (posting_id) REFERENCES job_postings(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. qualification_requirements (지원자격)
CREATE TABLE IF NOT EXISTS qualification_requirements (
  id INT AUTO_INCREMENT PRIMARY KEY,
  section_id INT,
  age_limit VARCHAR(100),
  education_req VARCHAR(100),
  certificate_req TEXT,
  language_req TEXT,
  military_req VARCHAR(200),
  disability_req VARCHAR(200),
  veteran_req VARCHAR(200),
  other_req TEXT,
  preferred_certs TEXT,
  FOREIGN KEY (section_id) REFERENCES recruitment_sections(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. selection_stages (전형 단계)
CREATE TABLE IF NOT EXISTS selection_stages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  section_id INT,
  stage_number INT,
  stage_name VARCHAR(100),
  details TEXT,
  pass_ratio VARCHAR(50),
  max_score INT,
  sub_items JSON,
  FOREIGN KEY (section_id) REFERENCES recruitment_sections(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. bonus_points (가점 항목)
CREATE TABLE IF NOT EXISTS bonus_points (
  id INT AUTO_INCREMENT PRIMARY KEY,
  posting_id INT,
  bonus_type VARCHAR(100),
  description TEXT,
  document_effect VARCHAR(100),
  written_effect VARCHAR(100),
  interview_effect VARCHAR(100),
  max_cumulative_pct INT,
  required_docs TEXT,
  FOREIGN KEY (posting_id) REFERENCES job_postings(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. recruitment_targets (채용목표제)
CREATE TABLE IF NOT EXISTS recruitment_targets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  posting_id INT,
  target_type VARCHAR(100),
  description TEXT,
  target_rate_pct INT,
  applicable_fields TEXT,
  conditions TEXT,
  FOREIGN KEY (posting_id) REFERENCES job_postings(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. users (사용자)
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(200) UNIQUE NOT NULL,
  name VARCHAR(100),
  is_active TINYINT DEFAULT 0,
  education_level VARCHAR(50),
  military_status VARCHAR(20),
  is_disabled TINYINT DEFAULT 0,
  is_veteran_family TINYINT DEFAULT 0,
  is_low_income TINYINT DEFAULT 0,
  is_north_defector TINYINT DEFAULT 0,
  is_multicultural TINYINT DEFAULT 0,
  is_self_reliance TINYINT DEFAULT 0,
  residence_region VARCHAR(20),
  toeic_score INT,
  toeic_speaking_level VARCHAR(10),
  opic_level VARCHAR(10),
  certificates JSON,
  preferred_fields JSON,
  preferred_regions JSON,
  preferred_types JSON,
  preferred_institutions JSON,
  synced_at DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**확인 사항:**

- `SHOW TABLES FROM alio_letter` → 10개 테이블 확인
- n8n MySQL 노드에서 `SELECT COUNT(*) FROM users` 실행 성공

### Step 0-3. 외부 API 키 및 인증 설정

| 항목                  | 설정 방법                                                        |
| --------------------- | ---------------------------------------------------------------- |
| Google Cloud 프로젝트 | console.cloud.google.com에서 생성                                |
| Sheets API            | 활성화                                                           |
| Gmail API             | 활성화                                                           |
| Gemini API Key        | Google AI Studio에서 발급                                        |
| n8n Credentials       | MySQL, Google OAuth2 (Sheets, Gmail), HTTP Header Auth (Gemini)  |

**확인 사항:**

- n8n에서 Google Sheets 노드 테스트 → 시트 읽기 성공
- n8n에서 Gmail 노드 테스트 → 테스트 이메일 발송 성공
- Gemini API 키로 간단한 텍스트 요청 → 응답 확인

---

## Phase 1: 사용자 등록 시스템

### Step 1-1. Google Form 생성

**3개 섹션 구성:**

**섹션 1 — 기본정보**

- 이름 (단답형, 필수)
- 이메일 (단답형, 이메일 검증, 필수)
- 거주 지역 (드롭다운: 서울, 부산, 대구, 인천, 광주, 대전, 울산, 세종, 경기, 강원, 충북, 충남, 전북, 전남, 경북, 경남, 제주)

**섹션 2 — 스펙 정보**

- 최종학력 (드롭다운: 고졸, 전문대졸, 대졸, 석사이상)
- 병역 상태 (드롭다운: 미필, 군필, 면제, 해당없음)
- 토익 점수 (단답형, 숫자 검증, 선택)
- 토익스피킹 레벨 (드롭다운: 없음, Lv5, Lv6, Lv7, Lv8)
- OPIc 레벨 (드롭다운: 없음, IL, IM1, IM2, IM3, IH, AL)
- 보유 자격증 (장문형, 쉼표로 구분 입력 안내)
- 가점 해당 항목 (체크박스: 등록장애인, 취업지원대상자, 저소득층, 북한이탈주민, 다문화가족, 자립준비청년)

**섹션 3 — 희망 조건**

- 희망 직무 (체크박스: 사무, ICT, 기계, 전기, 화학, 토목, 건축, 환경, 기타)
- 희망 지역 (체크박스: 17개 시도)
- 희망 채용구분 (체크박스: 일반, 장애, 보훈, 고졸, 별정직)
- 관심 기관 (장문형, 쉼표로 구분, 선택)

**확인 사항:**

- 미리보기로 전체 폼 흐름 확인
- 테스트 응답 제출 → Google Sheets에 데이터 기록 확인

### Step 1-2. Apps Script 설정 (수정 링크 자동 발송)

Google Sheets → 확장 프로그램 → Apps Script에서 아래 코드 배포:

```javascript
function onFormSubmit(e) {
  var response = e.response;
  var email =
    response.getRespondentEmail() ||
    response.getItemResponses()[1].getResponse();
  var editUrl = response.getEditResponseUrl();

  GmailApp.sendEmail(email, "[알리오레터] 프로필 등록 완료", "", {
    htmlBody: `
        <h2>프로필 등록이 완료되었습니다!</h2>
        <p>아래 링크로 언제든 정보를 수정할 수 있습니다:</p>
        <p><a href="${editUrl}">프로필 수정하기</a></p>
        <p>결제가 확인되면 서비스가 활성화됩니다.</p>
      `,
  });
}
```

**설정:**

- 트리거 추가: `onFormSubmit` → 폼 제출 시 실행
- 권한 승인

**확인 사항:**

- 폼 제출 후 이메일에 수정 링크 도착 확인
- 수정 링크로 접근 → 기존 응답 수정 가능 확인

### Step 1-3. n8n 워크플로우: Google Sheets → MySQL 사용자 동기화

```
[Google Sheets Trigger] (행 추가/수정 감지)
    ↓
[Code 노드] Sheets 데이터 → users 테이블 형식으로 변환
    - 체크박스 → is_disabled, is_veteran_family 등 0/1 매핑
    - 쉼표 구분 텍스트 → JSON 배열 변환
    - 희망조건 체크박스 → JSON 배열 변환
    ↓
[MySQL] UPSERT (email 기준)
    INSERT INTO users (...) VALUES (...)
    ON DUPLICATE KEY UPDATE ...
```

**Code 노드 핵심 변환 로직:**

```javascript
// 자격증: "정보처리기사, 전기기사" → JSON 배열
const certs = row.certificates
  ? JSON.stringify(
      row.certificates
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    )
  : "[]";

// 체크박스: "등록장애인, 취업지원대상자" → 각 플래그 매핑
const bonusItems = (row.bonus_items || "").split(",").map((s) => s.trim());
const is_disabled = bonusItems.includes("등록장애인") ? 1 : 0;
const is_veteran_family = bonusItems.includes("취업지원대상자") ? 1 : 0;
// ... 나머지 동일 패턴

// 희망직무: 체크박스 결과 → JSON 배열
const preferred_fields = JSON.stringify(
  (row.preferred_fields || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean),
);
```

**MySQL UPSERT 구문:**

```sql
INSERT INTO users (email, name, education_level, military_status,
  is_disabled, is_veteran_family, is_low_income, is_north_defector,
  is_multicultural, is_self_reliance, residence_region,
  toeic_score, toeic_speaking_level, opic_level,
  certificates, preferred_fields, preferred_regions,
  preferred_types, preferred_institutions, synced_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW())
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  education_level = VALUES(education_level),
  military_status = VALUES(military_status),
  is_disabled = VALUES(is_disabled),
  is_veteran_family = VALUES(is_veteran_family),
  is_low_income = VALUES(is_low_income),
  is_north_defector = VALUES(is_north_defector),
  is_multicultural = VALUES(is_multicultural),
  is_self_reliance = VALUES(is_self_reliance),
  residence_region = VALUES(residence_region),
  toeic_score = VALUES(toeic_score),
  toeic_speaking_level = VALUES(toeic_speaking_level),
  opic_level = VALUES(opic_level),
  certificates = VALUES(certificates),
  preferred_fields = VALUES(preferred_fields),
  preferred_regions = VALUES(preferred_regions),
  preferred_types = VALUES(preferred_types),
  preferred_institutions = VALUES(preferred_institutions),
  synced_at = NOW();
```

**확인 사항:**

- Google Form 제출 → Sheets 기록 → n8n 트리거 발동 → MySQL 저장 확인
- `SELECT * FROM users WHERE email = 'test@test.com'` 으로 데이터 정합성 확인
- 폼 수정 → Sheets 업데이트 → MySQL UPSERT 확인

---

## Phase 2: 공고 수집 파이프라인

### Step 2-1. 잡알리오 크롤링 구조 분석

먼저 잡알리오 사이트 구조를 파악한다.

**타겟 URL:** `https://job.alio.go.kr/recruit.do` (채용정보 목록)

```
[브라우저 개발자도구]
    ↓
1. 공고 목록 페이지 요청/응답 구조 분석
   - GET/POST 파라미터
   - 페이징 방식
   - 응답 HTML/JSON 구조
    ↓
2. 공고 상세 페이지 구조 분석
   - 상세 URL 패턴
   - PDF 첨부파일 다운로드 URL 패턴
    ↓
3. 필요한 요청 헤더 확인
   - User-Agent, Cookie, Referer 등
```

**확인 사항:**

- n8n HTTP Request 노드로 공고 목록 조회 성공
- 상세 페이지 접근 및 PDF URL 추출 성공

### Step 2-2. n8n 워크플로우 1 구축: 신규 공고 탐색

```
[Schedule Trigger] 매일 09:00, 18:00
    ↓
[HTTP Request] 잡알리오 공고 목록 조회
    ↓
[Code 노드] HTML/JSON 파싱 → 공고 목록 추출
    - 각 공고의 {제목, 기관명, 상세URL, 공고일}
    ↓
[MySQL] 기존 수집된 공고의 source_url 목록 조회
    ↓
[Code 노드] 신규 공고 필터링
    - 이미 DB에 있는 URL 제외
    - 결과를 Stack(배열) 형태로 정리 (과거→최신 순)
    ↓
[IF] 신규 공고 있음?
    ├── YES → Step 2-3으로 진행 (Loop)
    └── NO  → 종료
```

### Step 2-3. n8n 워크플로우 1 구축: 공고 처리 Loop

```
[Loop Over Items] 신규 공고 Stack 순회
    ↓
  ┌─ [HTTP Request] 상세 페이지 접근
  │      ↓
  │  [Code 노드] 메타데이터 추출
  │    - 기관명, 공고번호, 마감일, PDF URL 등
  │      ↓
  │  [MySQL] institutions 테이블에 기관 UPSERT
  │    - INSERT ... ON DUPLICATE KEY UPDATE
  │      ↓
  │  [HTTP Request] PDF 다운로드 (Binary 모드)
  │      ↓
  │  [Step 2-4] Gemini API 호출 → JSON 추출
  │      ↓
  │  [Step 2-5] JSON 검증 + DB 저장
  │      ↓
  │  [Step 2-6] AI 요약 생성 + 저장
  └─ [다음 항목으로]
```

### Step 2-4. Gemini API 연동: PDF → 구조화 JSON 추출

**n8n HTTP Request 노드 설정:**

```
Method: POST
URL: https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={{$credentials.geminiApiKey}}

Headers:
  Content-Type: application/json

Body (JSON):
{
  "contents": [
    {
      "parts": [
        {
          "inline_data": {
            "mime_type": "application/pdf",
            "data": "{{$binary.data.toBase64()}}"
          }
        },
        {
          "text": "<프롬프트 내용 — LLM추출_프롬프트설계.md의 시스템 프롬프트 + JSON 스키마>"
        }
      ]
    }
  ],
  "generationConfig": {
    "temperature": 0.1,
    "responseMimeType": "application/json"
  }
}
```

**프롬프트 파일 저장:**

```bash
docker exec n8n mkdir -p /home/node/.n8n/assets
docker cp ./prompt.md n8n:/home/node/.n8n/assets/prompt.md
```

- LLM추출\_프롬프트설계.md의 시스템 프롬프트 전체를 `prompt.md`로 저장
- JSON 스키마 포함
- n8n에서 Read Binary File 노드로 `/home/node/.n8n/assets/prompt.md` 읽어서 API 요청에 삽입

**확인 사항:**

- 실제 잡알리오 PDF 1건으로 테스트
- 응답 JSON이 스키마에 맞는지 수동 확인
- `validation.match == true` 확인

### Step 2-5. JSON 검증 + DB 분산 저장

**Code 노드 — 검증 로직:**

```javascript
const data = JSON.parse(geminiResponse);

// 1. 필수 필드 체크
const meta = data.posting_meta;
if (!meta.institution_name || !meta.title || !meta.total_headcount) {
  return { valid: false, reason: "missing_meta_fields" };
}

// 2. sections 존재 확인
if (!data.sections || data.sections.length === 0) {
  return { valid: false, reason: "no_sections" };
}

// 3. 인원 합계 검증
let unitsSum = 0;
for (const section of data.sections) {
  for (const unit of section.units || []) {
    unitsSum += unit.headcount;
  }
}
if (unitsSum !== meta.total_headcount) {
  return {
    valid: false,
    reason: `headcount_mismatch: ${unitsSum} vs ${meta.total_headcount}`,
  };
}

return { valid: true, data };
```

**DB 저장 순서 (MySQL 노드 체이닝):**

```
1. job_postings INSERT → LAST_INSERT_ID()로 posting_id 획득
2. sections 순회:
   a. recruitment_sections INSERT → section_id 획득
   b. recruitment_units INSERT (section_id, posting_id 참조)
   c. qualification_requirements INSERT (section_id 참조)
   d. selection_stages INSERT (section_id 참조)
3. bonus_points INSERT (posting_id 참조)
4. recruitment_targets INSERT (posting_id 참조)
5. job_postings UPDATE → raw_extracted_data에 원본 JSON 저장
6. job_postings UPDATE → status = 'active' (검증 통과) 또는 'review_needed' (실패)
```

**확인 사항:**

- PDF 1건 처리 후 모든 테이블에 데이터가 올바르게 분산 저장되었는지 확인
- `SELECT SUM(headcount) FROM recruitment_units WHERE posting_id = ?` == `total_headcount`
- 검증 실패 케이스도 테스트 (일부러 headcount 불일치 유발)

### Step 2-6. AI 요약 생성

**별도 Gemini API 호출 (요약 전용):**

```
프롬프트:
"아래 채용공고 PDF를 읽고 취준생에게 유용한 핵심 정보를 200자 이내로 요약하세요.
포함할 내용: 기관명, 총 채용인원, 주요 직무, 접수기간, 특이사항"
```

**결과를 `job_postings.ai_summary`에 저장.**

---

## Phase 3: 매칭 엔진 + 이메일 알림

### Step 3-1. 매칭 로직 설계

매칭은 3단계로 수행한다:

**1단계: 희망조건 필터 (필수 매칭)**

```sql
-- 사용자의 희망 직무/지역에 맞는 공고 유닛 추출
SELECT u.id AS user_id, u.email, u.name,
       ru.id AS unit_id, ru.job_field, ru.headcount,
       rs.id AS section_id, rs.recruitment_type, rs.education_level,
       rs.grade, rs.work_locations,
       p.id AS posting_id, p.title, p.application_end, p.source_url,
       i.name AS institution_name
FROM users u
CROSS JOIN recruitment_units ru
JOIN recruitment_sections rs ON ru.section_id = rs.id
JOIN job_postings p ON ru.posting_id = p.id
JOIN institutions i ON p.institution_id = i.id
WHERE u.is_active = 1
  AND p.status = 'active'
  AND p.id = ?  -- 신규 공고 ID
  AND JSON_CONTAINS(u.preferred_fields, JSON_QUOTE(ru.job_field))
  AND EXISTS (
    SELECT 1
    FROM JSON_TABLE(u.preferred_regions, '$[*]' COLUMNS(val VARCHAR(20) PATH '$')) ur
    JOIN JSON_TABLE(rs.work_locations, '$[*]' COLUMNS(val VARCHAR(20) PATH '$')) wl
      ON ur.val = wl.val
  );
```

**2단계: 자격 적부 체크 (Code 노드)**

```javascript
function checkQualification(user, qualification) {
  const checks = [];

  // 학력 체크
  const eduOrder = ["고졸", "전문대졸", "대졸", "석사이상"];
  if (qualification.education_req !== "제한 없음") {
    const reqIdx = eduOrder.indexOf(qualification.education_req);
    const userIdx = eduOrder.indexOf(user.education_level);
    checks.push({
      item: "학력",
      required: qualification.education_req,
      user_value: user.education_level,
      pass: userIdx >= reqIdx,
    });
  }

  // 병역 체크
  if (
    qualification.military_req &&
    qualification.military_req.includes("불이행자 제외")
  ) {
    checks.push({
      item: "병역",
      required: "이행 완료",
      user_value: user.military_status,
      pass: user.military_status !== "미필",
    });
  }

  // 장애인 채용 체크
  if (qualification.disability_req) {
    checks.push({
      item: "장애인 등록",
      required: "장애인 등록자",
      user_value: user.is_disabled ? "해당" : "비해당",
      pass: user.is_disabled === 1,
    });
  }

  // 보훈 채용 체크
  if (qualification.veteran_req) {
    checks.push({
      item: "취업지원대상자",
      required: "취업지원대상자",
      user_value: user.is_veteran_family ? "해당" : "비해당",
      pass: user.is_veteran_family === 1,
    });
  }

  return {
    all_pass: checks.every((c) => c.pass),
    checks,
  };
}
```

**3단계: 가점 분석 (Code 노드)**

```javascript
function calculateBonus(user, bonusPoints, selectionStages) {
  const results = [];

  for (const bp of bonusPoints) {
    let applies = false;
    let reason = "";

    if (bp.bonus_type === "등록장애인" && user.is_disabled) {
      applies = true;
      reason = "등록장애인 해당";
    }
    if (bp.bonus_type === "취업지원대상자" && user.is_veteran_family) {
      applies = true;
      reason = "취업지원대상자 해당";
    }
    // ... 기타 가점 유형

    if (applies) {
      results.push({
        type: bp.bonus_type,
        reason,
        document_effect: bp.document_effect,
        written_effect: bp.written_effect,
        interview_effect: bp.interview_effect,
      });
    }
  }

  // 서류 점수 계산 (토익 기반)
  const docStage = selectionStages.find((s) => s.stage_number === 1);
  if (docStage && docStage.sub_items) {
    const subItems =
      typeof docStage.sub_items === "string"
        ? JSON.parse(docStage.sub_items)
        : docStage.sub_items;
    const langItem = subItems.find((si) => si.name.includes("외국어"));
    if (langItem && user.toeic_score) {
      const langScore =
        Math.min(user.toeic_score / 850, 1) * langItem.max_score;
      results.push({
        type: "서류_외국어성적",
        score: Math.round(langScore * 10) / 10,
        max_score: langItem.max_score,
        detail: `토익 ${user.toeic_score}점 → ${Math.round(langScore * 10) / 10}/${langItem.max_score}점`,
      });
    }
  }

  return results;
}
```

### Step 3-2. n8n 워크플로우 3: 매칭 + 이메일 발송

```
[트리거] 워크플로우 1 완료 시 (또는 Execute Workflow 노드로 호출)
    ↓
[MySQL] 신규 active 공고 ID 목록 조회
    ↓
[Loop Over Items] 공고별 반복
    ↓
  ┌─ [MySQL] 1단계: 희망조건 매칭 쿼리 실행
  │      ↓
  │  [Code 노드] 2단계: 자격 적부 체크
  │      ↓
  │  [Code 노드] 3단계: 가점 분석
  │      ↓
  │  [Code 노드] 사용자별 결과 그룹핑
  │    - { user_email → [매칭결과1, 매칭결과2, ...] }
  │      ↓
  │  [Loop] 사용자별 이메일 생성
  │    ├─ [Code 노드] HTML 이메일 템플릿 렌더링 (Step 3-3)
  │    └─ [Gmail 노드] 이메일 발송
  └─ [다음 공고]
```

### Step 3-3. 이메일 HTML 템플릿 작성

```bash
docker cp ./email_template.html n8n:/home/node/.n8n/assets/email_template.html
```

**이메일 구조:**

```
┌─────────────────────────────────────────┐
│  📋 [기관명] 채용공고 분석 리포트        │
│  공고 제목: XXXX                         │
│  접수기간: YYYY-MM-DD ~ YYYY-MM-DD      │
├─────────────────────────────────────────┤
│                                         │
│  📌 AI 요약                             │
│  "200자 이내 핵심 요약"                  │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  🎯 매칭된 포지션                        │
│  ┌───────────────────────────────┐      │
│  │ 채용구분: 대졸-일반            │      │
│  │ 직무: 발전-전기 (21명)         │      │
│  │ 직급: 4직급(나)               │      │
│  │ 근무지: 부산, 하동, ...        │      │
│  └───────────────────────────────┘      │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  ✅ 자격 요건 체크                       │
│  학력: 제한 없음     ✅ 충족             │
│  병역: 이행 필요     ✅ 충족             │
│  어학: 제한 없음     ✅ 충족             │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  📊 서류 점수 예상 (대졸-일반 기준)      │
│  외국어: 토익 820점 → 48.2/50점         │
│  자격증 가점: 별첨 확인 필요             │
│  ──────────────────────                 │
│  예상 합계: 48.2 / 100점                │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  🏷️ 적용 가능 가점                      │
│  (해당 없음 또는 가점 항목 나열)         │
│                                         │
├─────────────────────────────────────────┤
│  [잡알리오 원문 보기]  [지원 바로가기]   │
└─────────────────────────────────────────┘
│  출처: 잡알리오(job.alio.go.kr)          │
│  프로필 수정: [수정 링크]                │
```

**확인 사항:**

- 테스트 데이터로 이메일 템플릿 렌더링 → 실제 이메일 발송
- 모바일/데스크톱 이메일 클라이언트에서 레이아웃 확인
- 링크 클릭 동작 확인 (잡알리오 원문, 지원 링크)

---

## Phase 4: 통합 테스트 + 배포

### Step 4-1. End-to-End 테스트 시나리오

**시나리오 1: 신규 사용자 등록**

```
1. Google Form 작성 제출
2. → Sheets에 기록 확인
3. → 수정 링크 이메일 수신 확인
4. → n8n 트리거로 MySQL 동기화 확인
5. → users 테이블 데이터 정합성 확인
```

**시나리오 2: 공고 수집 → 매칭 → 알림**

```
1. 워크플로우 1 수동 실행
2. → 잡알리오 공고 목록 크롤링 확인
3. → 신규 공고 PDF 다운로드 확인
4. → Gemini API JSON 추출 확인
5. → JSON 검증 통과 확인
6. → DB 10개 테이블 분산 저장 확인
7. → 워크플로우 3 트리거
8. → 매칭 쿼리 결과 확인 (테스트 사용자 기준)
9. → 자격 체크/가점 분석 결과 확인
10. → 이메일 수신 및 내용 확인
```

**시나리오 3: 에러 처리**

```
1. Gemini API 응답 실패 시 → 재시도 로직 확인
2. JSON 검증 실패 시 → status='review_needed' 확인
3. 매칭 결과 0건 시 → 이메일 미발송 확인
4. 접수 마감된 공고 → status='closed' 업데이트 확인
```

### Step 4-2. 에러 핸들링 및 재시도 정책

| 에러 상황                   | 처리 방법                                  |
| --------------------------- | ------------------------------------------ |
| 잡알리오 접속 실패          | 5분 후 재시도 (최대 3회)                   |
| PDF 다운로드 실패           | 해당 공고 스킵, 다음 실행 시 재시도        |
| Gemini API 429 (Rate Limit) | 60초 대기 후 재시도                        |
| Gemini API 응답 파싱 실패   | 1회 재시도 (temperature 0.05로 낮춰서)     |
| JSON 검증 실패              | status='review_needed'로 저장, 관리자 알림 |
| Gmail 발송 실패             | 5분 후 재시도 (최대 2회)                   |

**n8n Error Workflow 설정:**

- 각 워크플로우에 Error Trigger 연결
- 에러 발생 시 관리자(본인) 이메일로 알림

### Step 4-3. Schedule 설정 및 모니터링

**최종 스케줄:**

| 워크플로우         | 트리거                | 시간                       |
| ------------------ | --------------------- | -------------------------- |
| WF1: 공고 수집     | Schedule              | 매일 09:00, 18:00          |
| WF2: 사용자 동기화 | Google Sheets Trigger | 실시간 (폼 제출/수정 시)   |
| WF3: 매칭 + 알림   | WF1 완료 시 자동 호출 | WF1 직후                   |

**모니터링 체크리스트:**

- n8n 대시보드에서 워크플로우 실행 이력 확인 (매일)
- 에러 알림 이메일 확인
- Gemini API 사용량 확인 (월 1회)

---

## Phase 5: 운영 + 개선

### Step 5-1. 결제 관리 프로세스

```
1. 사용자가 계좌이체로 결제
2. 관리자가 Google Sheets "결제관리" 시트에 기록
   - 이메일, 결제일, 만료일, 결제상태(완료/만료)
3. n8n 주기적(매일) 만료 체크
   - 만료일 < 오늘 → is_active = 0
   - 결제상태=완료 AND 만료일 >= 오늘 → is_active = 1
```

### Step 5-2. 공고 마감 자동 처리

```
[Schedule Trigger] 매일 00:00
    ↓
[MySQL] UPDATE job_postings
  SET status = 'closed'
  WHERE status = 'active'
  AND application_end < CURDATE()
```

### Step 5-3. 향후 확장 로드맵

| 순서 | 항목             | 설명                                                |
| ---- | ---------------- | --------------------------------------------------- |
| 1    | 이메일 열람 추적 | 이메일 오픈율/클릭률 분석                           |
| 2    | 카카오 알림톡    | 사용자 증가 시 알림 채널 추가                       |
| 3    | 합격 스펙 데이터 | 합격자 스펙 공유 → 리워드 → 서류 합격률 예측        |
| 4    | 기관 급여 연동   | 알리오 공시 급여정보 자동 수집 → salary_info 테이블 |

---

## 체크리스트 요약

| Phase | 핵심 산출물              | 완료 기준                                          |
| ----- | ------------------------ | -------------------------------------------------- |
| 0     | MySQL DB + API 키        | n8n → MySQL 연결 성공, 10개 테이블, API 연결       |
| 1     | Google Form + 동기화     | 폼 제출 → Sheets → MySQL 자동 흐름                 |
| 2     | 공고 수집 파이프라인     | PDF → Gemini → JSON → DB 저장 자동화               |
| 3     | 매칭 + 이메일 알림       | 테스트 사용자에게 분석 리포트 이메일 수신           |
| 4     | E2E 테스트 + 배포        | 전체 플로우 무인 자동 실행 확인                     |
| 5     | 운영 안정화              | 결제 관리, 에러 모니터링 정상 운영                  |
