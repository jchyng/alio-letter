# LLM 추출 프롬프트 설계

## 개요

채용공고 PDF를 LLM에 넘겨서 구조화된 JSON으로 추출한다.
기관마다 PDF 포맷이 다르므로, **규칙 기반 파싱이 아닌 LLM 기반 추출**이 핵심.

---

## LLM 선택 기준

| 기준 | 요구사항 |
|------|---------|
| 컨텍스트 길이 | PDF 전체를 한 번에 넣을 수 있어야 함 (20~30페이지) |
| 한국어 성능 | 한국어 표/테이블 파싱 정확도 |
| JSON 출력 | structured output 지원 |
| 비용 | 공고 1건당 비용이 합리적 |
| 멀티모달 | PDF 이미지 직접 처리 가능하면 유리 |

**후보:** Gemini 2.5 Pro (100만 토큰 컨텍스트), Claude Sonnet/Opus, GPT-4o

---

## 추출 JSON 스키마

LLM에게 아래 스키마에 맞춰 JSON을 출력하라고 지시한다.

```json
{
  "posting_meta": {
    "institution_name": "한국남부발전(주)",
    "posting_number": "채용공고 2026-01호",
    "title": "2026년 상반기 신입사원 및 별정직 채용공고",
    "posted_date": "2026-02-23",
    "application_start": "2026-03-01",
    "application_end": "2026-03-12",
    "total_headcount": 102
  },

  "sections": [
    {
      "section_name": "신입사원 (대졸수준-일반)",
      "recruitment_type": "일반",
      "education_level": "대졸수준",
      "grade": "4직급(나)",
      "probation_months": 3,
      "work_locations": ["부산", "하동", "인천", "제주", "영월", "안동", "삼척", "세종"],
      "work_type": "통상근무 혹은 교대근무",

      "units": [
        {"job_field": "사무", "headcount": 8},
        {"job_field": "ICT", "headcount": 7},
        {"job_field": "발전-기계", "headcount": 25},
        {"job_field": "발전-전기", "headcount": 21},
        {"job_field": "화학", "headcount": 7},
        {"job_field": "토목", "headcount": 4},
        {"job_field": "건축", "headcount": 7}
      ],

      "qualifications": {
        "age_limit": "제한 없음 (정년 만60세)",
        "education_req": "제한 없음",
        "certificate_req": "제한 없음",
        "language_req": "제한 없음",
        "military_req": "병역의무 불이행자 제외",
        "disability_req": null,
        "veteran_req": null,
        "other_req": null,
        "preferred_certs": null
      },

      "selection_stages": [
        {
          "stage_number": 1,
          "stage_name": "서류심사",
          "pass_ratio": "30배수",
          "max_score": 100,
          "details": "외국어성적(50점) + 자격증가점(최대 50점)",
          "sub_items": [
            {"name": "외국어성적", "max_score": 50, "formula": "(토익환산점수÷850)×50, 850이상 만점"},
            {"name": "자격증가점", "max_score": 50, "note": "별첨 6 참고"}
          ]
        },
        {
          "stage_number": 2,
          "stage_name": "필기전형(기초지식평가)",
          "pass_ratio": "3배수",
          "max_score": 200,
          "details": "인성평가(적부) + 직무능력(100) + 전공기초(100)",
          "sub_items": [
            {"name": "인성평가", "max_score": null, "note": "E,F등급 부적합 (적부판정)"},
            {"name": "직무능력평가(K-JAT)", "max_score": 100, "note": "직무수행+직업기초능력"},
            {"name": "전공기초-사무(상경)", "max_score": 100, "note": "경제학,회계학,경영학 50문항"},
            {"name": "전공기초-기술", "max_score": 100, "note": "지원분야 기사 수준 50문항"}
          ]
        },
        {
          "stage_number": 3,
          "stage_name": "면접전형(NCS기반 역량면접)",
          "pass_ratio": "2배수",
          "max_score": 400,
          "details": "Presentation(100)+GD(100)+인성·조직적합성(200)",
          "sub_items": [
            {"name": "Presentation", "max_score": 100},
            {"name": "Group Discussion", "max_score": 100},
            {"name": "인성 및 조직적합성", "max_score": 200}
          ]
        },
        {
          "stage_number": 4,
          "stage_name": "합격예정자 결정",
          "pass_ratio": "1배수",
          "max_score": null,
          "details": "필기+면접 합산 고득점순",
          "sub_items": null
        },
        {
          "stage_number": 5,
          "stage_name": "신체검사, 비위면직자 및 신원조사",
          "pass_ratio": "최종합격",
          "max_score": null,
          "details": "적부판정",
          "sub_items": null
        }
      ]
    },
    {
      "section_name": "신입사원 (대졸수준-장애)",
      "recruitment_type": "장애",
      "education_level": "대졸수준",
      "...": "구조 동일, 내용만 다름 (서류면제 등)"
    }
  ],

  "bonus_points": [
    {
      "bonus_type": "등록장애인",
      "description": "장애인고용촉진 및 직업재활법에 의한 장애인 등록자",
      "document_effect": "면제",
      "written_effect": "배점의 10%",
      "interview_effect": "배점의 10%",
      "max_cumulative_pct": 10,
      "required_docs": "장애인 증빙서류"
    },
    {
      "bonus_type": "취업지원대상자",
      "description": "국가유공자 등 예우 및 지원에 관한 법률 제31조",
      "document_effect": "면제",
      "written_effect": "관련법령에 따름",
      "interview_effect": "관련법령에 따름",
      "max_cumulative_pct": 10,
      "required_docs": "취업지원대상자 증빙서류"
    }
  ],

  "recruitment_targets": [
    {
      "target_type": "이전지역인재",
      "description": "부산광역시 소재 학교 졸업자 또는 졸업예정자",
      "target_rate_pct": 30,
      "applicable_fields": ["사무", "ICT", "발전-기계", "발전-전기", "화학", "토목", "건축"],
      "conditions": "분야별 연 채용모집인원 6인 이상"
    }
  ],

  "validation": {
    "total_headcount_check": 102,
    "units_sum": 102,
    "match": true
  }
}
```

