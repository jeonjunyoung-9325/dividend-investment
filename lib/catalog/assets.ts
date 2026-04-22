import { AssetCatalogMeta } from "@/types";

export const assetCatalog: Record<string, AssetCatalogMeta> = {
  QQQ: {
    ticker: "QQQ",
    currentPrice: "468.12",
    priceCurrency: "USD",
    metadataUpdatedAt: "2026-04-22",
  },
  VOO: {
    ticker: "VOO",
    currentPrice: "515.37",
    priceCurrency: "USD",
    metadataUpdatedAt: "2026-04-22",
  },
  JEPI: {
    ticker: "JEPI",
    currentPrice: "57.14",
    priceCurrency: "USD",
    metadataUpdatedAt: "2026-04-22",
  },
  SCHD: {
    ticker: "SCHD",
    currentPrice: "83.52",
    priceCurrency: "USD",
    metadataUpdatedAt: "2026-04-22",
  },
  O: {
    ticker: "O",
    currentPrice: "56.83",
    priceCurrency: "USD",
    metadataUpdatedAt: "2026-04-22",
  },
  SOXX: {
    ticker: "SOXX",
    currentPrice: "231.79",
    priceCurrency: "USD",
    metadataUpdatedAt: "2026-04-22",
  },
  NVDY: {
    ticker: "NVDY",
    currentPrice: "27.46",
    priceCurrency: "USD",
    metadataUpdatedAt: "2026-04-22",
  },
  IAU: {
    ticker: "IAU",
    currentPrice: "58.14",
    priceCurrency: "USD",
    metadataUpdatedAt: "2026-04-22",
  },
  "KODEX 200타겟위클리커버드콜": {
    ticker: "KODEX 200타겟위클리커버드콜",
    currentPrice: "10525",
    priceCurrency: "KRW",
    metadataUpdatedAt: "2026-04-22",
  },
  "RISE 200위클리커버드콜": {
    ticker: "RISE 200위클리커버드콜",
    currentPrice: "9980",
    priceCurrency: "KRW",
    metadataUpdatedAt: "2026-04-22",
  },
  "KODEX 미국성장커버드콜액티브": {
    ticker: "KODEX 미국성장커버드콜액티브",
    currentPrice: "12840",
    priceCurrency: "KRW",
    metadataUpdatedAt: "2026-04-22",
  },
};

export const scenarioGrowthRates = {
  conservative: "0",
  base: "0.03",
  optimistic: "0.07",
} as const;
