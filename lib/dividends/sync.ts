import "server-only";

import Decimal from "decimal.js";
import {
  fetchKisDomesticActualDividends,
  fetchKisOverseasDividendRights,
  fetchKisOverseasPeriodTransactions,
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
}) {
  return [
    "kis_overseas_rights_balance",
    input.assetId,
    input.paidDate,
    input.baseDate,
  ].join(":");
}

async function loadSyncContext() {
  if (!isKisConfigured()) {
    throw new Error("KIS 환경변수가 설정되지 않았습니다.");
  }

  const supabase = getSupabaseServerClient();
  const { data: assetsData, error } = await supabase.from("assets").select("*").order("display_order");
  if (error) {
    throw error;
  }

  const assets = (assetsData ?? []) as Asset[];
  const now = new Date();
  const startYear = now.getFullYear() - 10;
  const startDate = `${startYear}0101`;
  const endDate = `${now.getFullYear()}1231`;
  const { data: fxRow } = await supabase.from("fx_rates").select("*").eq("pair", "USD/KRW").maybeSingle();

  return {
    supabase,
    assets,
    startDate,
    endDate,
    fallbackUsdKrw: new Decimal(String(fxRow?.rate ?? "1365.5")),
  };
}

function getOverseasAssets(assets: Asset[]) {
  return assets.filter((asset) => asset.market === "US");
}

async function syncDomesticActualDividends(context: Awaited<ReturnType<typeof loadSyncContext>>) {
  const domesticAssets = new Map(
    context.assets
      .filter((asset) => asset.market === "KR")
      .flatMap((asset) => {
        const keys = [asset.quote_symbol, asset.ticker].filter(Boolean) as string[];
        return keys.map((key) => [key, asset] as const);
      }),
  );

  const domesticRows = await fetchKisDomesticActualDividends({
    startDate: context.startDate,
    endDate: context.endDate,
  });

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
        basis_shares: row.allocatedQuantity === "0" ? null : row.allocatedQuantity,
        per_share_amount:
          new Decimal(row.allocatedQuantity || "0").gt(0)
            ? new Decimal(row.grossAmountKrw).div(row.allocatedQuantity).toDecimalPlaces(8, Decimal.ROUND_HALF_UP).toFixed(8)
            : null,
        per_share_currency: "KRW",
        base_date: row.paidDate,
        local_record_date: null,
        applied_fx_rate: "1.0000",
        memo: `KIS 국내 권리현황 자동 동기화 · ${row.name} · 배정수량 ${row.allocatedQuantity}`,
        source: "kis_domestic_period_rights" as const,
        external_key: externalKey,
        imported_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
    })
    .filter((row): row is NonNullable<typeof row> => Boolean(row));

  if (domesticUpsertRows.length > 0) {
    const { error } = await context.supabase.from("actual_dividends").upsert(domesticUpsertRows, {
      onConflict: "external_key",
    });
    if (error) {
      throw error;
    }
  }

  return {
    importedCount: domesticUpsertRows.length,
    importedTickers: Array.from(
      new Set(
        domesticUpsertRows
          .map((row) => context.assets.find((asset) => asset.id === row.asset_id)?.ticker)
          .filter((ticker): ticker is string => Boolean(ticker)),
      ),
    ),
  };
}

