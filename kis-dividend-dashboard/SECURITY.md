# 보안 정책

이 문서는 인터넷에 공개되는 개인용 Streamlit 배포를 전제로 한 운영 지침입니다. 보안 사고가
의심되면 먼저 앱을 비공개 또는 중지하고, 노출된 값을 원 제공자에서 폐기·회전한 뒤 원인을
조사하세요. Git 기록에서 문자열을 삭제하는 것만으로는 이미 유출된 Secret을 안전하게 만들 수
없습니다.

## 조회 전용 설계와 주문 기능 배제

앱의 KIS 경계는 접근토큰 발급과 잔고·계좌현황·거래/권리/배당 일정·시세·환율 등 조회 API로
제한합니다. 매수, 매도, 정정, 취소, 예약주문, 조건주문, 자동매매 및 주문가능금액을 이용한 실행
코드는 포함하지 않습니다. UI에도 주문 입력, 주문 hashkey 생성 또는 주문 endpoint를 노출하지
않습니다.

KIS 권한 설정에서 조회와 주문 권한을 분리할 수 있다면 필요한 최소 조회 권한만 부여하세요. 코드
검토 시 `/order`, 매수·매도 TR ID, 주문 body 생성이 새로 추가되지 않았는지 확인합니다. 이 앱은
투자 판단이나 세무 자문 도구가 아니며 예상 배당·세후 금액은 명시된 가정에 따른 추정치입니다.

## Secret 저장과 배포 환경 분리

다음 값은 로컬 `.env` 또는 Streamlit Community Cloud의 서버 측 Secrets에만 둡니다.

- `KIS_APP_KEY`, `KIS_APP_SECRET`
- `KIS_ACCOUNT_NO`, `SUPABASE_DB_URL`
- `APP_PASSWORD_HASH`, `SESSION_SECRET`, `TOKEN_ENCRYPTION_KEY`

`.env`, `.streamlit/secrets.toml`, `*.pem`, `*.key`, `token_cache*`는 Git에서 제외합니다. 예제,
테스트 fixture, issue, PR, 화면 캡처, 브라우저 query parameter와 localStorage에 실제 값을 넣지
마세요. Streamlit 설정 화면에서도 위 값은 읽거나 수정할 수 없습니다. 개발·테스트·운영 자격증명과
DB를 분리하고 테스트에 운영 Supabase를 사용하지 않습니다.

대시보드 테이블은 기존 Supabase 프로젝트의 `public` 객체와 충돌하지 않도록 전용
`kis_dashboard` 스키마에 저장합니다. 애플리케이션의 PostgreSQL 세션은 해당 스키마만
`search_path`로 사용하며 `anon`, `authenticated`, `public` 역할의 schema·table·routine·sequence
권한을 마이그레이션에서 철회합니다. 이 앱은 PostgreSQL 서버 연결만 사용하므로 Supabase Data API의
Exposed schemas에 `kis_dashboard`를 추가하지 않습니다.

공개 push 전 다음을 확인합니다.

```bash
git status --short
git ls-files | grep -E '(^|/)(\.env|secrets\.toml)$|\.(pem|key)$|token_cache' && \
  echo "민감 파일 추적 여부를 확인하세요" || true
```

Secret 원문을 찾기 위한 명령을 공유 터미널에서 실행하면 그 출력 자체가 새 유출이 될 수 있습니다.
GitHub secret scanning 경고는 오탐으로 넘기지 말고 실제 값이면 즉시 폐기합니다.

## 접근토큰 암호화와 키 관리

KIS 접근토큰은 `cryptography`의 Fernet 인증 대칭암호로 애플리케이션에서 암호화한 뒤
`kis_token_cache.encrypted_access_token`에 저장합니다. 자체 암호 알고리즘은 사용하지 않습니다.
DB에는 App Key 원문이 아니라 SHA-256 fingerprint만 저장하며 Fernet 키는 절대 DB에 저장하지
않습니다. 평문 토큰은 API 요청에 필요한 짧은 수명 객체와 보조 메모리 cache에서만 다룹니다.

