# LLM 추출 프롬프트 설계

## 개요

채용공고 PDF를 LLM에 넘겨서 구조화된 JSON으로 추출한다.
기관마다 PDF 포맷이 다르므로, **규칙 기반 파싱이 아닌 LLM 기반 추출**이 핵심.

> **역할 분리**: Gemini는 비구조화 문서 → 구조화 JSON 변환만 담당.
> `posting_url`, `file_urls`는 스크래퍼가 수집하여 DB에 먼저 저장한다.
> Gemini 출력에 이 두 필드는 포함하지 않는다.

---

## LLM 선택 기준

| 기준 | 요구사항 |
|------|---------|
| 컨텍스트 길이 | PDF 전체를 한 번에 넣을 수 있어야 함 (20~30페이지) |
| 한국어 성능 | 한국어 표/테이블 파싱 정확도 |
| JSON 출력 | structured output 지원 |
| 비용 | 공고 1건당 비용이 합리적 |
| 멀티모달 | PDF 이미지 직접 처리 가능하면 유리 |

**선택:** Gemini 2.5 Flash (100만 토큰 컨텍스트, 비용 효율)

---

## 출력 JSON 스키마

> DB 테이블 필드명과 1:1 매핑. 변환 레이어 없이 DB에 직접 저장 가능.

