# alio-letter — 배포 체크리스트

> 이 문서만 보고 처음부터 끝까지 배포 가능하도록 작성됨.
> 완료한 항목은 `- [x]`로 표시할 것.

---

## 0. 전제조건 확인

```bash
node -v        # 18 이상 필요
npm -v
python3 --version  # 3.10 이상 필요
libreoffice --version  # HWP 변환에 필요
```

LibreOffice 없으면:
```bash
sudo apt install libreoffice libreoffice-h2orestart
sudo apt install fonts-nanum fonts-nanum-extra fonts-unfonts-core fonts-baekmuk
fc-cache -fv
```

- [x] 전제조건 확인 완료

---

## 1. Resend 계정 + API 키 발급

### 1-1. 회원가입 & API 키

1. https://resend.com 접속 → Sign Up
2. 이메일 인증 완료 후 대시보드 진입
3. 좌측 메뉴 **API Keys** → **Create API Key**
   - Name: `alio-letter`
   - Permission: `Sending access`
   - Domain: `All domains`
4. 발급된 키 (`re_` 로 시작) 복사 → 잃어버리면 재발급 필요

- [ ] API 키 발급 완료

### 1-2. 발신 도메인 인증 (선택 — 없으면 개발 테스트만 가능)

> 도메인 없이는 `onboarding@resend.dev`로만 발송 가능 (Resend 가이드 페이지에서 확인한 이메일로만 수신됨).
> 실서비스를 위해서는 본인 소유 도메인 필요.

1. 도메인 구매 (예: `alio-letter.com`) — 가비아, 후이즈 등
2. Resend 대시보드 → **Domains** → **Add Domain**
3. 도메인 입력 후 DNS 레코드 3개 발급됨 (MX, TXT x2)
4. 도메인 DNS 관리 페이지에서 레코드 3개 추가
5. Resend에서 **Verify** → 상태가 `Verified`로 바뀔 때까지 대기 (최대 48시간, 보통 수분)

- [ ] 도메인 인증 완료 (또는 개발 테스트로 진행 결정)

### 1-3. 무료 플랜 한도 확인 (주기적 확인 필요 → [운영 점검 항목](#-운영-주기적-점검-항목) 참고)

