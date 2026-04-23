import "server-only";

type KisEnv = "real" | "demo";

interface KisConfig {
  appKey: string;
  appSecret: string;
  baseUrl: string;
  accountNo: string;
  accountProductCode: string;
  env: KisEnv;
}

type KisJson = Record<string, unknown>;

const READ_ONLY_KIS_PATHS = new Set([
  "/uapi/domestic-stock/v1/trading/inquire-balance",
  "/uapi/domestic-stock/v1/trading/period-rights",
  "/uapi/overseas-stock/v1/trading/inquire-balance",
  "/uapi/domestic-stock/v1/trading/intgr-margin",
  "/uapi/etfetn/v1/quotations/inquire-price",
  "/uapi/overseas-price/v1/quotations/price",
]);

let tokenCache: {
  accessToken: string;
  expiresAt: number;
} | null = null;
let tokenPromise: Promise<string> | null = null;
let requestQueue: Promise<void> = Promise.resolve();
let lastRequestAt = 0;

function getKisConfig(): KisConfig | null {
  const appKey = process.env.KIS_APP_KEY;
  const appSecret = process.env.KIS_APP_SECRET;
  const accountNo = process.env.KIS_ACCOUNT_NO;
  const accountProductCode = process.env.KIS_ACCOUNT_PRODUCT_CODE;

  if (!appKey || !appSecret || !accountNo || !accountProductCode) {
    return null;
  }

  return {
    appKey,
    appSecret,
    accountNo,
    accountProductCode,
    baseUrl: process.env.KIS_BASE_URL ?? "https://openapi.koreainvestment.com:9443",
    env: process.env.KIS_ENV === "demo" ? "demo" : "real",
  };
}

export function isKisConfigured() {
  return Boolean(getKisConfig());
}

function assertReadOnlyPath(path: string) {
  if (!READ_ONLY_KIS_PATHS.has(path)) {
    throw new Error(`허용되지 않은 KIS 경로입니다. 이 앱은 조회 전용 API만 사용합니다: ${path}`);
  }
}

async function getAccessToken(config: KisConfig) {
  if (tokenCache && tokenCache.expiresAt > Date.now() + 60_000) {
    return tokenCache.accessToken;
  }

  if (tokenPromise) {
    return tokenPromise;
  }

  tokenPromise = (async () => {
    const response = await fetch(`${config.baseUrl}/oauth2/tokenP`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify({
        grant_type: "client_credentials",
        appkey: config.appKey,
        appsecret: config.appSecret,
      }),
      cache: "no-store",
    });

    const json = (await response.json()) as KisJson;
    if (!response.ok || typeof json.access_token !== "string") {
      throw new Error(`KIS access token 발급에 실패했습니다: ${JSON.stringify(json)}`);
    }

    const expiresIn = Number(json.expires_in ?? 3600);
    tokenCache = {
      accessToken: json.access_token,
      expiresAt: Date.now() + expiresIn * 1000,
    };

    return tokenCache.accessToken;
  })();

  try {
    return await tokenPromise;
  } finally {
    tokenPromise = null;
  }
}

async function kisGet(params: {
  path: string;
  trId: string;
  searchParams?: Record<string, string>;
  trCont?: string;
}) {
  const config = getKisConfig();
  if (!config) {
    throw new Error("KIS 환경변수가 설정되지 않았습니다.");
  }

  assertReadOnlyPath(params.path);

  const accessToken = await getAccessToken(config);
  const url = new URL(`${config.baseUrl}${params.path}`);

  Object.entries(params.searchParams ?? {}).forEach(([key, value]) => {
    url.searchParams.set(key, value);
  });

  const scheduled = requestQueue.then(async () => {
    const minimumInterval = 1100;
    const elapsed = Date.now() - lastRequestAt;
    if (elapsed < minimumInterval) {
      await new Promise((resolve) => setTimeout(resolve, minimumInterval - elapsed));
    }

    const response = await fetch(url, {
      method: "GET",
      headers: {
        "content-type": "application/json; charset=utf-8",
        authorization: `Bearer ${accessToken}`,
        appkey: config.appKey,
        appsecret: config.appSecret,
        tr_id: params.trId,
        custtype: "P",
        tr_cont: params.trCont ?? "",
      },
      cache: "no-store",
    });

    lastRequestAt = Date.now();

    const json = (await response.json()) as KisJson;
    if (!response.ok) {
      throw new Error(`KIS 요청 실패(${params.path}): ${JSON.stringify(json)}`);
    }

    return json;
  });

  requestQueue = scheduled.then(
    () => undefined,
    () => undefined,
  );

  return scheduled;
}

function asArray(value: unknown) {
  if (Array.isArray(value)) {
    return value as KisJson[];
  }

  if (value && typeof value === "object") {
    return [value as KisJson];
  }

  return [] as KisJson[];
}

export async function fetchKisUsdKrwRate() {
  const config = getKisConfig();
  if (!config) {
    return null;
  }

  const json = await kisGet({
    path: "/uapi/domestic-stock/v1/trading/intgr-margin",
    trId: "TTTC0869R",
    searchParams: {
      CANO: config.accountNo,
      ACNT_PRDT_CD: config.accountProductCode,
      CMA_EVLU_AMT_ICLD_YN: "N",
      WCRC_FRCR_DVSN_CD: "01",
      FWEX_CTRT_FRCR_DVSN_CD: "01",
    },
  });

  const output = (json.output ?? {}) as KisJson;
  const rate = output.usd_frst_bltn_exrt;

  return typeof rate === "string" || typeof rate === "number"
    ? {
        pair: "USD/KRW",
        rate: String(rate),
        provider: "kis",
      }
    : null;
}