```json
{
  "postings_update": {
    "total_positions": 102,
    "positions_summary": [
      { "field": "사무", "total": 9, "by_track": { "일반": 8, "장애": 1 } },
      { "field": "전기", "total": 30, "by_track": { "일반": 21, "지역전문": 2, "장애": 2, "보훈": 1, "고졸": 4 } }
    ],
    "schedule": [
      { "step": "지원서접수", "start": "2026-03-03", "end": "2026-03-12", "note": "온라인 접수" },
      { "step": "필기전형", "date": "2026-04-05", "note": "서울 또는 부산" },
      { "step": "최종합격자발표", "date": "2026-05-15" }
    ]
  },

  "posting_tracks": [
    {
      "track_name": "대졸수준-일반",
      "grade": "4직급(나)",
      "total_positions": 79,
      "positions": [
        { "field": "사무", "count": 8 },
        { "field": "ICT", "count": 7 },
        { "field": "전기", "count": 21 }
      ],
      "work_locations": ["부산(본사)", "하동", "인천", "영월"],
      "work_type": "통상근무 또는 교대근무",

      "eligibility": {
        "age": "제한 없음 (만 60세 미만)",
        "education": "제한 없음",
        "language": "제한 없음",
        "certificate": "제한 없음",
        "military": "병역의무 불이행자 해당하지 않는 자. 현역의 경우 최종합격자 발표일 이전 전역 가능한 자",
        "special": null,
        "required_conditions": [],
        "preferred_conditions": []
      },

      "selection_process": [
        {
          "stage": 1,
          "name": "서류심사",
          "max_score": 100,
          "details": "외국어성적(50점) + 자격증 가점(최대 50점)",
          "pass_ratio": "30배수",
          "tiebreak": "동점자 전원 합격"
        },
        {
          "stage": 2,
          "name": "필기전형",
          "pass_ratio": "3배수",
          "sub_items": [
            { "name": "인성평가", "type": "적부판정", "details": "E·F등급 부적합" },
            { "name": "직무능력평가(K-JAT)", "max_score": 100 },
            { "name": "전공기초", "max_score": 100, "details": "지원분야별 상이" }
          ],
          "note": "가점 제외 합계 40% 미만 과락",
          "tiebreak": "동점자 전원 합격"
        },
        {
          "stage": 3,
          "name": "면접전형(NCS 기반 역량면접)",
          "max_score": 400,
          "pass_ratio": "2배수",
          "sub_items": [
            { "name": "Presentation", "max_score": 100 },
            { "name": "Group Discussion", "max_score": 100 },
            { "name": "실무역량·인성·조직적합성", "max_score": 200 }
          ],
          "note": "60% 미만 과락",
          "tiebreak": "보훈 > 장애 > 직무능력평가 > 인성평가 등급 > 전공기초 고득점순"
        },
        {
          "stage": 4,
          "name": "합격예정자 결정",
          "details": "필기+면접 합산 고득점순"
        },
        {
          "stage": 5,
          "name": "신체검사·비위면직자및신원조사",
          "type": "적부판정"
        }
      ],

      "scoring_criteria": {
        "language_score": {
          "max": 50,
          "formula": "(토익환산점수 ÷ 850) × 50",
          "cap_rule": "850점 이상 시 50점 만점",
          "accepted_tests": ["TOEIC", "TOEIC Speaking", "OPIc"],
          "validity_note": "공고 마감일 기준 유효기간 미만료 국내정기시험 성적만 인정"
        },
        "certificate_score": { "max": 50 }
      },

      "bonus_points": [
        {
          "type": "등록장애인",
          "definition": "장애인고용촉진및직업재활법에 의거 장애인 등록자",
          "document": "면제",
          "written": "배점의 10%",
          "interview": "배점의 10%"
        },
        {
          "type": "취업지원대상자",
          "definition": "국가유공자등예우및지원에관한법률 제31조 채용시험 가점 대상자",
          "document": "면제",
          "written": "관련 법령에 따름",
          "interview": "관련 법령에 따름"
        }
      ],

      "bonus_points_rule": "전형별 가산점은 10% 한도 내 중복 인정. 서류전형 면제 대상자는 합격예정인원 초과 추가합격 가능",

      "certificate_bonus_table": {
        "common": [
          { "category": "한국사", "score": 5, "types": ["한국사능력검정시험 3급 이상"] },
          { "category": "국어능력", "score": 5, "types": ["국어능력인증 3급", "KBS한국어능력 3+급", "한국실용글쓰기 준2급 이상"] },
          { "category": "IT능력", "score": 5, "types": ["정보처리기사", "정보처리산업기사", "사무자동화산업기사", "컴퓨터활용능력 1급(대한상공회의소)"], "note": "ICT 지원자는 IT자격증 가점 제외" },
          { "category": "외국어", "score": 5, "types": ["토익스피킹 AL등급(7등급)", "OPIc AL등급 이상"] }
        ],
        "by_field": {
          "전기": [
            { "grade": "기사", "score": 10, "types": ["전기", "전기공사", "소방설비(전기분야)", "산업안전"] },
            { "grade": "산업기사", "score": 5, "types": ["전자", "신재생에너지발전설비(태양광)"] }
          ],
          "기계": [
            { "grade": "기사", "score": 10, "types": ["일반기계", "에너지관리", "금속재료", "설비보전", "메카트로닉스", "기계설계", "산업안전", "소방설비(기계)", "공조냉동기계", "비파괴검사(전분야)", "용접", "건설기계설비", "건설기계정비", "신재생에너지발전설비(태양광)", "가스", "건설안전"] },
            { "grade": "산업기사", "score": 5, "types": ["일반기계", "에너지관리", "금속재료", "설비보전", "메카트로닉스", "기계설계", "산업안전", "소방설비(기계)", "공조냉동기계", "비파괴검사(전분야)", "용접", "건설기계설비", "건설기계정비", "신재생에너지발전설비(태양광)", "가스", "건설안전"] }
          ],
          "화학": [
            { "grade": "기사", "score": 10, "types": ["대기환경(대기관리)", "수질환경(수질관리)", "소음진동", "폐기물처리", "화공", "에너지관리", "온실가스관리", "신재생에너지발전설비(태양광)", "토양환경", "위험물", "산업안전", "화학분석", "가스", "환경위해관리"] },
            { "grade": "산업기사", "score": 5, "types": ["대기환경(대기관리)", "수질환경(수질관리)", "소음진동", "폐기물처리", "화공", "에너지관리", "온실가스관리", "신재생에너지발전설비(태양광)", "토양환경", "위험물", "산업안전", "화학분석", "가스", "환경위해관리"] }
          ],
          "토목": [
            { "grade": "기사", "score": 10, "types": ["토목", "건설재료시험", "측량 및 지형공간정보", "지적", "콘크리트", "건설안전"] },
            { "grade": "기사", "score": 8, "types": ["조경", "도시계획"] },
            { "grade": "산업기사", "score": 5, "types": ["토목", "건설재료시험", "측량 및 지형공간정보", "지적", "콘크리트", "건설안전"] },
            { "grade": "산업기사", "score": 3, "types": ["조경"] }
          ],
          "건축": [
            { "grade": "기사", "score": 10, "types": ["건축", "실내건축", "건축설비", "콘크리트", "건설안전"] },
            { "grade": "기사", "score": 8, "types": ["조경", "도시계획"] },
            { "grade": "산업기사", "score": 5, "types": ["건축", "실내건축", "건축설비", "콘크리트", "건설안전"] },
            { "grade": "산업기사", "score": 3, "types": ["조경"] }
          ],
          "ICT": [
            { "grade": "기사", "score": 10, "types": ["정보통신", "무선설비", "전자", "방송통신", "정보보안", "전자계산기", "전자계산기조직응용", "정보처리"] },
            { "grade": "산업기사(관리)", "score": 5, "types": [] }
          ]
        },
        "rules": {
          "max_certificates": 3,
          "same_type_rule": "동일종류 자격증은 상위등급 1개만 인정. 예: 전기기사+전기산업기사 보유 시 전기기사만 인정",
          "field_restriction": "직무 자격증은 해당 모집단위 분야 자격증에만 가점 부여. 예: 전기 지원자가 건축기사 보유 시 미부여",
          "ict_it_exclusion": "ICT 지원자는 공통 IT능력(IT자격증) 가점 제외"
        }
      },

      "language_conversion_table": {
        "toeic_speaking": [
          { "score": 200, "converted_toeic": 975 },
          { "score": 190, "converted_toeic": 955 }
        ],
        "opic": [
          { "grade": "AL", "converted_toeic": 965 },
          { "grade": "IH", "converted_toeic": 870 }
        ],
        "validity": "공고 마감일 기준 유효기간 미만료 성적만 인정"
      },

      "quota_policies": [
        {
          "name": "본사 이전지역인재 채용목표제",
          "target": "부산광역시 소재 학교 졸업자 또는 졸업예정자 (대학원 제외)",
          "rule": "전형별 30% 미달 시 고득점순 추가 선발"
        }
      ]
    }
  ],

  "validation": {
    "total_positions_check": 102,
    "tracks_sum": 102,
    "match": true
  }
}
```

