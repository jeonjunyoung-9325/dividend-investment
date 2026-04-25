const baseUrl = process.env.BACKFILL_BASE_URL ?? "http://127.0.0.1:3002";
const startYear = Number(process.env.BACKFILL_START_YEAR ?? "2020");

async function main() {
  let cursor = null;
  let importedCount = 0;

  while (true) {
    const response = await fetch(`${baseUrl}/api/dividends/sync`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify({
        cursor,
        startYear,
      }),
    });

    const text = await response.text();
    const json = text ? JSON.parse(text) : {};

    if (!response.ok) {
      throw new Error(json.message ?? text ?? "배당 백필에 실패했습니다.");
    }

    importedCount += json.importedCount ?? 0;
    const label = json.stepLabel ?? "배치 처리";
    const progress = `${json.currentStep ?? "?"}/${json.totalSteps ?? "?"}`;
    console.log(`[${progress}] ${label} · 누적 ${importedCount}건`);

    if (json.completed) {
      console.log(`완료: 총 ${importedCount}건 동기화`);
      break;
    }

    cursor = json.nextCursor ?? null;
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
