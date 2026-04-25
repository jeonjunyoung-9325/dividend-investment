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

const ACTUAL_DIVIDEND_SYNC_START_YEAR = 2026;

type DividendSyncCursor =
  | { kind: "domestic" }
  | { kind: "overseas"; assetIndex: number; year: number; month: number; openingShares: string };

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

async function loadSyncContext(startYearOverride?: number) {
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
  const currentYear = now.getFullYear();
  const startYear = Math.min(currentYear, startYearOverride ?? ACTUAL_DIVIDEND_SYNC_START_YEAR);
  const { data: fxRow } = await supabase.from("fx_rates").select("*").eq("pair", "USD/KRW").maybeSingle();

  return {
    supabase,
    assets,
    startYear,
    currentYear,
    fallbackUsdKrw: new Decimal(String(fxRow?.rate ?? "1365.5")),
  };
}

function getOverseasAssets(assets: Asset[]) {
  return assets.filter((asset) => asset.market === "US");
}

function getChunkMonthSpan(asset: Asset) {
  return asset.dividend_frequency === "quarterly" ? 3 : 1;
}

function getNextCursor(
  cursor: DividendSyncCursor,
  startYear: number,
  currentYear: number,
  overseasAssets: Asset[],
  nextOpeningShares: Decimal,
): DividendSyncCursor | null {
  if (cursor.kind === "domestic") {
    return overseasAssets.length === 0
      ? null
      : {
          kind: "overseas",
          assetIndex: 0,
          year: startYear,
          month: 1,
          openingShares: "0",
        };
  }

  const asset = overseasAssets[cursor.assetIndex];
  const monthSpan = getChunkMonthSpan(asset);
  const nextMonth = cursor.month + monthSpan;

  if (nextMonth <= 12) {
    return {
      kind: "overseas",
      assetIndex: cursor.assetIndex,
      year: cursor.year,
      month: nextMonth,
      openingShares: nextOpeningShares.toFixed(8),
    };
  }

  if (cursor.year < currentYear) {
    return {
      kind: "overseas",
      assetIndex: cursor.assetIndex,
      year: cursor.year + 1,
      month: 1,
      openingShares: nextOpeningShares.toFixed(8),
    };
  }

  if (cursor.assetIndex + 1 < overseasAssets.length) {
    return {
      kind: "overseas",
      assetIndex: cursor.assetIndex + 1,
      year: startYear,
      month: 1,
      openingShares: "0",
    };
  }

  return null;
}

function getTotalSteps(startYear: number, currentYear: number, overseasAssets: Asset[]) {
  const yearCount = currentYear - startYear + 1;
  return (
    1 +
    overseasAssets.reduce((acc, asset) => {
      const periodsPerYear = asset.dividend_frequency === "quarterly" ? 4 : 12;
      return acc + yearCount * periodsPerYear;
    }, 0)
  );
}

function getCurrentStep(cursor: DividendSyncCursor, startYear: number, currentYear: number, overseasAssets: Asset[]) {
  if (cursor.kind === "domestic") {
    return 1;
  }

  let stepsBefore = 1;

  for (let index = 0; index < cursor.assetIndex; index += 1) {
    const asset = overseasAssets[index];
    const periodsPerYear = asset.dividend_frequency === "quarterly" ? 4 : 12;
    stepsBefore += (currentYear - startYear + 1) * periodsPerYear;
  }

  const asset = overseasAssets[cursor.assetIndex];
  const periodsPerYear = asset.dividend_frequency === "quarterly" ? 4 : 12;
  const yearOffset = cursor.year - startYear;
  const monthOffset = asset.dividend_frequency === "quarterly" ? Math.floor((cursor.month - 1) / 3) : cursor.month - 1;

  return stepsBefore + yearOffset * periodsPerYear + monthOffset + 1;
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
    startDate: `${context.startYear}0101`,
    endDate: `${context.currentYear}1231`,
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

async function syncOverseasActualDividendsYear(
  context: Awaited<ReturnType<typeof loadSyncContext>>,
  asset: Asset,
  year: number,
  month: number,
  openingShares: Decimal,
) {
  const monthSpan = getChunkMonthSpan(asset);
  const endMonth = Math.min(month + monthSpan - 1, 12);
  const chunkStart = `${year}${String(month).padStart(2, "0")}01`;
  const chunkEnd = `${year}${String(endMonth).padStart(2, "0")}31`;
  const exchangeCode = asset.quote_market ?? "NAS";
  const transactionRows = await fetchKisOverseasPeriodTransactions({
    startDate: chunkStart,
    endDate: chunkEnd,
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

  const rightsRows = await fetchKisOverseasDividendRights({
    startDate: chunkStart,
    endDate: chunkEnd,
    ticker: asset.ticker,
  });

  const { error: deleteError } = await context.supabase
    .from("actual_dividends")
    .delete()
    .eq("source", "kis_overseas_rights_balance")
    .eq("asset_id", asset.id)
    .gte("paid_date", `${year}-${String(month).padStart(2, "0")}-01`)
    .lte("paid_date", `${year}-${String(endMonth).padStart(2, "0")}-31`);

  if (deleteError) {
    throw deleteError;
  }

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
    }, openingShares);

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

  const closingShares = signedTransactions.reduce((acc, transaction) => acc.plus(transaction.shares), openingShares);

  return {
    importedCount: upsertRows.length,
    importedTickers: upsertRows.length > 0 ? [asset.ticker] : [],
    closingShares,
  };
}

export async function syncActualDividendsBatch(
  cursorInput?: DividendSyncCursor | null,
  options?: { startYear?: number },
) {
  const context = await loadSyncContext(options?.startYear);
  const overseasAssets = getOverseasAssets(context.assets);
  const totalSteps = getTotalSteps(context.startYear, context.currentYear, overseasAssets);
  const cursor = cursorInput ?? ({ kind: "domestic" } satisfies DividendSyncCursor);

  if (cursor.kind === "domestic") {
    const result = await syncDomesticActualDividends(context);
    const nextCursor = getNextCursor(cursor, context.startYear, context.currentYear, overseasAssets, new Decimal(0));

    return {
      ...result,
      currentStep: getCurrentStep(cursor, context.startYear, context.currentYear, overseasAssets),
      totalSteps,
      completed: nextCursor === null,
      nextCursor,
      stepLabel: "국내 배당 권리현황 동기화",
      note: "국내 배당 권리현황을 먼저 반영했습니다.",
    };
  }

  const asset = overseasAssets[cursor.assetIndex];
  if (!asset) {
    throw new Error("유효하지 않은 해외 배당 동기화 단계입니다.");
  }

  const result = await syncOverseasActualDividendsYear(
    context,
    asset,
    cursor.year,
    cursor.month,
    new Decimal(cursor.openingShares || "0"),
  );
  const nextCursor = getNextCursor(
    cursor,
    context.startYear,
    context.currentYear,
    overseasAssets,
    result.closingShares,
  );

  return {
    importedCount: result.importedCount,
    importedTickers: result.importedTickers,
    currentStep: getCurrentStep(cursor, context.startYear, context.currentYear, overseasAssets),
    totalSteps,
    completed: nextCursor === null,
    nextCursor,
    stepLabel: `${asset.ticker} · ${cursor.year}년 ${cursor.month}월${asset.dividend_frequency === "quarterly" ? `-${Math.min(cursor.month + 2, 12)}월` : ""} 배당 동기화`,
    note: `${asset.ticker} ${cursor.year}년 ${cursor.month}월 기준 배당 내역을 반영했습니다.`,
  };
}