`TOKEN_ENCRYPTION_KEY`는 `Fernet.generate_key()`로 생성하고 다른 Secret과 재사용하지 않습니다.
키, 평문 토큰, Authorization header, tokenP 요청 body는 화면, 예외, 객체 표현 또는 로그에 넣지
마세요. 복호화가 실패하면 ciphertext를 출력하지 않고 비민감 `decrypt_failed` 상태만 남깁니다.
실패 상태와 차단시각은 암호화 키 오류가 tokenP 반복 호출로 번지는 것을 막습니다.

토큰 발급은 환경·App Key fingerprint별 PostgreSQL advisory transaction lock 안에서 수행합니다.
잠금 후 cache를 다시 확인하므로 여러 브라우저와 프로세스가 동시에 요청해도 한 발급만 진행합니다.
잠금 timeout이면 중복 발급하지 않습니다. 공식 24시간 유효기간, 1일 1회 원칙과 6시간 갱신주기를
준수하며 네트워크 일시 오류 외에는 자동 재시도하지 않습니다.

## 계좌번호 마스킹

계좌번호 전체는 서버 Secret으로만 전달하고 브라우저, 표, metric, URL, 다운로드 파일과 로그에
표시하지 않습니다. 진단에 식별이 꼭 필요하면 숫자·하이픈을 정규화한 뒤 앞 네 자리만 남겨
`1234****-**` 형태로 표시합니다. 계좌 상품코드도 함께 노출하지 않습니다.

예외 객체나 외부 HTTP client debug logging이 request params를 자동 출력할 수 있으므로 운영에서
wire-level debug logging을 켜지 않습니다. 고객지원에 계좌를 보낼 때도 스크린샷을 먼저 마스킹합니다.

## 로그인 비밀번호와 세션 관리

`APP_PASSWORD_HASH`에는 argon2-cffi `PasswordHasher`로 생성한 Argon2id hash만 저장하고 평문은
어디에도 저장하지 않습니다. 로그인 전에는 KIS API와 실제 계좌 DB provider를 import·호출하지
않습니다. 성공 상태와 마지막 활동시각은 Streamlit `session_state`에서만 유지하며 기본 30분
미사용 시 만료됩니다. 인증정보를 URL이나 브라우저 localStorage에 저장하지 않습니다.

로그인 실패 메시지는 hash 형식, 사용자 존재 여부, 검증 시간을 구분하지 않으며 연속 실패에는
세션별 최대 수 초의 지연이 적용됩니다. 이는 완전한 중앙집중식 brute-force 차단이 아니므로 길고
고유한 비밀번호를 사용하고 공개 URL을 비밀로 간주하지 마세요. 앱은 개인용 단일 비밀번호 게이트로
MFA, 사용자별 계정, 기기 철회 목록을 제공하지 않습니다.

비밀번호를 변경할 때는 `README.md`의 `getpass` 명령으로 새 hash를 생성해 Cloud Secret을 교체하고
앱을 재부팅합니다. 이전 비밀번호를 다른 서비스에서도 사용했다면 그 서비스도 별도로 변경합니다.

## 로그의 민감정보 제거

다음 원문은 어떤 로그 수준에서도 기록하지 않습니다.

- App Key, App Secret, 접근토큰 및 Authorization header
- 계좌번호 전체와 DB 접속 문자열·비밀번호
- Fernet 키, Session Secret, 로그인 평문 비밀번호
- 원본 API request header/body와 업로드 원본 파일

구조화 로그에는 비민감 error class/`msg_cd`, 마스킹 계좌 식별자, API 용도, 거래소, 시작·종료
시각, 성공/부분성공/실패, 저장 건수만 남깁니다. KIS `msg1`이나 HTTP body도 그대로 기록하기 전에
민감값 포함 가능성을 검토합니다. `requests`, SQLAlchemy, psycopg의 상세 debug/echo와 Streamlit
Secrets 출력을 운영에서 비활성화합니다.

장애 자료를 공유하기 전 키처럼 보이는 문자열, URI userinfo, bearer token, 계좌번호를 한 번 더
삭제합니다. 삭제한 값의 자리에는 `<redacted>` 또는 마스킹 문자열만 사용합니다.

## 공개 배포 위험과 완화책

