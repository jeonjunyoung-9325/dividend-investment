import "server-only";

import Decimal from "decimal.js";
import {
  fetchKisDomesticActualDividends,
  fetchKisOverseasDividendRights,
  fetchKisOverseasSettledBalances,
  isKisConfigured,
} from "@/lib/market/kis";
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

function buildOverseasExternalKey(input: {
  assetId: string;
  paidDate: string;
  baseDate: string;
  grossAmountKrw: string;
}) {
  return [
    "kis_overseas_rights_balance",
    input.assetId,
    input.paidDate,
    input.baseDate,
    input.grossAmountKrw,
  ].join(":");
}

export async function syncActualDividendsFromKis() {
  if (!isKisConfigured()) {
    throw new Error("KIS 환경변수가 설정되지 않았습니다.");
  }

  const supabase = getSupabaseServerClient();
  const { data: assetsData, error } = await supabase.from("assets").select("*");
  if (error) {
    throw error;
  }

  const assets = (assetsData ?? []) as Asset[];
  const domesticAssets = new Map(
    assets
      .filter((asset) => asset.market === "KR")
      .flatMap((asset) => {
        const keys = [asset.quote_symbol, asset.ticker].filter(Boolean) as string[];
        return keys.map((key) => [key, asset] as const);
      }),
  );
  const overseasAssets = new Map(
    assets
      .filter((asset) => asset.market === "US")
      .flatMap((asset) => {
      const keys = [asset.quote_symbol, asset.ticker].filter(Boolean) as string[];
      return keys.map((key) => [key, asset] as const);
    }),
  );

  const now = new Date();
  const startYear = now.getFullYear() - 5;
  const startDate = `${startYear}0101`;
  const endDate = `${now.getFullYear()}1231`;

  const domesticRows = await fetchKisDomesticActualDividends({ startDate, endDate });
  const domesticUpsertRows = domesticRows
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

  const settledBalanceCache = new Map<string, Awaited<ReturnType<typeof fetchKisOverseasSettledBalances>>>();
  const overseasUpsertRows = [];

  for (const asset of overseasAssets.values()) {
    const rightsRows = await fetchKisOverseasDividendRights({
      startDate,
      endDate,
      ticker: asset.ticker,
    });

    for (const row of rightsRows) {
      if (row.status !== "Y") {
        continue;
      }

      const balanceDate = row.localRecordDate || row.baseDate;
      if (!balanceDate) {
        continue;
      }

      if (!settledBalanceCache.has(balanceDate)) {
        settledBalanceCache.set(balanceDate, await fetchKisOverseasSettledBalances({ baseDate: balanceDate }));
      }

      const balances = settledBalanceCache.get(balanceDate) ?? [];
      const matchedBalance = balances.find((balance) => balance.symbol === asset.ticker);
      if (!matchedBalance) {
        continue;
      }

      const quantity = new Decimal(matchedBalance.shares || "0");
      const perShareAmount = new Decimal(row.perShareAmount || "0");
      const fxRate = new Decimal(matchedBalance.exchangeRate || "0");
      if (quantity.lte(0) || perShareAmount.lte(0) || fxRate.lte(0)) {
        continue;
      }

      const grossAmountForeign = quantity.mul(perShareAmount);
      const grossAmountKrw = grossAmountForeign.mul(fxRate).toDecimalPlaces(2, Decimal.ROUND_HALF_UP);
      const externalKey = buildOverseasExternalKey({
        assetId: asset.id,
        paidDate: row.baseDate || balanceDate,
        baseDate: balanceDate,
        grossAmountKrw: grossAmountKrw.toFixed(2),
      });

      overseasUpsertRows.push({
        asset_id: asset.id,
        paid_date: row.baseDate || balanceDate,
        gross_amount_krw: grossAmountKrw.toFixed(2),
        tax_amount_krw: null,
        memo: `KIS 해외 권리조회 자동 동기화 · ${row.name} · 기준수량 ${quantity.toFixed(8)}주 · 주당 ${perShareAmount.toFixed(5)} ${row.currency} · 환율 ${fxRate.toFixed(4)}`,
        source: "kis_overseas_rights_balance" as const,
        external_key: externalKey,
        imported_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    }
  }

  const upsertRows = [...domesticUpsertRows, ...overseasUpsertRows];

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
    domesticImportedCount: domesticUpsertRows.length,
    overseasImportedCount: overseasUpsertRows.length,
    note: "국내는 KIS 권리현황, 해외는 KIS 권리조회와 기준일 결제잔고를 결합해 과거 기준수량 기반으로 세전 배당을 원화 환산해 동기화했습니다.",
  };
}