export async function fetchKisDomesticEtfQuote(symbol: string, market = "J") {
  const json = await kisGet({
    path: "/uapi/etfetn/v1/quotations/inquire-price",
    trId: "FHPST02400000",
    searchParams: {
      FID_COND_MRKT_DIV_CODE: market,
      FID_INPUT_ISCD: symbol,
    },
  });

  const output = (json.output ?? {}) as KisJson;
  const price = output.stck_prpr;

  if (typeof price !== "string" && typeof price !== "number") {
    throw new Error(`국내 ETF 현재가를 찾을 수 없습니다: ${symbol}`);
  }

  return {
    symbol,
    price: String(price),
    currency: "KRW",
    provider: "kis",
  };
}

export async function fetchKisOverseasQuote(symbol: string, market: string) {
  const json = await kisGet({
    path: "/uapi/overseas-price/v1/quotations/price",
    trId: "HHDFS00000300",
    searchParams: {
      AUTH: "",
      EXCD: market,
      SYMB: symbol,
    },
  });

  const output = (json.output ?? {}) as KisJson;
  const price = output.last;

  if (typeof price !== "string" && typeof price !== "number") {
    throw new Error(`해외 현재가를 찾을 수 없습니다: ${market} ${symbol}`);
  }

  return {
    symbol,
    price: String(price),
    currency: "USD",
    provider: "kis",
  };
}

export async function fetchKisDomesticBalances() {
  const config = getKisConfig();
  if (!config) {
    return [];
  }

  const json = await kisGet({
    path: "/uapi/domestic-stock/v1/trading/inquire-balance",
    trId: config.env === "real" ? "TTTC8434R" : "VTTC8434R",
    searchParams: {
      CANO: config.accountNo,
      ACNT_PRDT_CD: config.accountProductCode,
      AFHR_FLPR_YN: "N",
      OFL_YN: "",
      INQR_DVSN: "01",
      UNPR_DVSN: "01",
      FUND_STTL_ICLD_YN: "N",
      FNCG_AMT_AUTO_RDPT_YN: "N",
      PRCS_DVSN: "00",
      CTX_AREA_FK100: "",
      CTX_AREA_NK100: "",
    },
  });

  return asArray(json.output1).map((row) => ({
    symbol: String(row.pdno ?? ""),
    name: String(row.prdt_name ?? ""),
    shares: String(row.hldg_qty ?? "0"),
    averagePrice: String(row.pchs_avg_pric ?? "0"),
    currentPrice: String(row.prpr ?? "0"),
    evaluationAmount: String(row.evlu_amt ?? "0"),
    market: "KR" as const,
    currency: "KRW",
  }));
}

export async function fetchKisDomesticActualDividends(params: {
  startDate: string;
  endDate: string;
}) {
  const config = getKisConfig();
  if (!config) {
    return [];
  }

  const json = await kisGet({
    path: "/uapi/domestic-stock/v1/trading/period-rights",
    trId: "CTRGA011R",
    searchParams: {
      INQR_DVSN: "03",
      CANO: config.accountNo,
      ACNT_PRDT_CD: config.accountProductCode,
      INQR_STRT_DT: params.startDate,
      INQR_END_DT: params.endDate,
      CUST_RNCNO25: "",
      HMID: "",
      RGHT_TYPE_CD: "03",
      PDNO: "",
      PRDT_TYPE_CD: "",
      CTX_AREA_NK100: "",
      CTX_AREA_FK100: "",
    },
  });

  return asArray(json.output)
    .map((row) => ({
      symbol: String(row.shtn_pdno ?? row.pdno ?? ""),
      name: String(row.prdt_name ?? ""),
      paidDate: String(row.cash_dfrm_dt ?? ""),
      grossAmountKrw: String(row.last_alct_amt ?? "0"),
      taxAmountKrw: String(row.tax_amt ?? "0"),
      allocatedQuantity: String(row.last_alct_qty ?? row.cblc_qty ?? "0"),
      rightTypeCode: String(row.rght_type_cd ?? ""),
    }))
    .filter((row) => row.symbol && row.paidDate && row.grossAmountKrw !== "0");
}

export async function fetchKisOverseasBalances() {
  const config = getKisConfig();
  if (!config) {
    return [];
  }

  const exchangeInputs = [
    { exchange: "NASD", quoteMarket: "NAS", currency: "USD" },
    { exchange: "NYSE", quoteMarket: "NYS", currency: "USD" },
    { exchange: "AMEX", quoteMarket: "AMS", currency: "USD" },
  ];

  const results = [];

  for (const entry of exchangeInputs) {
    try {
      const json = await kisGet({
        path: "/uapi/overseas-stock/v1/trading/inquire-balance",
        trId: config.env === "real" ? "TTTS3012R" : "VTTS3012R",
        searchParams: {
          CANO: config.accountNo,
          ACNT_PRDT_CD: config.accountProductCode,
          OVRS_EXCG_CD: entry.exchange,
          TR_CRCY_CD: entry.currency,
          CTX_AREA_FK200: "",
          CTX_AREA_NK200: "",
        },
      });

      results.push(
        ...asArray(json.output1).map((row) => ({
        symbol: String(row.ovrs_pdno ?? ""),
        shares: String(row.ovrs_cblc_qty ?? "0"),
        averagePrice: String(row.pchs_avg_pric ?? "0"),
        currentPrice: String(row.now_pric2 ?? "0"),
        evaluationAmount: String(row.ovrs_stck_evlu_amt ?? "0"),
        market: "US" as const,
        currency: String(row.tr_crcy_cd ?? entry.currency),
        quoteMarket: String(row.ovrs_excg_cd ?? entry.quoteMarket),
        })),
      );
    } catch {
      continue;
    }
  }

  return results;
}