---

## 시스템 프롬프트

```
당신은 공기업 채용공고 PDF에서 구조화된 데이터를 추출하는 전문가입니다.

아래 규칙을 반드시 따르세요:

[필수 규칙]

1. 모든 채용 트랙을 빠짐없이 추출하세요.
   대졸-일반, 대졸-지역전문, 대졸-장애, 대졸-보훈, 고졸, 별정직 등
   공고에 등장하는 모든 트랙을 각각 독립된 객체로 출력하세요.

2. 절대로 "동일", "위와 같음", "상동", "대졸수준-일반과 동일" 같은
   참조 표현을 사용하지 마세요.
   다른 트랙과 내용이 같더라도 반드시 실제 데이터를 그대로 복사하여 출력하세요.
   JSON 필드 값이 문자열 참조가 되어서는 안 됩니다.

3. "선발분야 및 인원" 피벗 테이블을 행 단위로 변환하세요.
   인원이 0이거나 빈칸인 셀은 제외하세요.
   모든 트랙의 total_positions 합계 == postings_update.total_positions 이어야 합니다.

4. 전형 단계별 세부사항을 정확히 추출하세요.
   배점, 배수, 산식, 동점자 처리 기준(tiebreak)이 있으면 모두 포함하세요.
   인성평가 같은 적부판정 항목도 sub_items에 포함하세요.

5. 가점 항목은 서류(document)/필기(written)/면접(interview) 각 단계별 효과를 구분하세요.
   가능한 값: "면제", "배점의 N%", "득점의 N%", "관련 법령에 따름", null
   각 항목의 자격 조건 원문(definition)도 함께 추출하세요.
   가점 중복 한도 규칙이 있으면 bonus_points_rule에 기록하세요.

6. certificate_bonus_table의 rules에 field_restriction(직무 자격증 교차 가점 제한 규칙)이
   명시되어 있으면 반드시 포함하세요.

7. scoring_criteria.language_score에 유효기간 조건이 있으면 validity_note에 기록하세요.

8. 날짜는 YYYY-MM-DD 형식으로 통일하세요.
   마감 시각이 있으면 YYYY-MM-DD HH:MM:SS 형식으로 기록하세요.

9. posting_url과 file_urls는 출력하지 마세요. (스크래퍼가 별도 수집)

10. 반드시 아래 JSON 스키마에 맞춰 출력하세요. JSON 외 다른 텍스트는 출력하지 마세요.
```