---

## 시스템 프롬프트

```
당신은 공기업 채용공고 PDF에서 구조화된 데이터를 추출하는 전문가입니다.

아래 규칙을 정확히 따르세요:

1. PDF에 포함된 모든 채용구분 섹션을 빠짐없이 추출하세요.
   - 대졸-일반, 대졸-장애, 대졸-보훈, 고졸, 별정직 등 모든 섹션
   - 각 섹션의 지원자격, 전형방법은 서로 다를 수 있으므로 각각 추출

2. "선발분야 및 인원" 피벗 테이블을 행 단위로 변환하세요.
   - 인원이 0이거나 빈칸인 셀은 제외
   - 모든 행의 headcount 합계가 총 채용인원과 일치해야 합니다

3. 전형 단계별 세부사항을 정확히 추출하세요.
   - 배점, 배수, 산식(formula)이 있으면 포함
   - 인성평가 같은 적부판정 항목도 포함

4. 가점 항목은 서류/필기/면접 각 단계별 효과를 구분하세요.
   - "면제", "배점의 N%", "관련법령에 따름", null 중 하나

5. 날짜는 YYYY-MM-DD 형식으로 통일하세요.

6. 추출 결과를 검증하세요:
   - units의 headcount 합계 == total_headcount
   - 각 section에 최소 1개 이상의 selection_stage 존재

반드시 아래 JSON 스키마에 맞춰 출력하세요. 다른 텍스트 없이 JSON만 출력하세요.
```

---

## 추출 후 검증 로직 (서버측)

```
1. JSON 파싱 성공 여부
2. posting_meta 필수 필드 null 체크
3. sections 배열이 1개 이상인지
4. 각 section에 units, qualifications, selection_stages 존재 여부
5. 전체 units headcount 합계 == total_headcount
6. 합계 불일치 시 → 수동 검토 큐에 넣기
7. 검증 통과 시 → DB 분산 저장
```

---

## 비용 추정 (Gemini 2.5 Pro 기준)

- 공고 PDF 평균 20페이지 ≈ 약 8,000~15,000 토큰 (입력)
- JSON 출력 ≈ 약 3,000~5,000 토큰
- 1건당 비용: 약 $0.01~0.03
- 월 100건 공고 처리 시: 약 $1~3
