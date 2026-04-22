# 배당 대시보드

보유 수량만 입력하면 현재 포트폴리오 비중, 예상 배당, 실제 수령 배당, 월별 추이, 실시간 배당 카운터를 볼 수 있는 개인용 배당 대시보드 웹앱입니다.

핵심 원칙은 두 가지입니다.

- 실제 배당과 예상 배당을 완전히 분리한다.
- 모든 금액 표시는 반드시 `60,000원` 형식으로 통일한다.

## 프로젝트 소개

- 단일 사용자용 앱이라 로그인 / 회원가입 기능을 넣지 않았습니다.
- 데이터 저장은 Supabase PostgreSQL을 사용합니다.
- 배포는 Vercel을 전제로 설계했습니다.
- 보유 수량은 `numeric(24,8)`와 `decimal.js`를 사용해 소수점 정밀도를 유지합니다.
- 실제 배당은 원화 기준, 세전 금액으로 직접 입력합니다.
- 예상 배당은 `dividend_assumptions` 테이블의 종목별 기준값으로 계산합니다.
- 과거 실제 배당 대상 수량을 현재 보유 수량으로 역산하지 않습니다.

## 기술 스택

- Next.js 16 App Router
- TypeScript
- Tailwind CSS
- shadcn/ui 스타일 컴포넌트
- Recharts
- Framer Motion
- TanStack Query
- Supabase
- PostgreSQL
- decimal.js

## 왜 로그인 기능을 제외했는가

이번 버전은 나 혼자 쓰는 개인용 배당 앱이기 때문에, 복잡한 인증 흐름보다 빠른 입력과 계산 명확성이 더 중요합니다.

- `/login`, `/signup` 페이지가 없습니다.
- Supabase Auth를 사용하지 않습니다.
- 사용자별 계정 분리와 RLS 강제를 넣지 않았습니다.

다만 코드 구조는 `lib/supabase`, `lib/queries`, `lib/calculations`로 나눠 두어서 이후 인증을 붙이기 쉽도록 설계했습니다.

## 실행 방법

```bash
npm install
npm run dev
```

브라우저에서 [http://localhost:3000](http://localhost:3000) 를 열면 됩니다.

## 필요한 환경변수

`.env.local` 파일을 만들고 아래 값을 채워 넣습니다.

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

예시는 [.env.example](/Users/juna/codex_juna/dividend%20investment/.env.example) 에 들어 있습니다.

## Supabase 설정 방법

1. Supabase 프로젝트를 생성합니다.
2. SQL Editor 또는 Supabase CLI로 [supabase/migrations/20260422_000001_init.sql](/Users/juna/codex_juna/dividend%20investment/supabase/migrations/20260422_000001_init.sql) 을 실행합니다.
3. 이어서 [supabase/seed.sql](/Users/juna/codex_juna/dividend%20investment/supabase/seed.sql) 을 실행합니다.
4. 프로젝트 URL과 anon key를 `.env.local`에 입력합니다.

Supabase CLI를 쓰는 경우 예시는 아래와 같습니다.

```bash
supabase db push
psql "$SUPABASE_DB_URL" -f supabase/seed.sql
```

## DB schema 설명

### assets

고정 종목 마스터 테이블입니다.

- `market`: `US | KR`
- `asset_type`: `core | income | satellite | hedge`
- `dividend_frequency`: `weekly | monthly | quarterly | none`

### holdings

사용자가 직접 수정하는 핵심 테이블입니다.

- `shares numeric(24,8)`
- `asset_id unique`
- 소수점 투자 지원

### actual_dividends

실제 수령 배당 기록입니다.

- `gross_amount_krw numeric(24,2)`
- 원화 기준
- 세전 금액

### dividend_assumptions

예상 배당 계산 엔진용 기준값 테이블입니다.

- `assumption_type`
  - `annual_per_share`
  - `monthly_per_share`
  - `weekly_per_share`
  - `none`
- `annual_dividend_per_share`
- `monthly_dividend_per_share`
- `weekly_dividend_per_share`
- `source_note`
- `updated_at`
- `is_active`

실제 배당 입력과 완전히 분리되어 있으며, 화면에서 수정 가능합니다.

## 실제 배당과 예상 배당의 계산 분리

- 실제 배당
  - 사용자가 직접 입력한 원화 기준 세전 금액을 정답으로 사용합니다.
  - 각 배당 건의 ex-date 기준 보유 수량을 현재 수량으로 복원하려고 하지 않습니다.
- 예상 배당
  - 현재 보유 수량과 `dividend_assumptions`를 사용합니다.
  - projection에서는 현재 보유 수량 + 투자 규칙으로 미래 보유 수량을 추정해 계산합니다.
  - 과거 실제 배당 기록을 이용해 과거 보유 수량을 역산하지 않습니다.

### investment_rules

반복 투자 규칙입니다.

- `daily | weekly | monthly`
- 금액 기준 또는 주수 기준 입력 가능

### goals

배당 목표 금액을 저장합니다.

### app_settings

환율, 세금 모드, 카운터 애니메이션 여부를 저장합니다.

## seed 실행 방법

[supabase/seed.sql](/Users/juna/codex_juna/dividend%20investment/supabase/seed.sql) 에 아래가 포함됩니다.

- 고정 종목 11개
- 보유 수량 0주 기본 row
- `dividend_assumptions` 초기 기준값
- 기본 목표
- 기본 투자 규칙
- 샘플 실제 배당 기록
- 기본 앱 설정

## 예상 배당 계산 규칙

예상 배당은 배당률 `%`가 아니라 `dividend_assumptions`의 종목별 per-share 기준값으로 계산합니다.

- `VOO`, `QQQ`, `SCHD`, `SOXX`
  - `annual_per_share`
- `JEPI`, `O`
  - `monthly_per_share`
- `NVDY`
  - `weekly_per_share`
- `IAU`
  - `none`
- 국내 커버드콜 3종
  - `monthly_per_share`

미국 종목 기준값은 USD per-share, 국내 종목 기준값은 KRW per-share로 관리하고, UI 출력은 모두 원화로 환산해 보여줍니다.

## 금액 포맷 규칙

앱 전체에서 금액은 반드시 공통 함수 `formatKRW(value)`를 통해 출력합니다.

예시:

- `60,000원`
- `1,162,476원`
- `8,040,469원`

적용 범위:

- KPI 카드
- 표
- 차트 툴팁
- 요약 문구
- 규칙 화면
- 배당 기록 화면
- 추정 화면

## Vercel 배포 방법

1. Git 저장소를 Vercel에 연결합니다.
2. Project Settings > Environment Variables에서 아래 값을 등록합니다.
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
3. Deploy를 실행합니다.

Vercel은 별도 서버 설정 없이 Next.js App Router 앱을 바로 배포할 수 있습니다.

## 확장 아이디어

- 실시간 가격 API 연동
- 세후 배당 추정 모드
- 환율 이력 반영
- 배당 캘린더와 지급일 예측 정교화
- Supabase Auth + RLS 도입
- 목표 달성 시뮬레이션 고도화
