# 한국투자증권 잔고·배당금 대시보드

한국투자증권 Open API와 Supabase PostgreSQL을 사용하는 개인용 조회 전용 Streamlit 웹앱입니다.
실제 주문 기능은 포함하지 않습니다.

> API 사양과 운영 정책의 마지막 확인일은 **2026-07-14**입니다. 아래 값은 한국투자증권
> 공식 개발자 포털에서 직접 확인한 것만 기록했으며, 확인하지 못한 동작은 별도로 표시합니다.

## 주요 기능

- 국내·해외 잔고를 공통 스키마로 정규화하고 원통화와 원화 평가액을 함께 표시합니다.
- 실제 입금 배당, 발표되어 자격이 확인된 예정 배당, 과거 이력 기반 예상 배당을 분리합니다.
- 월·분기·반기·연·불규칙 지급주기를 날짜 간격으로 판별하고 여러 예측 방식을 지원합니다.
- 세율과 환율 가정을 명시한 세전·세후 예상액, 월별 흐름, 종목별 기여도를 제공합니다.
- 날짜별 잔고 스냅샷과 직전 조회 대비 자산 변화를 PostgreSQL에 보존합니다.
- UTF-8, UTF-8-SIG, CP949 CSV 및 XLSX 배당 내역을 메모리에서 검증·미리보기한 뒤 가져옵니다.
- 개인용 Argon2 비밀번호 로그인, 미사용 세션 만료, 로그아웃, 로그인 실패 지연을 적용합니다.
- API 키 없이도 국내 2종목·미국 3종목과 30일 이력을 확인할 수 있는 격리된 DEMO_MODE가 있습니다.
- 모바일과 데스크톱에서 사용할 수 있는 한국어 반응형 Streamlit 화면을 제공합니다.

주문, 정정, 취소, 예약주문, 자동매매 기능은 소스와 화면 모두에 포함하지 않습니다.

## 기술 구조

```text
브라우저
  -> Streamlit 로그인 게이트와 조회 전용 UI
  -> 서비스·계산 계층
  -> KIS 조회 전용 클라이언트
  -> Supabase PostgreSQL
       - 잔고/배당/환율/동기화 이력
       - Fernet 암호문 형태의 KIS 접근토큰
       - PostgreSQL advisory transaction lock
```

Python 3.12, Streamlit, SQLAlchemy 2.x, psycopg 3, Pydantic Settings, Pandas,
Plotly, cryptography(Fernet), argon2-cffi, openpyxl, pytest 및 Ruff를 사용합니다.
운영 저장소는 PostgreSQL이며 SQLite는 인메모리 테스트에서만 사용합니다. 금액·수량 계산은
`Decimal`, DB 저장은 `NUMERIC`, 시간은 timezone-aware UTC를 사용하고 화면에서
`Asia/Seoul`로 변환합니다.

## 프로젝트 구조

```text
kis-dividend-dashboard/
├── app.py                         # 인증 이후 페이지 라우팅
├── pages/                         # 잔고·배당·캘린더·이력·설정
├── src/
│   ├── calculations/              # 배당주기·예측·세금·환산
│   ├── kis/                       # 인증, 조회 API, 연속조회, limiter
│   ├── repositories/              # PostgreSQL 영속화와 토큰 잠금
│   ├── services/                  # 동기화, 가져오기, UI 조회 경계
│   ├── ui/                        # 로그인, 반응형 컴포넌트, 포맷
│   ├── config.py                  # 서버 측 Secret 검증
│   ├── models.py                  # SQLAlchemy 2.x 모델
│   ├── schemas.py                 # 정규화 입력·출력 스키마
│   └── security.py                # Fernet·fingerprint·마스킹
├── migrations/001_initial_schema.sql
├── sample_data/                   # 비민감 가상 가져오기 데이터
├── tests/                         # mock 기반 단위·통합 테스트
├── .env.example
├── pyproject.toml
├── SECURITY.md
└── DATA_SOURCES.md
```

## 데이터 흐름과 조회 전용 경계

로그인 성공 전에는 지연 import 경계를 유지하여 KIS 클라이언트와 실제 계좌 DB 조회 서비스를
호출하지 않습니다. `지금 동기화`를 누르면 토큰 재사용 여부를 먼저 판단하고, 국내 잔고와 활성
해외 거래소를 조회한 뒤 성공한 결과만 정규화·upsert합니다. 일부 거래소나 환율 조회가 실패하면
성공한 범위는 저장하고 마지막 정상 데이터는 삭제하지 않습니다. 동기화 로직은 UI와 분리되어
같은 흐름을 CLI에서도 실행할 수 있습니다.

`DEMO_MODE=true`에서는 KIS 토큰·잔고 API와 실제 계좌 DB 데이터 경로를 사용하지 않고
`src/demo_data.py`의 결정적 가상 데이터만 읽습니다. 로그인은 demo에서도 필요합니다.

## 한국투자증권 공식 API 확인 결과

### 공식 자료와 확인일