Streamlit Community Cloud URL은 인터넷에서 검색·공유·추측될 수 있습니다. 앱 비밀번호는 계좌
API 자격증명과 다르게 설정하고, 공용 기기에서 로그인하지 않으며 사용 후 로그아웃합니다. 브라우저
자동완성과 화면 녹화, 알림 미리보기, CSV 다운로드 위치도 데이터 노출 경로가 될 수 있습니다.

무료 호스팅은 프로세스 재시작과 휴면이 가능하므로 토큰을 로컬 파일이나 메모리에만 저장하지
않습니다. Supabase에 ciphertext와 UTC 메타데이터를 저장하되, DB를 읽을 수 있는 주체가 Fernet
키까지 함께 얻지 못하도록 서로 다른 서비스에서 보호합니다. GitHub 저장소는 공개될 수 있다는
가정으로 운영합니다.

정기 점검 항목은 다음과 같습니다.

1. GitHub secret scanning과 저장소 접근자 확인
2. Streamlit Cloud 앱 접근자, build/runtime log와 Secret 수정 이력 확인
3. Supabase Auth/DB 접근·연결 log, 비정상 리전·시간대 접속과 용량 확인
4. KIS 포털의 App Key 상태와 예상하지 못한 호출/동기화 시각 확인
5. 의존성 보안 업데이트, `pytest`, Ruff와 정적 검사 실행
6. 주문 endpoint/TR ID가 추가되지 않았는지 조회 전용 allowlist 검토

## App Key·App Secret 유출 대응

1. Streamlit 앱을 즉시 중지하거나 비공개로 전환해 추가 호출을 막습니다.
2. 한국투자 KIS Developers 포털에서 노출된 App Key/App Secret을 폐기·재발급합니다. 하나만
   노출된 것처럼 보여도 같은 자격증명 쌍을 함께 회전합니다.
3. KIS가 제공하는 범위에서 비정상 API 사용과 계좌 활동을 확인하고 의심 거래는 증권사 공식
   고객센터에 문의합니다. 이 앱은 주문 기능이 없지만 유출된 키가 다른 도구에서 악용될 가능성을
   배제하지 않습니다.
4. Cloud Secrets의 두 값을 새 값으로 교체합니다. 새 App Key fingerprint는 기존 token cache와
   분리됩니다.
5. GitHub/Cloud log, commit, artifact, issue, 채팅과 로컬 shell history 등 유출 경로를 조사하고
   공개 사본을 제거합니다. 제거 전 자격증명 폐기가 우선입니다.
6. 앱을 재배포하고 한 번만 동기화합니다. tokenP 호출을 반복하지 말고 공식 발급 제한을 확인합니다.
7. 사고 시각, 범위, 폐기·교체 완료시각과 확인 결과를 Secret 없는 별도 기록에 남깁니다.

App Secret 오류의 원문 request body나 입력한 Secret을 진단 로그로 남기지 않습니다.

## Supabase 접속정보 유출 대응

1. 앱을 중지하고 Supabase Dashboard에서 DB 비밀번호를 즉시 회전합니다.
2. 필요하면 노출된 DB user의 연결을 종료·권한을 철회하고 새 최소권한 user를 준비합니다.
3. Streamlit `SUPABASE_DB_URL`을 새 URI로 교체하고 다른 배포·로컬 환경의 복사본도 갱신합니다.
4. Supabase의 DB 접근/쿼리 log와 테이블 변경시각을 확인해 데이터 열람, 수정, 삭제, 비정상
   연결이 있었는지 조사합니다.
5. 공격자가 `kis_token_cache` ciphertext를 읽었을 가능성이 있으면 Fernet 키도 노출됐는지 별도로
   판단합니다. 두 값이 함께 노출됐거나 판단할 수 없으면 아래 토큰 키 유출 절차와 KIS 자격증명
   회전을 함께 수행합니다.
6. 잔고·배당·설정 데이터의 무결성을 정상 백업/동기화 근거와 대조합니다. 오염된 데이터를 무조건
   최신 정상값으로 간주하지 않습니다.
