# Dividend Dashboard Design System

## Product direction

Quiet, trustworthy personal-finance workspace. The interface should make balances and cash flow easy to scan without looking like a trading terminal. Use short Korean labels, generous whitespace, and one clear comparison visual per section.

## Tokens

- Background: `#f4f5f0`; card: `#fbfcf7`; foreground: `#17211f`.
- Primary: `#2f7a57`; secondary blue: `#3f7bb8`; warm comparison: `#d28145`.
- Muted surfaces: `#e9ece2`; border: `#dbe3d6`; muted text: `#5f6d67`.
- Scenario mapping: conservative = muted gray, base = primary green, optimistic = warm orange. Always pair color with a Korean text label.
- Radius: controls `0.75rem`; cards `1.5rem`. Use the existing `shadow-soft` only on cards.

## Typography

- Manrope with the system Korean fallback for UI text.
- IBM Plex Mono only for dense numeric values where alignment helps comparison.
- Page title: `text-2xl` to `text-3xl`; section title: `text-lg`; body: `text-sm` with `leading-6`.
- Avoid all-caps English decoration. Korean labels are the primary information architecture.

## Layout

- Page flow: header, compact controls, three scenario summaries, one monthly chart, one yearly comparison, collapsed assumptions.
- Desktop content uses the shared application shell. Cards use 3 columns only for directly comparable scenarios.
- Mobile stacks controls and summaries into one column. Charts must remain within the viewport and tables use horizontal scrolling.
- Do not place a dark, full-width dashboard island inside the light application shell.

## Components

- Reuse `Card`, `Select`, `Switch`, and `PageHeader` before introducing variants.
- Scenario summary cards share identical structure: label, 12-month net estimate, final monthly estimate, short assumption note.
- Forecast charts show only the three scenario series. Tooltips show full won amounts.
- Investment rules and forecast assumptions live in a native `details` disclosure to keep the default page concise.

## Accessibility and states

- Interactive targets are at least 44px high.
- Focus states use the existing ring token.
- Loading, empty, warning, and unavailable-reinvestment states must use plain Korean text.
- Never communicate a scenario or data freshness state using color alone.