- 확인일: **2026-07-14 (Asia/Seoul)**
- [KIS Developers API 가이드](https://apiportal.koreainvestment.com/apiservice-apiservice)
- [OAuth 공식 API 목록](https://apiportal.koreainvestment.com/api/apis/public/api-list/21ee37e4-dec1-4738-91ce-04f693a7ed29)
- [국내주식 주문/계좌 공식 API 목록](https://apiportal.koreainvestment.com/api/apis/public/api-list/b0a44bfd-dfd5-47f1-9b06-758383e595db)
- [해외주식 주문/계좌 공식 API 목록](https://apiportal.koreainvestment.com/api/apis/public/api-list/fae9f1bb-0de9-4523-ab91-6c534e212700)
- [국내주식 종목정보 공식 API 목록](https://apiportal.koreainvestment.com/api/apis/public/api-list/996ddbef-140c-46da-9bfb-b1cdc1d9b81b)
- [해외주식 시세분석 공식 API 목록](https://apiportal.koreainvestment.com/api/apis/public/api-list/d6ad7811-8c4b-4cbf-b1fa-149234017f40)
- [공식 오류코드](https://apiportal.koreainvestment.com/faq-error-code)

공식 포털은 개별 API 화면을 쿼리 경로로 전환하므로, 위 공식 목록과 아래 API 경로·TR ID를
함께 대조했습니다. 문서에 없는 HTTP 상태 코드, 헤더 또는 응답 필드는 추정하지 않습니다.

### 실전·모의투자 기본 URL

| 환경 | 공식 기본 URL |
| --- | --- |
| 실전투자 | `https://openapi.koreainvestment.com:9443` |
| 모의투자 | `https://openapivts.koreainvestment.com:29443` |

접근토큰은 두 환경 모두 `POST /oauth2/tokenP`로 발급하지만, 환경·App Key fingerprint별로
분리 저장합니다.

### 사용 API, URL 및 TR ID

| 용도 | Method / 경로 | 실전 TR ID | 모의 TR ID | 공식 한계 |
| --- | --- | --- | --- | --- |
| 접근토큰 발급 | `POST /oauth2/tokenP` | 없음 | 없음 | 일반 개인/법인 토큰 정책은 아래 참조 |
| 국내주식 잔고·예수금 | `GET /uapi/domestic-stock/v1/trading/inquire-balance` | `TTTC8434R` | `VTTC8434R` | 실전 50건, 모의 20건/회 후 연속조회 |
| 국내 주문체결 이력 | `GET /uapi/domestic-stock/v1/trading/inquire-daily-ccld` | 최근 3개월 `TTTC0081R`, 이전 `CTSC9215R` | 최근 3개월 `VTTC0081R`, 이전 `VTSC9215R` | 실전 100건, 모의 15건/회 후 연속조회 |
| 국내 계좌 권리 | `GET /uapi/domestic-stock/v1/trading/period-rights` | `CTRGA011R` | 미지원 | 권리유형 3이 배당이나 실제 입금 전용 API는 아님 |
| 국내 배당 일정 | `GET /uapi/domestic-stock/v1/ksdinfo/dividend` | `HHKDB669102C0` | 미지원 | 예탁원 제공 정보용 일정 |
| 투자계좌 자산현황 | `GET /uapi/domestic-stock/v1/trading/inquire-account-balance` | `CTRP6548R` | 미지원 | 결제기준 자산현황 |
| 해외주식 잔고 | `GET /uapi/overseas-stock/v1/trading/inquire-balance` | `TTTS3012R` | `VTTS3012R` | 실전 100건/회 후 연속조회, 미니스탁 미지원 |
| 해외 체결기준 현재잔고·환율 | `GET /uapi/overseas-stock/v1/trading/inquire-present-balance` | `CTRP6504R` | `VTRP6504R` | 모의는 `output3`만 정상; 잔고는 `VTTS3012R` 사용 권고 |
| 해외 주문체결 이력 | `GET /uapi/overseas-stock/v1/trading/inquire-ccnl` | `TTTS3035R` | `VTTS3035R` | 실전 20건, 모의 15건/회; 해외소수점 매매내역 미지원 |
| 해외 일별거래 | `GET /uapi/overseas-stock/v1/trading/inquire-period-trans` | `CTOS4001R` | 미지원 | 매매·정산·수수료 내역이며 배당입금 필드 없음 |
| 해외 기간별 권리 | `GET /uapi/overseas-price/v1/quotations/period-rights` | `CTRGT011R` | 미지원 | 예정 권리는 변경 가능; 수령 자격을 보장하지 않음 |

국내 잔고 응답은 보유·주문가능수량, 평균매입가, 현재가, 매입·평가금액, 평가손익·수익률과
`output2`의 예수금·총평가금액을 제공합니다. 해외 잔고 응답은 거래소, 통화, 보유·주문가능수량,
평균매입가, 현재가, 외화 매입·평가금액과 평가손익을 제공합니다. 해외 체결기준 현재잔고의
`bass_exrt`는 원화 평가 적용 기준환율이며 실제 환전금액과 다를 수 있습니다.

### 연속조회 방식과 거래소 코드

연속조회는 다음 공식 규칙을 적용합니다.

1. 첫 요청의 `tr_cont` 헤더와 연속조회 키는 공백으로 보냅니다.
2. 응답 헤더 `tr_cont`가 `F` 또는 `M`이면 다음 데이터가 있습니다. `D` 또는 `E`면
   마지막 데이터입니다.
3. 다음 페이지 요청은 응답 헤더가 `M`일 때 `tr_cont: N`을 보내고, 직전 응답의 연속조회
   조건/키를 그대로 전달합니다.
4. 국내 잔고는 `CTX_AREA_FK100`/`CTX_AREA_NK100`, 해외 잔고는
   `CTX_AREA_FK200`/`CTX_AREA_NK200`을 사용합니다. 해외 기간별 권리는 50자리 키를
   사용합니다.

해외 잔고 요청에 확인된 거래소·통화 코드는 다음과 같습니다.

| 범위 | 거래소 코드 |
| --- | --- |
| 실전 미국 전체/시장별 | `NASD` 미국전체, `NAS` 나스닥, `NYSE` 뉴욕, `AMEX` 아멕스 |
| 모의 미국 | `NASD` 나스닥, `NYSE` 뉴욕, `AMEX` 아멕스 |
| 실전·모의 공통 | `SEHK` 홍콩, `SHAA` 상해, `SZAA` 심천, `TKSE` 일본, `HASE` 하노이, `VNSE` 호치민 |
| 통화 | `USD`, `HKD`, `CNY`, `JPY`, `VND` |

`NASD`의 의미가 실전에서는 미국전체, 모의에서는 나스닥으로 다릅니다. 같은 티커가 서로 다른
거래소에 존재할 수 있으므로 해외 종목 키는 `market + exchange + symbol`로 구성합니다.

### 응답·오류·호출 제한

정상 응답은 `rt_cd == "0"`이며, 실패 응답은 `msg_cd`와 `msg1`을 함께 검사합니다. 공식
오류코드 중 앱이 명시적으로 구분하는 값은 `EGW00103`(유효하지 않은 App Key),
`EGW00105`(유효하지 않은 App Secret), `EGW00121`(유효하지 않은 token),
`EGW00122`(token 없음), `EGW00123`(token 만료), `EGW00201`(초당 거래건수 초과),
`EGW00301`/`EGW00302`(시간 초과)입니다. 국내 잔고에는 별도 원장 유량 초과 메시지
`EGW00215`도 문서화되어 있습니다.

공식 포털은 오류별 HTTP 상태 코드나 `Retry-After` 헤더를 확정적으로 공개하지 않습니다.
따라서 HTTP 상태와 `rt_cd`/`msg_cd`를 함께 검증하며, 확인되지 않은 상태 코드 매핑은
하드코딩하지 않습니다.

[API 호출 유량 안내(2026-04-20 기준)](https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000001/post/d0d1a83f-6f8d-4437-9700-6d26702fd989)에 따르면
실전은 계좌당 초당 18건, 모의는 초당 1건, `/oauth2/tokenP`는 초당 1건입니다. 동시 호출은
100~150ms 간격이 권고됩니다. 또한 [신규 고객 초당 호출 제한 안내](https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000001/post/c1113824-17c7-47a7-b7b8-8880506a847c)에
따라 2026-04-03 17:00부터 신규 신청은 신청 시점부터 3일 동안 초당 3건으로 제한되고 이후
기본 유량으로 상향됩니다. 갱신은 기본 유량이며 모의계좌는 이 신규 제한 대상이 아닙니다.

국내 잔고 API에는 계좌별 일반 유량과 별개인 원장 초당 120 TPS 제한도 있습니다. 이는 전체
원장 제한이므로 앱의 계좌별 limiter 상한으로 오해하지 않습니다. 호출 정책은 변경될 수 있어
배포·장애 대응 전에 위 공지를 다시 확인해야 합니다.

## 접근토큰 정책

### 발급 제한과 유효기간

공식 `접근토큰발급(P)[인증-001]` 문서는 일반 개인·일반 법인 접근토큰에 대해 다음과 같이
명시합니다.

- 유효기간 24시간
- 1일 1회 발급 원칙
- 갱신발급주기 6시간
- 신규 발급 후 6시간 이내 재호출하면 직전 토큰 반환
- 응답의 `access_token_token_expired`로 실제 만료일시 관리

같은 포털 일부 예시의 `expires_in` 설명에는 24시간과 일치하지 않는 장기 값도 혼재하므로, 이
개인용 앱은 명시된 일반고객 24시간 정책과 실제 `access_token_token_expired` 응답을 기준으로 합니다. 잔고 조회,
페이지 새로고침 또는 Streamlit 재시작 때마다 `/oauth2/tokenP`를 호출하지 않습니다.

### 암호화 저장과 재사용

토큰 조회 순서는 프로세스 메모리의 유효 토큰, `kis_token_cache`의 유효 암호문, 신규 발급 순입니다.
메모리 캐시는 성능 보조 수단일 뿐 영속 기준이 아닙니다. DB에는 App Key 원문 대신 SHA-256
fingerprint와 `TOKEN_ENCRYPTION_KEY`를 이용한 Fernet 인증 암호문만 저장합니다. 발급 응답의
`access_token_token_expired`를 우선 사용하고, 확인할 수 없을 때만 공식 24시간 유효기간을
보조값으로 사용합니다.

모든 비교는 UTC aware datetime으로 수행하며 기본 5분의 만료 여유시간을 둡니다. 여유시간에
진입했다는 이유만으로 반복 발급하지 않고 실제 만료, 마지막 발급·요청 시각, 6시간 갱신주기와
실패 차단 상태를 함께 확인합니다. 복호화 실패는 `decrypt_failed` 상태로 기록하고 원문이나
암호화 키를 오류에 포함하지 않습니다. 실전과 모의 토큰 및 서로 다른 App Key는 각각 별도 행입니다.

### PostgreSQL 잠금과 중복 발급 방지

신규 발급 후보가 생기면 환경과 App Key fingerprint에서 안정적인 lock key를 만들고 PostgreSQL
`pg_advisory_xact_lock`을 트랜잭션 범위에서 획득합니다. `TOKEN_LOCK_TIMEOUT_SECONDS` 안에
잠금을 얻지 못하면 중복 발급하지 않고 동기화를 중단합니다. 잠금 획득 뒤 DB를 다시 읽어 다른
세션이 저장한 유효 토큰이 있으면 그것을 재사용합니다. 여전히 발급이 필요한 경우에만
`/oauth2/tokenP`를 호출하고 암호문·발급/만료/마지막 요청 시각을 같은 트랜잭션에 저장합니다.

네트워크 일시 오류만 최대 한 번 재시도합니다. 인증·호출제한·응답 검증 오류는 재시도하지 않으며,
아직 실제로 만료되지 않은 마지막 토큰이 있으면 그 토큰을 사용합니다. 안전한 토큰이 없으면 기존
잔고를 보존한 채 사용자에게 마지막 정상 데이터임을 알립니다.

## 공식 API만으로 제공되지 않는 데이터

2026-07-14 현재 공식 전체 API 카탈로그에서 일반 개인계좌의 국내·해외 **실제 배당 입금**을
`gross_amount`, `tax_amount`, `net_amount`로 완전하고 명확하게 반환한다고 확인된 전용 API는
찾지 못했습니다. 국내 `기간별계좌권리현황조회`에는 배당 권리, 지급일, 배정금액, 세금 관련
필드가 있지만 공식 문서가 이를 실제 입금 원장의 완전한 대체라고 명시하지 않습니다. 해외
`기간별권리조회`는 일정·주당배당·확정여부 정보이며 개인 계좌의 수령 자격이나 실제 입금액을
보장하지 않습니다.

또한 일반 주식 계좌의 범용 입출금내역 API, 오류별 HTTP 상태 코드, `Retry-After` 헤더는 공식
포털에서 확인하지 못했습니다. 이 값들은 추측하지 않습니다.

실제 받은 배당금은 다음 우선순위로 보완합니다.

1. 공식 API에서 의미가 명확히 확인된 값
2. 사용자가 한국투자증권에서 내려받아 업로드한 CSV 또는 XLSX
3. 사용자가 직접 입력한 배당 내역
4. 검증 가능한 외부 제공자 데이터
5. 데이터 없음 또는 계산 불가 표시

파일 업로드 값은 `source`로 공식 API 값과 구분하고 파일·행 hash로 중복을 방지합니다. 확정
예정 배당은 기준일 당시 수량을 확인할 수 없으면 현재 수량으로 대체하지 않고
`수령 자격 확인 필요`로 표시합니다. 자세한 출처 경계는 `DATA_SOURCES.md`를 참조하세요.

## 데이터 출처와 최신성 표시

모든 화면은 가능한 범위에서 출처, 조회 시각, 기준일, 실시간 여부와 마지막 정상 저장값 사용 여부를
같이 표시합니다. KIS 공식 API, 사용자 업로드, 직접 입력, 외부 제공자와 계산 추정값은 서로 다른
`source`로 저장합니다. 출처가 없거나 필수 값이 부족하면 0으로 채우지 않고 `데이터 없음`,
`계산 불가`, `수령 자격 확인 필요` 또는 `예측 불가`로 표시합니다. 세부 규칙은
[DATA_SOURCES.md](DATA_SOURCES.md)에 있습니다.

## 로컬 실행

### Python 3.12 준비

```bash
cd kis-dividend-dashboard
python3.12 -m venv .venv
source .venv/bin/activate
python --version
```

마지막 명령이 `Python 3.12.x`인지 확인합니다.

### 의존성 설치

실행 의존성만 설치하려면 다음을 사용합니다.

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

테스트와 정적 검사를 함께 수행하려면 프로젝트와 개발 도구를 설치합니다. `pyproject.toml`의
`dependency-groups.dev`는 개발 도구 버전의 기준입니다.

```bash
python -m pip install -e .
python -m pip install \
  'basedpyright>=1.21,<2' \
  'pytest>=8.3,<10' \
  'pytest-cov>=6,<8' \
  'pytest-mock>=3.14,<4' \
  'responses>=0.25,<1' \
  'ruff>=0.9,<1'
```

### 환경변수 설정

```bash
cp .env.example .env
```

아래 `환경변수와 Secret` 표에 따라 `.env`를 채웁니다. `.env`와
`.streamlit/secrets.toml`은 Git에서 제외되어 있습니다. 실제 값을 셸 기록, 이슈, README,
스크린샷 또는 테스트 fixture에 넣지 마세요.

### 데이터베이스 마이그레이션

Supabase Dashboard의 **SQL Editor**에서 `migrations/001_initial_schema.sql` 전체를 실행합니다.
마이그레이션은 기존 `public` 테이블을 변경하지 않고 비공개 `kis_dashboard` 스키마를 생성합니다.
로컬에 `psql`이 있고 직접 연결이 허용된 경우에는 다음도 가능합니다.

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f migrations/001_initial_schema.sql
```

마이그레이션 성공 후 Table Editor의 schema 선택을 `kis_dashboard`로 바꾸고
`portfolio_snapshots`, `dividend_import_batches`, `dividend_payments`,
`dividend_events`, `exchange_rates`, `kis_token_cache`, `sync_runs`, `app_settings` 테이블과
인덱스·제약조건이 생성됐는지 확인합니다. SQLAlchemy 연결에는
`search_path=kis_dashboard`가 자동 적용되어 같은 이름의 기존 `public` 테이블을 읽지 않습니다.
운영 DB에 SQLite URL을 사용하지 마세요.

### Streamlit 실행

가상 데이터로 먼저 확인합니다.

```bash
DEMO_MODE=true streamlit run app.py
```

실제 모드는 `.env`의 모든 필수 Secret과 Supabase migration을 준비한 뒤 실행합니다.

```bash
streamlit run app.py
```

기본 브라우저가 열리지 않으면 터미널에 표시된 `http://localhost:8501`로 접속합니다.

## 환경변수와 Secret

실제 값은 로컬 `.env` 또는 Streamlit Community Cloud의 Secrets에만 저장합니다.
`.env.example`에는 변수 이름과 비민감 기본값만 둡니다.

| 이름 | 필수 시점 | 설명 |
| --- | --- | --- |
| `KIS_APP_KEY` | 실제 모드 | 한국투자 Open API App Key |
| `KIS_APP_SECRET` | 실제 모드 | 한국투자 Open API App Secret |
| `KIS_ACCOUNT_NO` | 실제 모드 | 상품코드를 제외한 계좌번호. 화면·로그에 원문 표시 금지 |
| `KIS_ACCOUNT_PRODUCT_CODE` | 실제 모드 | 두 자리 상품코드, 기본 `01` |
| `KIS_MODE` | 실제 모드 | `real` 또는 `demo`(한국투자 모의투자 환경). 앱 샘플 모드와 다름 |
| `SUPABASE_DB_URL` | 실제 모드 | Supabase PostgreSQL 접속 문자열 |
| `APP_PASSWORD_HASH` | 모든 웹 실행 | Argon2id 비밀번호 hash. 평문 비밀번호 금지 |
| `SESSION_SECRET` | 실제 모드 | 충분히 긴 무작위 서버 Secret. 브라우저에 저장하지 않음 |
| `TOKEN_ENCRYPTION_KEY` | 실제 모드 | Fernet 키. 접근토큰 암호화용 |
| `DEFAULT_USD_KRW_RATE` | 선택 | 정상 환율을 구할 수 없을 때만 쓰는 명시적 기본값 |
| `TOKEN_EXPIRY_BUFFER_MINUTES` | 선택 | 만료 안전 여유시간, 기본 5분 |
| `TOKEN_LOCK_TIMEOUT_SECONDS` | 선택 | 토큰 DB 잠금 대기 제한, 기본 5초 |
| `SESSION_TIMEOUT_MINUTES` | 선택 | 미사용 로그인 만료, 기본 30분 |
| `DEMO_MODE` | 선택 | `true`이면 실제 API와 실제 계좌 DB 데이터 접근 금지 |

`KIS_MODE=demo`는 한국투자 **모의투자 API**를 뜻하고, `DEMO_MODE=true`는 API를 전혀 호출하지
않는 앱 자체의 **가상 샘플 모드**입니다.

Argon2id hash는 평문을 명령줄 인자로 남기지 않도록 `getpass`로 생성합니다.

```bash
python - <<'PY'
from getpass import getpass
from argon2 import PasswordHasher

password = getpass("새 앱 비밀번호: ")
confirmation = getpass("비밀번호 확인: ")
if not password or password != confirmation:
    raise SystemExit("비밀번호가 비어 있거나 일치하지 않습니다.")
print(PasswordHasher().hash(password))
PY
```

Fernet 키와 세션 Secret은 각각 독립적으로 생성합니다.

```bash
python - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode("ascii"))
PY

python - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
```

출력은 Secret 저장소로 바로 옮기고 터미널 공유·스크린샷·커밋을 피합니다.

## Supabase PostgreSQL 설정

1. [Supabase](https://supabase.com/)에서 무료 프로젝트를 만들고 강한 DB 비밀번호를 설정합니다.
2. **Connect** 화면에서 현재 배포 환경에 맞는 PostgreSQL URI를 복사합니다. Streamlit Cloud에서
   IPv4 호환이 필요하면 Supabase가 안내하는 pooler URI를 선택합니다.
3. URI의 비밀번호 특수문자는 URL encoding이 필요할 수 있습니다. 수정한 URI를 Git이 아닌
   `SUPABASE_DB_URL` Secret에 저장합니다.
4. SQL Editor에서 `migrations/001_initial_schema.sql`을 실행합니다. 기존 프로젝트를 재사용해도
   `public` 스키마의 동명 테이블은 보존되고 대시보드 객체는 `kis_dashboard`에 생성됩니다.
5. Table Editor에서 schema를 `kis_dashboard`로 선택한 뒤 위 8개 테이블과 unique/index/check
   제약이 생성됐는지 확인합니다. 이 스키마를 Data API의 Exposed schemas에 추가하지 마세요.
6. DB 연결 실패를 대비해 프로젝트의 리전, 휴면 상태, 접속 문자열, 비밀번호와 SSL 조건을
   확인합니다. DB URL 전체를 로그나 문의 글에 붙이지 마세요.

무료 프로젝트의 휴면·용량·연결 정책은 바뀔 수 있습니다. 앱은 프로세스 로컬 파일을 운영 데이터로
사용하지 않으므로 Streamlit 재시작 후에도 Supabase의 정상 데이터와 암호화 토큰을 재사용합니다.

## 개인용 로그인과 세션 만료

앱 첫 화면은 로그인 게이트입니다. Argon2 검증이 성공해야 페이지 및 실제 데이터 provider가
로드됩니다. 성공 여부와 마지막 활동시각은 브라우저별 Streamlit `session_state`에서 관리하고,
`SESSION_TIMEOUT_MINUTES` 동안 미사용하면 만료됩니다. 연속 실패에는 세션별 짧은 지연이
적용되며 오류는 검증 상세를 노출하지 않습니다. 로그아웃은 현재 session state를 제거합니다.

이 로그인은 개인용 단일 비밀번호 게이트이며 다중 사용자 계정, MFA, IP 차단 시스템은 아닙니다.
공개 URL은 추측 가능하다고 가정하고 강한 고유 비밀번호를 사용하세요.

## 수동 동기화와 CLI 실행

웹에서는 로그인 후 상단 `지금 동기화`를 누릅니다. 진행 중에는 중복 실행을 막고 결과에서 국내,
해외 거래소별, 배당, 환율, 저장·수정 건수와 토큰 신규 발급/재사용 상태를 확인합니다. 부분 실패
시 기존 정상 행은 삭제하지 않습니다.

동일 서비스 흐름을 UI 없이 실행하려면 다음을 사용합니다.

```bash
python -m src.sync
```

CLI도 `.env`의 실제 Secret과 migration된 PostgreSQL이 필요합니다. Cron이나 외부 스케줄러는
기본 배포에 포함하지 않으며, 무료 운영은 수동 동기화를 전제로 합니다. 짧은 간격으로 명령을
반복 실행해 토큰 발급을 유도하지 마세요.

## CSV·XLSX 가져오기

1. 한국투자증권에서 거래·배당 내역을 CSV 또는 XLSX로 내려받습니다.
2. 앱의 **배당 > 파일 가져오기**에서 파일을 선택합니다.
3. 자동 인식된 열과 `symbol`, `payment_date`, `gross_amount`, `currency` 필수 매핑을 확인하고,
   나머지 열을 직접 매핑합니다.
4. 날짜·숫자·통화 오류, 유효 후보와 중복 후보를 확인합니다.
5. 원본 파일 의미가 불명확한 열을 임의로 세전·세금·실수령으로 매핑하지 않습니다.
6. 확인 체크 후 저장하고 저장·제외·오류 행 수를 확인합니다.
7. 오류 행은 UTF-8-SIG CSV로 내려받아 수정할 수 있습니다.

CSV 인코딩은 UTF-8-SIG, UTF-8, CP949 순으로 검사하고 XLSX는 openpyxl로 읽습니다. 원본 파일은
메모리에서 처리하며 영구 저장하지 않습니다. 파일 SHA-256과 정규화한 행별 `import_hash`로 같은
파일 또는 행의 재업로드 중복을 막습니다. 샘플 형식은 `sample_data/dividend_payments.csv`를
참조하세요.

## DEMO_MODE

`.env` 또는 Streamlit Secrets에서 `DEMO_MODE=true`로 설정합니다. 이 모드에는 국내 2종목,
미국 주식/ETF 3종목, 원화·달러 자산, 월·분기배당, 세금 포함 실제 지급내역, 확정 이벤트,
데이터 부족 종목과 최소 30일 자산 스냅샷이 포함됩니다. 화면 상단에 가상 데이터임을 표시합니다.

DEMO_MODE는 KIS tokenP 및 잔고 API를 호출하지 않고 실제 계좌 DB 데이터도 조회하지 않습니다.
다만 인터넷에 배포하는 UI이므로 `APP_PASSWORD_HASH`는 설정해야 합니다. 실제 모드로 전환하려면
프로세스를 재시작하고 실제 Secret·DB migration을 확인하세요.

## 테스트와 정적 검사

테스트는 실제 한국투자 API를 호출하지 않고 fake/mock 응답과 인메모리 SQLite를 사용합니다.

```bash
python -m pytest -q
python -m pytest --cov=src --cov-report=term-missing
ruff check .
ruff format --check .
basedpyright
```

PostgreSQL advisory lock의 실제 동작을 별도로 검증하는 테스트가 구성된 경우에는 격리된 테스트용
PostgreSQL URL만 사용하세요. 운영 Supabase를 테스트 대상으로 사용하지 않습니다. 배포 전에는
실행 결과의 실패·경고를 직접 읽고 해결하며, 실행하지 않은 기능을 검증됐다고 간주하지 않습니다.

## Streamlit Community Cloud 배포

### GitHub 저장소 준비

1. GitHub에 새 저장소를 만들고 프로젝트 파일을 push합니다.
2. push 전에 `git status`와 `git ls-files`로 `.env`, `.streamlit/secrets.toml`, 키 파일,
   토큰 cache와 실제 계좌 파일이 추적되지 않는지 확인합니다.
3. GitHub secret scanning 경고가 있으면 배포 전에 실제 Secret을 폐기·재발급합니다. 단순히
   커밋을 삭제하는 것만으로 유출 대응이 끝나지 않습니다.

### Secrets 등록

Streamlit Community Cloud의 앱 **Settings > Secrets**에 다음 TOML을 실제 값으로 입력합니다.

```toml
KIS_APP_KEY = ""
KIS_APP_SECRET = ""
KIS_ACCOUNT_NO = ""
KIS_ACCOUNT_PRODUCT_CODE = "01"
KIS_MODE = "real"
SUPABASE_DB_URL = ""
APP_PASSWORD_HASH = ""
SESSION_SECRET = ""
TOKEN_ENCRYPTION_KEY = ""
DEFAULT_USD_KRW_RATE = ""
TOKEN_EXPIRY_BUFFER_MINUTES = "5"
TOKEN_LOCK_TIMEOUT_SECONDS = "5"
SESSION_TIMEOUT_MINUTES = "30"
DEMO_MODE = "false"
```

Root-level Streamlit Secrets는 서버 환경에서만 읽습니다. 값을 Python 파일, 브라우저 query
parameter, localStorage 또는 화면 설정 페이지로 옮기지 마세요.

### 배포와 최초 로그인

아래 순서가 전체 배포 체크리스트입니다.

1. 한국투자증권 KIS Developers에서 개인 Open API 사용을 신청합니다.
2. App Key와 App Secret을 발급하고 Secret 저장소에만 보관합니다.
3. Supabase 무료 프로젝트를 만들고 강한 DB 비밀번호와 리전을 정합니다.
4. Supabase의 PostgreSQL 접속 URI를 안전하게 보관합니다.
5. SQL Editor에서 `migrations/001_initial_schema.sql`을 실행합니다.
6. GitHub 저장소를 만들고 `.gitignore`를 확인합니다.
7. Secret을 제외한 프로젝트를 GitHub에 push합니다.
8. [Streamlit Community Cloud](https://share.streamlit.io/)에서 저장소, branch, `app.py`를 연결합니다.
9. 앱 Settings의 Secrets에 위 TOML 값을 등록합니다.
10. `getpass` 예제로 Argon2id `APP_PASSWORD_HASH`를 생성하고 평문은 저장하지 않습니다.
11. Fernet `TOKEN_ENCRYPTION_KEY`와 별도 `SESSION_SECRET`을 생성합니다.
12. 앱을 재부팅 또는 redeploy하고 build log에 Secret이 없는지 확인합니다.
13. `https://프로젝트명.streamlit.app`에서 최초 로그인합니다.
14. `지금 동기화`를 한 번 누르고 국내·해외·환율·토큰 재사용 상태를 확인합니다.
15. iOS Safari와 Android Chrome 또는 사용할 모바일 브라우저에서 접속합니다.
16. 아래 절차로 모바일 홈 화면 바로가기를 추가합니다.
17. Secret 변경은 Cloud 앱 Settings에서 수행하고 앱을 재부팅합니다.
18. API 키가 유출되면 즉시 KIS 포털에서 폐기·재발급하고 `SECURITY.md` 대응 절차를 수행합니다.
19. 토큰 암호화 키 변경 전 기존 암호문을 복호화할 수 없게 된다는 점과 발급 제한을 확인합니다.

무료 플랜의 build·휴면·리소스 한도는 현재 정책을 다시 확인하세요.

### 모바일 접속과 홈 화면 바로가기

- iPhone/iPad Safari: 앱 URL 열기 → 공유 버튼 → **홈 화면에 추가** → 이름 확인 → 추가.
- Android Chrome: 앱 URL 열기 → 메뉴(⋮) → **홈 화면에 추가** 또는 **앱 설치** → 확인.

이는 웹앱 바로가기이며 별도 네이티브 앱을 설치하거나 계좌 Secret을 기기에 저장하지 않습니다.
공용 기기에서는 로그인하지 말고, 사용 후 로그아웃과 브라우저 탭 종료를 모두 수행하세요.

## Secret 생성·교체·유출 대응

- 앱 비밀번호 변경: 새 Argon2id hash를 생성해 `APP_PASSWORD_HASH`만 교체하고 재부팅합니다.
- KIS App Key/Secret 변경: KIS 포털에서 기존 자격증명을 폐기한 뒤 두 값을 함께 교체합니다. App Key
  fingerprint가 달라지므로 새 토큰 cache identity가 사용됩니다.
- Supabase 비밀번호 변경: Dashboard에서 회전하고 `SUPABASE_DB_URL`을 즉시 교체한 뒤 기존
  연결을 재부팅합니다.
- Fernet 키 변경: 기존 `kis_token_cache.encrypted_access_token`은 새 키로 복호화할 수 없습니다.
  현재 토큰의 발급·만료와 공식 재발급 가능 시각을 먼저 확인하고, 기존 cache를 안전하게
  무효화한 뒤 한 번만 재발급합니다. 무계획 회전은 반복 발급 실패를 만들 수 있습니다.
- `SESSION_SECRET` 변경: 값을 교체하고 앱을 재부팅하며 기존 세션은 신뢰하지 않고 다시 로그인합니다.

유출은 Git 기록에서 문자열만 지우는 것으로 해결되지 않습니다. 원 제공자에서 폐기·회전하고,
Cloud/GitHub/Supabase 접근 로그와 비정상 동기화를 확인한 뒤 자세한 절차는
[SECURITY.md](SECURITY.md)를 따릅니다.

## 문제 해결

| 증상 | 확인·대응 |
| --- | --- |
| `APP_PASSWORD_HASH가 설정되지 않았습니다` | Argon2id hash인지 확인하고 Cloud Secrets 또는 `.env`에 저장한 뒤 재부팅합니다. |
| 로그인이 계속 실패 | 평문이 아닌 `$argon2...` 전체 hash가 잘리지 않았는지 확인합니다. 상세 검증 오류는 화면에 나오지 않습니다. |
| Supabase 연결 실패 | 프로젝트 휴면, URI, URL-encoded 비밀번호, pooler/IPv4, SSL 및 migration 여부를 확인합니다. DB URL을 화면에 붙이지 않습니다. |
| 토큰 잠금 시간 초과 | 다른 동기화가 끝날 때까지 기다린 뒤 한 번만 다시 시도합니다. 여러 탭에서 반복 클릭하지 않습니다. |
| 토큰 발급 제한/인증 오류 | 1일 1회·6시간 정책과 마지막 요청시각, KIS 자격증명·환경을 확인합니다. 자동 반복 실행하지 않습니다. |
| 토큰 복호화 실패 | `TOKEN_ENCRYPTION_KEY`가 발급 당시와 같은지 확인합니다. 키를 복원할 수 없으면 `SECURITY.md`의 안전한 무효화 절차를 따릅니다. |
| `EGW00123` | 토큰 만료 응답입니다. 앱이 잠금과 발급 정책 아래 갱신하도록 두고 수동 tokenP 호출을 반복하지 않습니다. |
| `EGW00201`/`EGW00215` | 호출 간격을 늘리고 동시 동기화를 중단합니다. 기존 정상 데이터는 유지됩니다. |
| 일부 해외 거래소만 실패 | 실패 거래소 경고와 조회 시각을 확인합니다. 성공 거래소 결과는 유지되므로 전체 데이터를 삭제하지 않습니다. |
| 환율 조회 실패 | 마지막 정상 저장환율/사용자값/명시 기본값 적용 여부와 기준일을 확인합니다. 이를 실시간 환율로 해석하지 않습니다. |
| CSV 인코딩·열 오류 | UTF-8(Sig) 또는 CP949인지, 필수 4개 열 매핑과 날짜·금액 형식을 확인하고 오류 행 CSV를 수정합니다. |
| 배당 예측 불가 | 지급 이력 표본, 날짜 간격, 현재 수량을 확인합니다. 데이터 부족을 0으로 대체하지 않습니다. |
| 앱이 재시작된 뒤 데이터 없음 | `DEMO_MODE`, Supabase Secret, migration과 마지막 sync run을 확인합니다. 운영 데이터는 로컬 파일이 아닙니다. |

오류 보고 전에는 민감정보를 제거한 상태에서 발생 시각, 화면의 안전한 오류코드, 환경(real/demo),
마지막 정상 동기화 시각만 기록하세요.

## 보안 문서

보안 운영 지침은 `SECURITY.md`, 데이터 출처별 의미와 한계는 `DATA_SOURCES.md`에서 설명합니다.

## 무료 플랜 주의사항

현재는 Streamlit Community Cloud와 Supabase 무료 플랜 운영을 전제로 합니다. 각 서비스의 무료
플랜 정책, 리소스 한도, 휴면 정책은 향후 변경될 수 있으므로 배포 전에 최신 공식 정책을 확인해야
합니다.

## 남아 있는 제한사항

- 공식 API만으로 실제 국내·해외 배당 입금의 세전·세금·실수령액을 완전하게 확인할 수 없어
  CSV/XLSX 또는 직접 입력이 필요할 수 있습니다.
- 해외 권리·국내 일정만으로 개인 계좌의 수령 자격을 확정하지 않습니다. 기준일 당시 수량이 없으면
  `수령 자격 확인 필요`로 남깁니다.
- 외부 배당 데이터 제공자는 기본 활성화하지 않습니다. 외부 환율이 없으면 마지막 저장값 또는
  명시한 기본 환율을 사용할 수 있으며 실시간으로 표시하지 않습니다.
- 자동 스케줄러, 주문 기능, MFA, 다중 사용자 권한, 세무 판단은 제공하지 않습니다.
- 미니스탁과 모의투자 API의 공식 미지원 범위는 앱에서 보완할 수 없습니다.
- KIS와 무료 호스팅 정책, TR ID, 응답 필드는 변경될 수 있습니다. 공식 확인일 이후 변경사항은
  배포 전 다시 검증해야 합니다.
- Streamlit Community Cloud와 Supabase 무료 플랜은 휴면, 용량, 연결 및 실행시간 정책이 바뀔 수
  있으며 무중단 운영을 보장하지 않습니다.
