# alio-letter — 남은 할 일

---

## 🔜 Resend 도메인 인증 (실서비스 필수)

> 현재 `onboarding@resend.dev`로 발송 중 — Resend 계정 이메일로만 수신 가능, 실사용자 수신 불가.
> `alio-letter.pages.dev`는 Cloudflare 소유 서브도메인이라 DNS 레코드 추가 불가.
> **Cloudflare Registrar에서 도메인 구매 시 DNS 관리를 같은 대시보드에서 할 수 있어 편리.**

1. 도메인 구매 (Cloudflare Registrar 권장: https://dash.cloudflare.com → Domain Registration)
2. Resend 대시보드 → Domains → Add Domain → DNS 레코드 3개 발급
3. Cloudflare DNS 관리 페이지에서 레코드 3개 추가 → Resend에서 Verify
4. Pages Secret `RESEND_FROM` 변경 후 재배포

```bash
cd /home/pi/workspace/alio-letter/alio-letter-web
export CLOUDFLARE_API_TOKEN=...
export CLOUDFLARE_ACCOUNT_ID=...
echo "noreply@구매한도메인" | npx wrangler pages secret put RESEND_FROM --project-name alio-letter
npm run deploy
```

- [ ] 도메인 구매 완료
- [ ] Resend DNS 인증 완료
- [ ] RESEND_FROM Pages Secret 업데이트 및 재배포

---

## ⚠️ 운영 — 주기적 점검 항목

| 항목 | 주기 | 확인 방법 |
|------|------|-----------|
| Resend 발송량 | 월 1회 | https://resend.com/overview — 월 3,000건 무료 한도 확인 |
| cron 로그 | 주 1회 | `tail -50 pipeline/daily.log` — 에러 없는지 확인 |
| Cloudflare D1 용량 | 월 1회 | Cloudflare 대시보드 → D1 → Storage Used 확인 (무료 5GB) |
| Gemini API 사용량 | 월 1회 | https://aistudio.google.com → 사용량 확인 |
| 잡알리오 HTML 구조 변경 여부 | 월 1회 | `python main.py 1` 후 수집 건수 확인 |