7. migration을 새 DB에 복구해야 한다면 검증된 dump와 `001_initial_schema.sql`을 사용하고,
   실제 계좌 CSV를 공개 저장소로 옮기지 않습니다.

DB URL에는 비밀번호가 포함되므로 URL 일부만 가렸다고 안전하다고 가정하지 않습니다. Supabase
service role key는 이 앱의 PostgreSQL URI와 별개이며 필요하지 않다면 앱에 추가하지 않습니다.

## 토큰 암호화 키 유출 및 교체 대응

Fernet 키만 회전하면 기존 접근토큰 ciphertext를 복호화할 수 없고, 무계획한 재시작은 복호화 실패와
tokenP 발급 제한을 반복할 수 있습니다. 다음 순서를 지킵니다.

1. 앱을 중지하고 Fernet 키가 노출된 위치와 `kis_token_cache` ciphertext/DB 접근정보도 함께
   노출됐는지 판단합니다.
2. ciphertext와 키가 모두 유출됐을 가능성이 있으면 KIS App Key/Secret을 폐기·재발급하여 접근토큰
   신뢰도 함께 끊습니다.
3. 현재 cache의 `environment`, fingerprint 앞부분, `issued_at`, `expires_at`, `last_requested_at`,
   `state`만 조회합니다. ciphertext를 출력하거나 내려받지 않습니다.
4. 공식 1일 1회 발급 원칙과 6시간 갱신주기상 새 발급이 가능한지 확인합니다. 즉시 안전한 발급이
   불가능하면 앱을 중지한 상태로 가능 시각까지 기다립니다.
5. `Fernet.generate_key()`로 새 키를 만들고 Cloud Secret에 저장합니다. 새 키를 DB나 Git에 넣지
   않습니다.
6. 노출된 키로 암호화된 대상 token cache 행을 트랜잭션 안에서 무효화합니다. 다른 환경/App Key
   행과 잔고·배당 데이터는 삭제하지 않습니다. 운영 DB 변경 전 안전한 비민감 메타데이터를
   확인하고 rollback 계획을 마련합니다.
7. 앱을 한 번 재부팅하고 동기화를 한 번만 실행해 새 토큰이 새 키로 암호화 저장됐는지
   `state`와 시각 메타데이터로 확인합니다. 토큰 원문을 확인용으로 출력하지 않습니다.
8. 복호화 실패나 제한 오류가 나면 자동/수동 재시도를 중단하고 blocked 상태와 공식 가능시각을
   확인합니다.

키를 정기적으로 회전할 때도 같은 절차가 필요합니다. 이전 키와 새 키를 동시에 저장하는 임시
dual-key migration은 현재 기본 설계에 포함하지 않습니다.

## 취약점 신고와 보안 점검 절차

공개 issue에 실제 URL, 계좌번호, Secret, DB URI, token, request/response dump 또는 업로드 파일을
첨부하지 마세요. 저장소 관리자가 제공하는 비공개 보안 신고 채널을 사용하고, 채널이 없으면 먼저
민감정보 없는 재현 개요만 전달해 안전한 전달 방법을 합의합니다.

신고에는 다음만 포함합니다.

- 영향받는 버전/commit과 환경(`DEMO_MODE`, KIS real/demo 구분만)
- 민감정보를 제거한 재현 단계, 예상 결과와 실제 결과
- 발생·관찰 시각과 안전한 오류 class/코드
- 계좌 데이터 접근, 토큰 발급, DB 변경 가능성에 대한 영향 평가
- 이미 수행한 중지·폐기·회전 조치

배포 또는 Secret 변경 전 최소 점검:

```bash
python -m pytest -q
ruff check .
ruff format --check .
basedpyright
```

이어 DEMO_MODE에서 로그인 전 실제 provider 미호출, 로그인/만료/로그아웃, 모든 페이지, 모바일
레이아웃, CSV/XLSX 미리보기와 오류 다운로드를 확인합니다. 실제 모드에서는 KIS 호출 제한 내에서
한 번만 동기화하고, 토큰 원문이 DB·화면·로그에 없으며 재시작 뒤 DB token이 재사용되는지
메타데이터로 검증합니다. 검증하지 않은 경로는 정상이라고 보고하지 않습니다.
