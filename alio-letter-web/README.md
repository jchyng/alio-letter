# Alio-Letter Web

잡알리오 채용공고 AI 맞춤 알림 서비스의 프론트엔드 + Cloudflare Functions 프로젝트.

## 기술 스택

- **프론트엔드**: 정적 HTML/CSS/JS (프레임워크 없음)
- **백엔드**: Cloudflare Functions (MySQL 직접 연결 + Gemini API)
- **호스팅**: Cloudflare Pages
- **보안연결**: Cloudflare Tunnel (라즈베리파이 DB 연결용)

## 디렉토리 구조

```
alio-letter-web/
├── src/                          # 정적 파일 (Cloudflare Pages에 배포됨)
│   ├── index.html                # 랜딩 페이지
│   ├── register.html             # 회원등록 폼
│   ├── profile.html              # 프로필 수정 폼 (/profile/:token)
│   └── style.css                 # 공통 CSS
├── functions/                    # Cloudflare Functions
│   └── api/
│       ├── register.js           # POST /api/register (Gemini 파싱 + DB 저장)
│       └── profile/
│           └── [token].js        # GET/POST /api/profile/:token
├── wrangler.toml                 # Cloudflare 설정 (DB 주소, API 키 등)
├── package.json
└── README.md
```

## 로컬 개발

### 1. 의존성 설치

```bash
cd alio-letter-web
npm install
```

### 2. 환경변수 설정

`wrangler.toml`에서 다음 변수들을 설정해야 합니다:

- `GEMINI_API_KEY`: Google AI Studio에서 발급받은 키
- `DB_HOST`: Cloudflare Tunnel로 연결된 DB 도메인
- `DB_USER`, `DB_PASSWORD`, `DB_NAME`: MySQL 접속 정보

### 3. 로컬 서버 실행

```bash
npm run dev
```

`http://localhost:8788`에서 확인 가능합니다.

## 배포

### 1. Cloudflare Tunnel 설정 (라즈베리파이)

라즈베리파이의 MySQL 포트를 Cloudflare Tunnel을 통해 외부(Cloudflare Worker)에서 접근 가능하도록 설정합니다.

```bash
cloudflared tunnel run <tunnel-name>
```

### 2. Cloudflare Pages 배포

```bash
npm run deploy
```

## API 엔드포인트

| 메서드 | 경로 | 역할 |
|--------|------|------|
| POST | `/api/register` | Gemini API로 스펙 파싱 → MySQL 저장 |
| GET | `/api/profile/:token` | MySQL에서 해당 토큰의 사용자 정보 조회 |
| POST | `/api/profile/:token` | 수정된 정보 Gemini 재파싱 → MySQL 업데이트 |

모든 비즈니스 로직은 Cloudflare Functions에서 직접 처리하며, 데이터는 Cloudflare Tunnel을 통해 집 안의 라즈베리파이 MySQL에 저장됩니다.
