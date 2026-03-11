## 기획 문서

1. 아이디어 핵심요약 ✅ => 아이디어_핵심요약.md
2. 잡알리오 데이터 이용 법적검토 ✅ => 잡알리오_데이터이용_법적검토.md
3. 핵심 로직 플로우 ✅ => 핵심로직_플로우.md
4. 구체적 구현 계획 (n8n + Google 생태계) ✅ => 구현계획_구체.md
5. DB 설계 (SQLite) ✅ => DB설계.md
6. LLM 추출 프롬프트 설계 ✅ => LLM추출_프롬프트설계.md
7. UI 설계 → 이메일 알림 설계로 대체 ✅ => UI설계.md

## 아키텍처 변경 이력

- v1: Supabase + Next.js + Edge Functions → 규모 과잉
- v2: Python Flask + SQLite + Oracle EC2 + PWA → 웹앱 개발 부담
- v3 (현재): **n8n (라즈베리파이) + Google Form/Sheets + SQLite + 이메일 알림** → 최소 구현

## 구현 단계 TODO

- [ ] Google Form 생성 (3섹션: 기본정보/스펙/희망조건)
- [ ] Apps Script 설정 (수정 링크 이메일 자동 발송)
- [ ] n8n 워크플로우 1: 공고 수집 파이프라인
- [ ] n8n 워크플로우 2: Google Sheets → SQLite 사용자 동기화
- [ ] n8n 워크플로우 3: 매칭 분석 + 이메일 발송
- [ ] SQLite DB 초기 스키마 생성
- [ ] Gemini API 연동 테스트 (PDF → JSON 추출)
- [ ] 이메일 템플릿 HTML 작성