async function syncOverseasActualDividendsForAsset(
  context: Awaited<ReturnType<typeof loadSyncContext>>,
  asset: Asset,
) {
  const exchangeCode = asset.quote_market ?? "NAS";
  const transactionRows = await fetchKisOverseasPeriodTransactions({
    startDate: context.startDate,
    endDate: context.endDate,
    exchangeCode,
    ticker: asset.ticker,
  });

  const signedTransactions = transactionRows
    .filter((row) => row.symbol === asset.ticker && row.settlementDate)
    .map((row) => ({
      date: row.settlementDate,
      exchangeRate: new Decimal(row.exchangeRate || "0"),
      shares:
        row.sideCode === "01"
          ? new Decimal(row.shares || "0").negated()
          : new Decimal(row.shares || "0"),
    }))
    .sort((left, right) => left.date.localeCompare(right.date));

  const { error: deleteError } = await context.supabase
    .from("actual_dividends")
    .delete()
    .eq("source", "kis_overseas_rights_balance")
    .eq("asset_id", asset.id);

  if (deleteError) {
    throw deleteError;
  }

  if (signedTransactions.length === 0) {
    return {
      importedCount: 0,
      importedTickers: [],
    };
  }

  const rightsStartDate = signedTransactions[0]?.date ?? context.startDate;
  const rightsRows = await fetchKisOverseasDividendRights({
    startDate: rightsStartDate,
    endDate: context.endDate,
    ticker: asset.ticker,
  });

  const overseasRowsByKey = new Map<string, {
    asset_id: string;
    paid_date: string;
    gross_amount_krw: string;
    tax_amount_krw: null;
    basis_shares: string;
    per_share_amount: string;
    per_share_currency: string;
    base_date: string;
    local_record_date: string | null;
    applied_fx_rate: string;
    memo: string;
    source: "kis_overseas_rights_balance";
    external_key: string;
    imported_at: string;
    updated_at: string;
  }>();

  for (const row of rightsRows) {
    if (row.status !== "Y") {
      continue;
    }

    const balanceDate = row.localRecordDate || row.baseDate;
    if (!balanceDate) {
      continue;
    }

    const quantity = signedTransactions.reduce((acc, transaction) => {
      if (transaction.date <= balanceDate) {
        return acc.plus(transaction.shares);
      }
      return acc;
    }, new Decimal(0));
    const perShareAmount = new Decimal(row.perShareAmount || "0");
    if (quantity.lte(0) || perShareAmount.lte(0)) {
      continue;
    }

    const grossAmountForeign = quantity.mul(perShareAmount);
    const fxRate = signedTransactions.reduce((selected, transaction) => {
      if (transaction.date <= balanceDate && transaction.exchangeRate.gt(0)) {
        return transaction.exchangeRate;
      }
      return selected;
    }, context.fallbackUsdKrw);
    const grossAmountKrw = grossAmountForeign.mul(fxRate).toDecimalPlaces(2, Decimal.ROUND_HALF_UP);
    const externalKey = buildOverseasExternalKey({
      assetId: asset.id,
      paidDate: row.baseDate || balanceDate,
      baseDate: balanceDate,
    });

    overseasRowsByKey.set(externalKey, {
      asset_id: asset.id,
      paid_date: row.baseDate || balanceDate,
      gross_amount_krw: grossAmountKrw.toFixed(2),
      tax_amount_krw: null,
      basis_shares: quantity.toFixed(8),
      per_share_amount: perShareAmount.toFixed(8),
      per_share_currency: row.currency,
      base_date: row.baseDate || balanceDate,
      local_record_date: row.localRecordDate || null,
      applied_fx_rate: fxRate.toDecimalPlaces(4, Decimal.ROUND_HALF_UP).toFixed(4),
      memo: `KIS 해외 권리조회 자동 동기화 · ${row.name} · 기준수량 ${quantity.toFixed(8)}주 · 주당 ${perShareAmount.toFixed(5)} ${row.currency}`,
      source: "kis_overseas_rights_balance" as const,
      external_key: externalKey,
      imported_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
  }

  const upsertRows = Array.from(overseasRowsByKey.values());
  if (upsertRows.length > 0) {
    const { error } = await context.supabase.from("actual_dividends").upsert(upsertRows, {
      onConflict: "external_key",
    });
    if (error) {
      throw error;
    }
  }

  return {
    importedCount: upsertRows.length,
    importedTickers: upsertRows.length > 0 ? [asset.ticker] : [],
  };
}

export async function syncActualDividendsBatch(cursor = 0) {
  const context = await loadSyncContext();
  const overseasAssets = getOverseasAssets(context.assets);
  const totalSteps = overseasAssets.length + 1;

  if (cursor < 0 || cursor >= totalSteps) {
    throw new Error("유효하지 않은 배당 동기화 단계입니다.");
  }

  if (cursor === 0) {
    const result = await syncDomesticActualDividends(context);
    return {
      ...result,
      currentStep: 1,
      totalSteps,
      completed: totalSteps === 1,
      nextCursor: totalSteps === 1 ? null : 1,
      stepLabel: "국내 배당 권리현황 동기화",
      note: "국내는 KIS 권리현황, 해외는 종목별 배치 동기화로 나누어 실제 배당을 반영합니다.",
    };
  }

  const asset = overseasAssets[cursor - 1];
  const result = await syncOverseasActualDividendsForAsset(context, asset);
  const nextCursor = cursor + 1 < totalSteps ? cursor + 1 : null;

  return {
    ...result,
    currentStep: cursor + 1,
    totalSteps,
    completed: nextCursor === null,
    nextCursor,
    stepLabel: `${asset.ticker} 해외 배당 동기화`,
    note: `${asset.ticker} 기준일 보유수량과 환율을 반영해 실제 배당 기록을 갱신했습니다.`,
  };
}

export async function syncActualDividendsFromKis() {
  let cursor: number | null = 0;
  let importedCount = 0;
  const importedTickers = new Set<string>();
  let totalSteps = 1;

  while (cursor !== null) {
    const result = await syncActualDividendsBatch(cursor);
    importedCount += result.importedCount;
    totalSteps = result.totalSteps;
    result.importedTickers.forEach((ticker) => importedTickers.add(ticker));
    cursor = result.nextCursor;
  }

  return {
    importedCount,
    totalSteps,
    completed: true,
    importedTickers: Array.from(importedTickers),
    note: "국내는 KIS 권리현황, 해외는 종목별 배치 동기화로 실제 배당을 반영했습니다.",
  };
}
