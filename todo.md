# TODO

## 진행 중
- [ ] PDF 추출 스키마 확정 (직무, 자격요건, 급여 등 추출할 필드 정의)
- [ ] Gemini 프롬프트 구체화 + `analyze_posting()` 반환값 구조화

## 이후
- [ ] JSONL → DB 마이그레이션 (`store.py`의 TODO 참고)

---

## 새 대화 시작 프롬프트

```
공공기관 채용공고 수집·분석 파이프라인 프로젝트야 (pipeline/).

현재 구현 완료된 단계:
1. 공고 목록 수집 (scraper.fetch_all_postings / fetch_new_postings)
2. 상세 공고 수집 + 첨부파일 다운로드/HWP→PDF 변환 (scraper.fetch_detail_postings)
3. Gemini로 PDF 분석 후 raw/analyses/{idx}.json 저장 (analyzer.analyze_all_postings)
진입점: python pipeline/main.py

지금 할 일:
- pipeline/analyzer.py의 analyze_posting()에서 Gemini로 PDF를 분석할 때
  추출할 필드(스키마)가 아직 미확정 상태야 (TODO 주석 참고).
- 추출 스키마를 확정하고, 그에 맞게 Gemini 프롬프트와 반환값을 구조화해줘.

todo.md에 전체 할 일 목록 있어.
```