- 무료 플랜: **일 100건, 월 3,000건**
- 초과 시 유료 플랜 필요 (https://resend.com/pricing)

---

## 2. Python 파이프라인 환경 설정

### 2-1. 가상환경 + 의존성 설치

```bash
cd /home/pi/workspace/alio-letter/pipeline
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> 이후 `python daily.py` 실행 시에도 반드시 venv 활성화 필요.
> crontab에서는 절대경로로 venv python을 지정해야 함 (아래 6번 참고).

- [ ] 의존성 설치 완료

### 2-2. .env 파일 생성

```bash
cat > /home/pi/workspace/alio-letter/pipeline/.env << 'EOF'
GEMINI_API_KEY=여기에_Gemini_API_키_입력
RESEND_API_KEY=여기에_Resend_API_키_입력
RESEND_FROM=noreply@YOUR_DOMAIN
CF_ACCOUNT_ID=여기에_Cloudflare_계정_ID_입력
CF_D1_DATABASE_ID=여기에_D1_데이터베이스_ID_입력
CF_API_TOKEN=여기에_D1_edit_권한_API_토큰_입력
EOF
```

> `RESEND_FROM`: 도메인 인증 완료 전이면 `onboarding@resend.dev` 로 테스트 가능.
> Gemini API 키: https://aistudio.google.com/app/apikey
> `CF_ACCOUNT_ID`: Cloudflare 대시보드 우측 사이드바 → 계정 ID
> `CF_D1_DATABASE_ID`: 3-2번 단계에서 D1 생성 후 출력되는 database_id
> `CF_API_TOKEN`: Cloudflare 대시보드 → My Profile → API Tokens → Create Token → D1 Edit 권한 포함

- [x] .env 작성 완료

### 2-3. 로컬 DB 초기화 확인

```bash
cd /home/pi/workspace/alio-letter/pipeline
source venv/bin/activate
python -c "import db; db.init_db(); print('DB OK')"
```

- [x] DB 초기화 확인

---

## 3. Cloudflare 설정

> ⚠️ 라즈베리파이 CLI 환경 주의: `wrangler login`은 브라우저 OAuth 콜백이 필요해 동작 안 함.
> API 토큰 방식으로 대체한다. 터미널 세션마다 아래 환경변수를 먼저 설정해야 함.

### 3-0. 사전 준비 (PC 브라우저에서)

**API 토큰 생성**

1. https://dash.cloudflare.com/profile/api-tokens → **Create Token**
2. **Custom token** 선택 후 권한 추가:
   - `Account > D1 > Edit`
   - `Account > Cloudflare Pages > Edit`
3. Account Resources: 본인 계정 선택 → **Create Token** → 토큰 값 복사

**Account ID 확인**

- https://dash.cloudflare.com 접속 → 우측 사이드바 → **Account ID** 복사

### 3-1. wrangler 설치 & 인증 설정

```bash
cd /home/pi/workspace/alio-letter/alio-letter-web
npm install

# 터미널 세션마다 실행 (재부팅·터미널 재시작 시 다시 입력 필요)
export CLOUDFLARE_API_TOKEN=여기에_API_토큰
export CLOUDFLARE_ACCOUNT_ID=여기에_ACCOUNT_ID

# 인증 확인
npx wrangler whoami
# "You are logged in with an User API Token" 메시지 확인
```

- [x] wrangler 인증 완료

### 3-2. D1 데이터베이스 생성

```bash
# 환경변수가 설정된 상태에서 실행
npx wrangler d1 create alio-letter
```

출력 예시:
```
✅ Successfully created DB 'alio-letter'

[[d1_databases]]
binding = "DB"
database_name = "alio-letter"
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

**→ `database_id` 값을 복사한다.**

- [x] D1 생성 완료

### 3-3. wrangler.toml 및 .env에 ID 입력

파일: `alio-letter-web/wrangler.toml`

```toml
[[d1_databases]]
binding = "DB"
database_name = "alio-letter"
database_id = "여기에_위에서_복사한_ID_입력"
```

파일: `pipeline/.env` (파이프라인이 D1에 직접 접근하는 데 사용)

```
CF_ACCOUNT_ID=위에서_확인한_ACCOUNT_ID
CF_D1_DATABASE_ID=위에서_복사한_database_id
CF_API_TOKEN=위에서_생성한_API_토큰
```

- [x] wrangler.toml 수정 완료
- [x] pipeline/.env CF 항목 입력 완료

### 3-4. D1에 테이블 초기화

```bash
cd /home/pi/workspace/alio-letter/alio-letter-web
npx wrangler d1 execute alio-letter --file=schema.sql --remote
```

확인:
```bash
npx wrangler d1 execute alio-letter --command="SELECT name FROM sqlite_master WHERE type='table'" --remote
# postings, posting_tracks, users, user_judgments 4개 나와야 함
```

- [x] 테이블 초기화 확인

### 3-5. Cloudflare Pages Secret 등록

> CF Functions(register.js 등)에서 사용하는 API 키.
> Pages 프로젝트가 먼저 존재해야 하므로 4번(배포) 이후에 진행 가능.
> 배포 전 선등록하려면 대시보드에서 직접 추가.

```bash
cd /home/pi/workspace/alio-letter/alio-letter-web
npx wrangler pages secret put GEMINI_API_KEY
# 프롬프트에 키 값 입력

npx wrangler pages secret put RESEND_API_KEY
# 프롬프트에 키 값 입력

npx wrangler pages secret put RESEND_FROM
# 프롬프트에 발신 주소 입력 (도메인 전: onboarding@resend.dev)
```

또는 대시보드: Workers & Pages → `alio-letter` → Settings → Environment variables

- [x] 환경변수 등록 완료

---

## 4. Cloudflare Pages 배포

```bash
cd /home/pi/workspace/alio-letter/alio-letter-web
npm run deploy
# = npx wrangler pages deploy src/
```

처음 배포 시 프로젝트 이름 입력 프롬프트가 뜨면: `alio-letter` 입력

배포 완료 후:
- [x] https://alio-letter.pages.dev 접속 → 랜딩 페이지 표시 확인
- [x] https://alio-letter.pages.dev/register 접속 → 회원가입 폼 확인

---

## 5. 파이프라인 수동 테스트

배포 전 파이프라인이 정상 동작하는지 먼저 확인.

```bash
cd /home/pi/workspace/alio-letter/pipeline
source venv/bin/activate

# 수집 건너뛰고 이메일 발송만 테스트
python daily.py --skip-scrape
# 예상 출력:
#   [daily] --skip-scrape: 수집 단계 건너뜀
#   [daily] 등록된 사용자 없음 — 종료
```

Resend API 키 입력 후 실제 이메일 발송 테스트:
```bash
# DB에 테스트 사용자 추가 후 실행
python -c "
import db, json
db.init_db()
db.save_user('test@example.com', '테스트', '경력 3년', None, None, 'test-token-123')
print('테스트 사용자 등록 완료')
"
python daily.py --skip-scrape
# [mailer] 발송 완료: test@example.com 가 출력되면 성공
```

- [x] 수동 테스트 완료

---

## 6. crontab 등록

> **주의**: crontab에서는 venv의 절대경로 python을 사용해야 함.
>
> **스케줄 설계**
> - 08:00 — 수집 + 분석 (`--skip-mail`): 공고 크롤링 및 Gemini 분석
> - 09:00 — 발송 (`--skip-scrape`): 판정 결과 이메일 발송
> - 분리한 이유: 분석 소요 시간이 가변적이라 발송 시각을 고정하기 위함

```bash
crontab -e
```

아래 내용 추가:

```cron
# alio-letter — 수집+분석 (매일 08시)
0 8 * * * /home/pi/workspace/alio-letter/pipeline/venv/bin/python /home/pi/workspace/alio-letter/pipeline/daily.py --skip-mail >> /home/pi/workspace/alio-letter/pipeline/daily.log 2>&1

# alio-letter — 이메일 발송 (매일 09시)
0 9 * * * /home/pi/workspace/alio-letter/pipeline/venv/bin/python /home/pi/workspace/alio-letter/pipeline/daily.py --skip-scrape >> /home/pi/workspace/alio-letter/pipeline/daily.log 2>&1
```

등록 확인:
```bash
crontab -l | grep alio-letter
```

- [x] crontab 등록 완료

---

## 7. E2E 테스트 (전체 흐름)

> ⚠️ `RESEND_FROM` 이슈: 도메인 인증 전에는 `onboarding@resend.dev`만 사용 가능하며,
> 이 경우 **Resend 가입 이메일 주소로만** 수신 가능. Pages Secret 확인 필요.

1. https://alio-letter.pages.dev/register → 이름·이메일·스펙·조건 입력 → 등록
   - [ ] 가입 확인 이메일 수신 확인

2. https://alio-letter.pages.dev/login → 이메일 입력 → 매직링크 발송
   - [ ] 매직링크 이메일 수신 → 링크 클릭 → 마이페이지 접속 확인

3. 파이프라인 직접 실행:
   ```bash
   cd /home/pi/workspace/alio-letter/pipeline
   source venv/bin/activate
   python daily.py
   ```
   - [ ] 공고 수집 → 분석 → 이메일 발송 전체 흐름 확인

4. cron 첫 실행 후 로그 확인:
   ```bash
   tail -f /home/pi/workspace/alio-letter/pipeline/daily.log
   ```
   - [ ] 오류 없이 완료 확인

### 이메일 수신 안 될 때 체크리스트

```bash
# 1. Pages Secret 목록 확인
npx wrangler pages secret list --project-name alio-letter

# 2. RESEND_FROM을 onboarding@resend.dev 로 업데이트
echo "onboarding@resend.dev" | npx wrangler pages secret put RESEND_FROM --project-name alio-letter

# 3. 기존 사용자로 재가입 시 이메일 미발송 → DB에서 삭제 후 재테스트
npx wrangler d1 execute alio-letter --command="DELETE FROM users WHERE email='이메일주소'" --remote

# 4. 재배포
npm run deploy
```

---

## 🔜 향후 개선 과제

### A. Resend 도메인 인증 (실서비스 필수)
> 현재 `onboarding@resend.dev`로 발송 중 — Resend 계정 이메일로만 수신 가능, 실사용자 수신 불가.
> `alio-letter.pages.dev`는 Cloudflare 소유 서브도메인이라 DNS 레코드 추가 불가 → 사용 불가.
> **Cloudflare Registrar에서 도메인을 구매하면 DNS 관리가 같은 대시보드에서 가능해 편리하다.**

1. 도메인 구매 (Cloudflare Registrar 권장: https://dash.cloudflare.com → Domain Registration)
2. Resend 대시보드 → Domains → Add Domain → DNS 레코드 3개 발급
3. Cloudflare DNS 관리 페이지에서 레코드 3개 추가 → Resend에서 Verify
4. Pages Secret `RESEND_FROM` 변경: `noreply@구매한도메인`

```bash
echo "noreply@구매한도메인" | npx wrangler pages secret put RESEND_FROM --project-name alio-letter
npm run deploy
```

- [ ] 도메인 구매 완료
- [ ] Resend DNS 인증 완료
- [ ] RESEND_FROM Pages Secret 업데이트 및 재배포

### B. 이메일 템플릿 개선 (UX)
> 완료 (2026-03-18)

- [x] 환영 이메일 (`register.js`): 서비스 소개, CTA, 브랜딩 적용
- [x] 매직링크 이메일 (`send-magic-link.js`): 보안 안내, 브랜딩 적용
- [x] 매칭 이메일 (`mailer.py`): 공고 카드 디자인, 가산점 3분류(적용/확인필요/준비가능), CTA

---

## ⚠️ 운영 — 주기적 점검 항목

> 배포 후에도 주기적으로 확인해야 할 것들.
> 자세한 내용은 [docs/08_운영_점검가이드.md](./docs/08_운영_점검가이드.md) 참고.

| 항목 | 주기 | 확인 방법 |
|------|------|-----------|
| Resend 발송량 | 월 1회 | https://resend.com/overview — 월 3,000건 무료 한도 확인 |
| cron 로그 | 주 1회 | `tail -50 pipeline/daily.log` — 에러 없는지 확인 |
| Cloudflare D1 용량 | 월 1회 | Cloudflare 대시보드 → D1 → Storage Used 확인 (무료 5GB) |
| Gemini API 사용량 | 월 1회 | https://aistudio.google.com → 사용량 확인 |
| 파이프라인 공고 수집 정상 여부 | 주 1회 | `python -c "import db; print(db.load_all()[:1])"` |
| 잡알리오 HTML 구조 변경 여부 | 월 1회 | `python main.py 1` 후 수집 건수 확인 |
