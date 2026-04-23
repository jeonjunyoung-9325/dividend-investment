import "server-only";

import {
  fetchKisDomesticBalances,
  fetchKisDomesticEtfQuote,
  fetchKisOverseasBalances,
  fetchKisOverseasQuote,
  fetchKisUsdKrwRate,
  isKisConfigured,
} from "@/lib/market/kis";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import { Asset } from "@/types";

function assetKey(asset: Asset) {
  return asset.quote_symbol || asset.ticker;
}

export async function refreshMarketData() {
  if (!isKisConfigured()) {
    throw new Error("KIS 환경변수가 설정되지 않았습니다.");
  }

  const supabase = getSupabaseServerClient();
  const { data: assetsData, error } = await supabase.from("assets").select("*").order("display_order");
  if (error) {
    throw error;
  }

  const assets = (assetsData ?? []) as Asset[];
  const now = new Date().toISOString();
  const quoteRows: Array<{
    asset_id: string;
    price: string;
    currency: string;
    provider: string;
    fetched_at: string;
    is_stale: boolean;
  }> = [];

  const [domesticBalances, overseasBalances] = await Promise.all([
    fetchKisDomesticBalances(),
    fetchKisOverseasBalances(),
  ]);

  const balanceQuoteMap = new Map<string, { price: string; currency: string; provider: string }>();

  domesticBalances.forEach((row) => {
    if (row.symbol) {
      balanceQuoteMap.set(row.symbol, {
        price: row.currentPrice,
        currency: row.currency,
        provider: "kis-balance",
      });
    }
  });

  overseasBalances.forEach((row) => {
    if (row.symbol) {
      balanceQuoteMap.set(row.symbol, {
        price: row.currentPrice,
        currency: row.currency,
        provider: "kis-balance",
      });
    }
  });

  await Promise.all(
    assets.map(async (asset) => {
      const key = assetKey(asset);
      const balanceQuote = key ? balanceQuoteMap.get(key) : null;

      if (balanceQuote) {
        quoteRows.push({
          asset_id: asset.id,
          price: balanceQuote.price,
          currency: balanceQuote.currency,
          provider: balanceQuote.provider,
          fetched_at: now,
          is_stale: false,
        });
        return;
      }

      if (asset.market === "KR" && asset.quote_symbol) {
        const quote = await fetchKisDomesticEtfQuote(asset.quote_symbol, asset.quote_market ?? "J");
        quoteRows.push({
          asset_id: asset.id,
          price: quote.price,
          currency: quote.currency,
          provider: quote.provider,
          fetched_at: now,
          is_stale: false,
        });
        return;
      }

      if (asset.market === "US" && asset.quote_symbol && asset.quote_market) {
        const quote = await fetchKisOverseasQuote(asset.quote_symbol, asset.quote_market);
        quoteRows.push({
          asset_id: asset.id,
          price: quote.price,
          currency: quote.currency,
          provider: quote.provider,
          fetched_at: now,
          is_stale: false,
        });
      }
    }),
  );

  if (quoteRows.length) {
    const { error: quoteError } = await supabase.from("market_quotes").upsert(quoteRows, {
      onConflict: "asset_id",
    });
    if (quoteError) {
      throw quoteError;
    }
  }

  const fxRate = await fetchKisUsdKrwRate().catch(() => null);
  if (!fxRate) {
    throw new Error("한국투자 Open API에서 USD/KRW 환율을 가져오지 못했습니다.");
  }

  const { error: fxError } = await supabase.from("fx_rates").upsert(
    {
      pair: fxRate.pair,
      rate: fxRate.rate,
      provider: fxRate.provider,
      fetched_at: now,
      is_stale: false,
    },
    { onConflict: "pair" },
  );
  if (fxError) {
    throw fxError;
  }

  return {
    quotesRefreshed: quoteRows.length,
    fxProvider: fxRate.provider,
    kisConfigured: true,
  };
}

export async function syncBrokerageHoldings() {
  if (!isKisConfigured()) {
    return {
      holdingsUpdated: 0,
      skipped: true,
      reason: "KIS 환경변수가 설정되지 않았습니다.",
    };
  }

  const supabase = getSupabaseServerClient();
  const { data: assetsData, error } = await supabase.from("assets").select("*");
  if (error) {
    throw error;
  }

  const assets = (assetsData ?? []) as Asset[];
  const domesticAssets = new Map(assets.filter((asset) => asset.market === "KR").map((asset) => [asset.quote_symbol, asset]));
  const overseasAssets = new Map(assets.filter((asset) => asset.market === "US").map((asset) => [asset.ticker, asset]));
  const now = new Date().toISOString();

  const [domesticBalances, overseasBalances] = await Promise.all([
    fetchKisDomesticBalances(),
    fetchKisOverseasBalances(),
  ]);

  const holdingRows: Array<{
    asset_id: string;
    shares: string;
    average_cost_krw: string | null;
    synced_shares: string;
    synced_average_cost_krw: string | null;
    synced_value_krw: string | null;
    last_synced_at: string;
    updated_at: string;
  }> = [];

  domesticBalances.forEach((row) => {
    const asset = domesticAssets.get(row.symbol);
    if (!asset) {
      return;
    }

    holdingRows.push({
      asset_id: asset.id,
      shares: row.shares,
      average_cost_krw: row.averagePrice,
      synced_shares: row.shares,
      synced_average_cost_krw: row.averagePrice,
      synced_value_krw: row.evaluationAmount,
      last_synced_at: now,
      updated_at: now,
    });
  });

  const liveRate = await fetchKisUsdKrwRate().catch(() => null);
  const { data: fxData } = await supabase.from("fx_rates").select("*").eq("pair", "USD/KRW").maybeSingle();
  const usdKrw = Number(liveRate?.rate ?? fxData?.rate ?? 1365.5);

  overseasBalances.forEach((row) => {
    const asset = overseasAssets.get(row.symbol);
    if (!asset) {
      return;
    }

    const appliedRate = Number(row.exchangeRate || 0) > 0 ? Number(row.exchangeRate) : usdKrw;
    const averageCostKrw = String(Number(row.averagePrice || 0) * appliedRate);
    const evaluationAmountKrw = String(Number(row.evaluationAmount || 0) * appliedRate);
    holdingRows.push({
      asset_id: asset.id,
      shares: row.shares,
      average_cost_krw: averageCostKrw,
      synced_shares: row.shares,
      synced_average_cost_krw: averageCostKrw,
      synced_value_krw: evaluationAmountKrw,
      last_synced_at: now,
      updated_at: now,
    });
  });

  if (holdingRows.length) {
    const dedupedHoldingRows = Array.from(
      new Map(holdingRows.map((row) => [row.asset_id, row])).values(),
    );

    const { error: holdingsError } = await supabase.from("holdings").upsert(dedupedHoldingRows, {
      onConflict: "asset_id",
    });
    if (holdingsError) {
      throw holdingsError;
    }
  }

  return {
    holdingsUpdated: Array.from(new Map(holdingRows.map((row) => [row.asset_id, row])).values()).length,
    skipped: false,
  };
}
