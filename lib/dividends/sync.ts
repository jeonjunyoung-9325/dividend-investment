import "server-only";

import { fetchKisDomesticActualDividends, isKisConfigured } from "@/lib/market/kis";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import { Asset } from "@/types";

function buildExternalKey(input: {
  assetId: string;
  paidDate: string;
  grossAmountKrw: string;
  taxAmountKrw: string;
}) {
  return [
    "kis_domestic_period_rights",
    input.assetId,
    input.paidDate,
    input.grossAmountKrw,
    input.taxAmountKrw,
  ].join(":");
}

export async function syncActualDividendsFromKis() {
  if (!isKisConfigured()) {
    throw new Error("KIS 환경변수가 설정되지 않았습니다.");
  }

  const supabase = getSupabaseServerClient();
  const { data: assetsData, error } = await supabase.from("assets").select("*").eq("market", "KR");
  if (error) {
    throw error;
  }

  const assets = (assetsData ?? []) as Asset[];
  const domesticAssets = new Map(
    assets.flatMap((asset) => {
      const keys = [asset.quote_symbol, asset.ticker].filter(Boolean) as string[];
      return keys.map((key) => [key, asset] as const);
    }),
  );

  const now = new Date();
  const startYear = now.getFullYear() - 1;
  const startDate = `${startYear}0101`;
  const endDate = `${now.getFullYear()}1231`;

  const rows = await fetchKisDomesticActualDividends({ startDate, endDate });
  const upsertRows = rows
    .map((row) => {
      const asset = domesticAssets.get(row.symbol);
      if (!asset) {
        return null;
      }

      const externalKey = buildExternalKey({
        assetId: asset.id,
        paidDate: row.paidDate,
        grossAmountKrw: row.grossAmountKrw,
        taxAmountKrw: row.taxAmountKrw,
      });

      return {
        asset_id: asset.id,
        paid_date: row.paidDate,
        gross_amount_krw: row.grossAmountKrw,
        tax_amount_krw: row.taxAmountKrw === "0" ? null : row.taxAmountKrw,
        memo: `KIS 국내 권리현황 자동 동기화 · ${row.name} · 배정수량 ${row.allocatedQuantity}`,
        source: "kis_domestic_period_rights" as const,
        external_key: externalKey,
        imported_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
    })
    .filter((row): row is NonNullable<typeof row> => Boolean(row));

  if (upsertRows.length) {
    const { error: upsertError } = await supabase.from("actual_dividends").upsert(upsertRows, {
      onConflict: "external_key",
    });
    if (upsertError) {
      throw upsertError;
    }
  }

  return {
    importedCount: upsertRows.length,
    skippedOverseas: true,
    note: "국내 KIS 권리현황 기반 실제 배당만 자동 동기화했습니다. 해외 실제 배당은 KIS가 계좌별 원화 세전 입금 row를 제공하지 않아 제외했습니다.",
  };
}
