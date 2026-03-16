# alio-letter — 내가 할 일

## 1. Resend 계정 설정

- [ ] resend.com 회원가입 + API 키 발급
- [ ] `pipeline/.env` 파일 생성 후 아래 추가:
  ```
  RESEND_API_KEY=re_xxx
  RESEND_FROM=noreply@YOUR_DOMAIN
  GEMINI_API_KEY=xxx
  ```
- [ ] (선택) 도메인 구매 + Resend DNS 인증
      → 없으면 `onboarding@resend.dev`로 개발 테스트만 가능

---

## 2. Cloudflare D1 설정

- [ ] Cloudflare 대시보드 → Workers & Pages → D1 → 데이터베이스 생성 (이름: `alio-letter-db`)
- [ ] 생성된 `database_id`를 `alio-letter-web/wrangler.toml`에 입력
- [ ] 테이블 초기화:
  ```bash
  cd alio-letter-web
  npx wrangler d1 execute alio-letter-db --file=schema.sql
  ```

---

## 3. Cloudflare 환경변수 (Secret) 등록

Cloudflare 대시보드 → Workers & Pages → 프로젝트 → Settings → Environment Variables

- [ ] `GEMINI_API_KEY`
- [ ] `RESEND_API_KEY`
- [ ] `RESEND_FROM`

---

## 4. Cloudflare Pages 배포

```bash
cd alio-letter-web
npx wrangler pages deploy src/
```

- [ ] 배포 완료 후 `https://alio-letter.pages.dev` 접속 확인

---

## 5. crontab 등록

```bash
crontab -e
```

아래 줄 추가:

```
# alio-letter 데일리 파이프라인 (매일 오전 6시)
0 6 * * * cd /home/pi/workspace/alio-letter/pipeline && python daily.py >> /home/pi/workspace/alio-letter/pipeline/daily.log 2>&1
```

- [ ] 등록 완료

---

## 6. E2E 테스트

- [ ] `https://alio-letter.pages.dev/register` → 회원가입 → 확인 이메일 수신 확인
- [ ] `cd pipeline && python daily.py --skip-scrape` → 이메일 발송 확인
- [ ] cron 첫 실행 후 `tail -f pipeline/daily.log` 로 결과 확인
