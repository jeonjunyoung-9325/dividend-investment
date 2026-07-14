# KIS Dividend Dashboard Design System

## 0. Research Log

- Embedded references: Revolut, Sentry, Linear 후보 중 `taste-skill` + Revolut의 핀테크 정밀성을 선택했다. 마케팅용 초대형 타이포그래피는 제외한다.
- UI database: 데이터 밀도 높은 금융 대시보드, 시계열·기여도·모바일 표 패턴을 확인했다.
- Streamlit: 최신 공식 `st.navigation`, `st.columns`, `st.dataframe`, `st.plotly_chart`, `AppTest` 계약을 확인했다.
- Imagen concept: `docs/design-concept.png`에서 1440px 데스크톱과 375px 모바일을 함께 비교했고, 검은 핀테크 표면·상태별 청/녹/보라 라벨·모바일 카드 적층을 채택했다. 생성안의 고정 사이드바와 주문을 연상시키는 내비게이션은 Streamlit의 상단 내비게이션과 조회 전용 정보 구조로 대체했다.
- External screen clone skipped: 특정 제품을 복제하지 않고 공식 Streamlit 컴포넌트와 자체 정보 구조를 사용했다.

## 1. Atmosphere & Identity

내 자산의 상태와 배당 현금흐름을 조용하고 정확하게 확인하는 개인 금융 관제판이다. 트레이딩 터미널처럼 보이지 않으며, 모든 숫자에 실제·확정·예상 근거와 기준 시각이 따라붙는 “검증 가능한 숫자”가 시각적 서명이다.

## 2. Color

| Role | Token | Light | Dark | Usage |
|---|---|---|---|---|
| Surface | `--surface-primary` | `#FAFAFA` | `#0F1115` | 앱 배경 |
| Panel | `--surface-secondary` | `#FFFFFF` | `#171A20` | 카드·패널 |
| Text | `--text-primary` | `#18181B` | `#FAFAFA` | 제목·금액 |
| Muted text | `--text-secondary` | `#52525B` | `#B8BEC9` | 설명·메타데이터 |
| Border | `--border-default` | `#E4E4E7` | `#343A46` | 경계 |
| Accent | `--accent-primary` | `#2563EB` | `#60A5FA` | 행동·포커스 |
| Success | `--status-success` | `#047857` | `#34D399` | 성공·확정 |
| Warning | `--status-warning` | `#B45309` | `#FBBF24` | 부분 성공·오래된 값 |
| Error | `--status-error` | `#B91C1C` | `#F87171` | 실패 |
| Estimated | `--status-estimated` | `#7C3AED` | `#C4B5FD` | 추정값 |

색상은 단독 상태 표시로 쓰지 않는다. 실제·확정·예상, 성공·부분 성공·실패 텍스트를 항상 병기한다.

## 3. Typography

- Primary: `Pretendard, Noto Sans KR, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif`
- 금액과 수량: `font-variant-numeric: tabular-nums`
- Page title: 28–32px / 700 / 1.25
- Section title: 20–24px / 650 / 1.35
- Card value: `clamp(20px, 4vw, 30px)` / 700 / 1.2
- Body: 16px / 400 / 1.55
- Table: 14px / 400 / 1.5
- Metadata: 12–13px / 500 / 1.4

금액을 줄임표로 자르지 않는다. 작은 카드에서는 단위를 분리하거나 글자 크기를 줄인다.

## 4. Spacing & Layout

- Base: 4px
- Scale: 4, 8, 12, 16, 20, 24, 32, 40, 48px
- Content max: 1440px
- Card padding: mobile 16px, desktop 20–24px
- Radius: card 12px, badge 999px
- Touch target: 44×44px minimum

| Width | KPI | Charts | Filters | Tables |
|---|---|---|---|---|
| `<360` | 1 column | 1 column | vertical | compact + detail |
| `360–767` | 2 columns | 1 column | expander | compact + detail |
| `768–1199` | 2 columns | 1–2 columns | 2 columns | internal scroll |
| `≥1200` | 4 columns | 2 columns | row | detailed |

페이지 본문 수평 스크롤은 금지하고, 데이터 표 자체의 가로 스크롤만 허용한다. `st.columns`는 한 단계 이상 중첩하지 않는다.

## 5. Components

### Authentication Gate

- Structure: title, read-only notice, password field, submit button, generic feedback
- States: configured, missing hash, invalid, delayed, success, expired
- Accessibility: visible label, password autocomplete, generic error
- Boundary: authentication succeeds before navigation or any data provider call

### Metric Grid

- Structure: evidence badge, label, value, delta, basis
- Variants: actual, confirmed, estimated, neutral, unavailable, stale
- Layout: intrinsic grid, 1/2/4 tracks by width
- Accessibility: label precedes value; status never color-only

### Sync Status

- Structure: state label, message, last success, token action, saved counts, failure details
- States: idle, running, success, partial, failed, stale fallback
- Security: token value, headers, account number, raw errors are forbidden

### Data Source

- Structure: source, basis time, fetch time, realtime status, last-saved flag
- Variants: KIS official, user upload, user input, external rate, calculated estimate

### Responsive Data Table

- Desktop: complete table with sorting and horizontal table scroll
- Mobile: essential columns plus a selected-row detail table or expander
- States: populated, empty, filtered-empty, loading, failed with last data

### Chart

- Structure: visible title, chart, one-sentence summary, table fallback
- Width: `width="stretch"`; page-scroll conflict avoided with `scrollZoom=False`
- Accessibility: series differ by label and style, not color alone

### Import Flow

- Steps: select, detect, map, validate, preview, duplicate review, confirm, save, result
- No upload is persisted as a server file; only confirmed normalized rows reach the DB

## 6. Motion & Interaction

- No decorative animation or live ticker
- Buttons expose default, hover, active, focus, disabled, and running states
- Nonessential motion is disabled for `prefers-reduced-motion`
- A synchronization button is disabled while the operation is running
- Tab and expander controls retain native Streamlit keyboard semantics

## 7. Depth & Surface

Strategy: borders plus tonal shift. Cards use one subtle border and a slightly shifted surface. Shadows and decorative glass effects are not used. Financial state colors are reserved for semantics.

## 8. Accessibility Constraints & Accepted Debt

- Target: WCAG 2.2 AA
- Body text contrast: 4.5:1; large text and controls: 3:1
- Full keyboard reachability and visible focus are required
- Errors must include text and recovery guidance
- 200% zoom must not overlap or clip primary content
- Every Plotly chart has a text summary and table fallback
- Light and dark modes are independently checked

Accepted debt: none. Streamlit or Plotly limitations require a documented fallback before acceptance.

## Visual QA Contract

Test every page and major state at 375×812, 390×844, 844×390, 768×1024, 1280×800, and 1440×900. Verify no body horizontal overflow, no clipped KPI, usable mobile filters and tables, responsive charts, keyboard focus order, 44px touch targets, 200% zoom, light/dark contrast, empty data, long names, long amounts, partial sync, stale fallback, and session expiry.