---

## 추출 후 검증 로직 (서버측)

```
1. JSON 파싱 성공 여부
2. postings_update 필수 필드 null 체크
3. posting_tracks 배열이 1개 이상인지
4. 각 트랙에 eligibility, selection_process 존재 여부
5. 모든 트랙 total_positions 합계 == postings_update.total_positions
6. bonus_points, certificate_bonus_table 필드가 문자열인 트랙 없는지 검사
   → "동일" 참조 문자열 감지 시 parse_status = 'failed' 처리
7. 합계 불일치 시 → parse_status = 'partial', 수동 검토 큐
8. 검증 통과 시 → DB 저장
```

---

---

## 자격증 점수 계산 (FLOW 3-2)

> 공고 파싱과 별도로, FLOW 3에서 사용자 자격증 점수를 계산할 때 호출하는 프롬프트.
> 코드 대신 AI를 사용하는 이유: 공고마다 자격증 표기가 다르고("전기" / "전기기사" / "전기(기사)"), 사용자 입력도 다양하여 정확한 문자열 매칭이 불가능하기 때문.

### 입력

```
[사용자 보유 자격증]
{user_certificates 목록 — cert_name, issue_date}

[지원 모집단위 분야]
{job_field — 예: "전기"}

[공고 자격증 가점 기준표]
{posting_tracks.certificate_bonus_table — JSON 전체}
```

### 출력 JSON 스키마

```json
{
  "matched_field_certs": [
    {
      "user_cert": "전기기사",
      "table_type": "전기",
      "grade": "기사",
      "score": 10,
      "reason": "전기 분야 기사급 자격증으로 by_field.전기에 해당"
    }
  ],
  "matched_common_certs": [
    {
      "user_cert": "한국사능력검정시험 1급",
      "category": "한국사",
      "score": 5,
      "reason": "3급 이상 해당"
    }
  ],
  "excluded_certs": [
    {
      "user_cert": "전기산업기사",
      "reason": "전기기사와 동일종류, 상위등급 1개만 인정"
    }
  ],
  "has_advanced_cert": true,
  "certificate_score": 15,
  "rules_applied": ["동일종류 상위등급 1개만 인정", "최대 3개 합산"]
}
```

> `has_advanced_cert`: 기사 이상 등급 자격증 보유 여부. FLOW 3-3 고급자격증 가점 판단에 직접 사용.

### 시스템 프롬프트

```
당신은 공기업 채용 서류전형의 자격증 가점을 계산하는 전문가입니다.

아래 규칙을 반드시 따르세요:

[필수 규칙]

1. 사용자 자격증 목록과 공고의 certificate_bonus_table을 비교하여 가점을 계산하세요.
   자격증명이 정확히 일치하지 않아도 동일한 자격증이면 인정하세요.
   예: "전기기사" = "전기 기사" = "전기(기사)" = "전기기사 (국가기술)"

2. by_field 매칭 시, 지원 모집단위 분야와 관련된 자격증에만 가점을 부여하세요.
   예: 전기 지원자가 건축기사를 보유해도 전기 분야 by_field에 없으면 by_field 가점 미부여.

3. common 항목은 분야 제한 없이 매칭하세요.

4. 동일종류 자격증(예: 전기기사 + 전기산업기사)은 상위등급 1개만 인정하고,
   나머지는 excluded_certs에 이유와 함께 기록하세요.

5. 최종 합산은 최대 3개까지만 인정하세요.
   4개 이상이면 점수 높은 순으로 3개 선택, 나머지는 excluded_certs에 기록하세요.

6. has_advanced_cert는 기사급 이상(기사, 기술사, 1급, 특급 등) 자격증을 1개 이상 보유하면 true.

7. 반드시 아래 JSON 스키마에 맞춰 출력하세요. JSON 외 다른 텍스트는 출력하지 마세요.
```

---

## 비용 추정 (Gemini 2.5 Flash 기준)

- 공고 PDF 평균 20페이지 ≈ 약 8,000~15,000 토큰 (입력)
- JSON 출력 ≈ 약 3,000~5,000 토큰
- 1건당 비용: 약 $0.003~0.008
- 월 100건 공고 처리 시: 약 $0.3~0.8
