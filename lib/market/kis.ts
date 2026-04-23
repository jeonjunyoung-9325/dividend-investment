import "server-only";

import { getSupabaseServerClient } from "@/lib/supabase/server";

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
  "/uapi/overseas-stock/v1/trading/inquire-present-balance",
  "/uapi/overseas-stock/v1/trading/inquire-paymt-stdr-balance",
  "/uapi/overseas-stock/v1/trading/inquire-period-trans",
  "/uapi/domestic-stock/v1/trading/intgr-margin",
  "/uapi/etfetn/v1/quotations/inquire-price",
  "/uapi/overseas-price/v1/quotations/price",
  "/uapi/overseas-price/v1/quotations/period-rights",
]);

let tokenCache: {
  accessToken: string;
  expiresAt: number;
} | null = null;
let tokenPromise: Promise<string> | null = null;
let requestQueue: Promise<void> = Promise.resolve();
let lastRequestAt = 0;
const TOKEN_PROVIDER = "kis";
const TOKEN_REUSE_BUFFER_MS = 60_000;
const TOKEN_MIN_REISSUE_WINDOW_MS = 23 * 60 * 60 * 1000;
const KIS_MIN_REQUEST_INTERVAL_MS = 400;

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
  if (tokenCache && tokenCache.expiresAt > Date.now() + TOKEN_REUSE_BUFFER_MS) {
    return tokenCache.accessToken;
  }

  const supabase = getSupabaseServerClient();
  const { data: storedToken } = await supabase
    .from("external_api_tokens")
    .select("*")
    .eq("provider", TOKEN_PROVIDER)
    .maybeSingle();

  const storedExpiresAt = storedToken?.expires_at ? new Date(storedToken.expires_at).getTime() : 0;
  const storedCreatedAt = storedToken?.created_at ? new Date(storedToken.created_at).getTime() : 0;
  const issuedRecently = storedCreatedAt > 0 && Date.now() - storedCreatedAt < TOKEN_MIN_REISSUE_WINDOW_MS;

  if (storedToken?.access_token && (storedExpiresAt > Date.now() + TOKEN_REUSE_BUFFER_MS || issuedRecently)) {
    tokenCache = {
      accessToken: storedToken.access_token,
      expiresAt: storedExpiresAt || Date.now() + TOKEN_MIN_REISSUE_WINDOW_MS,
    };
    return storedToken.access_token;
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
    const expiresAt = Date.now() + expiresIn * 1000;
    tokenCache = {
      accessToken: json.access_token,
      expiresAt,
    };

    const { error } = await supabase.from("external_api_tokens").upsert(
      {
        provider: TOKEN_PROVIDER,
        access_token: json.access_token,
        expires_at: new Date(expiresAt).toISOString(),
      },
      { onConflict: "provider" },
    );

    if (error) {
      throw error;
    }

    return tokenCache.accessToken;
  })();

  try {
    return await tokenPromise;
  } finally {
    tokenPromise = null;
  }
}

async function clearStoredAccessToken() {
  tokenCache = null;
}

async function kisGet(
  params: {
  path: string;
  trId: string;
  searchParams?: Record<string, string>;
  trCont?: string;
},
  attempt = 0,
): Promise<KisJson> {
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
    const elapsed = Date.now() - lastRequestAt;
    if (elapsed < KIS_MIN_REQUEST_INTERVAL_MS) {
      await new Promise((resolve) => setTimeout(resolve, KIS_MIN_REQUEST_INTERVAL_MS - elapsed));
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
      const errorCode = String(json.error_code ?? "");
      const errorDescription = String(json.error_description ?? json.msg1 ?? "");
      const tokenError =
        errorCode.includes("TOKEN") ||
        errorDescription.includes("접근토큰") ||
        errorDescription.toLowerCase().includes("token");

      if (tokenError && attempt === 0) {
        const supabase = getSupabaseServerClient();
        const { data: storedToken } = await supabase
          .from("external_api_tokens")
          .select("created_at, expires_at")
          .eq("provider", TOKEN_PROVIDER)
          .maybeSingle();

        const storedCreatedAt = storedToken?.created_at ? new Date(storedToken.created_at).getTime() : 0;
        const reissueAllowed =
          storedCreatedAt === 0 || Date.now() - storedCreatedAt >= TOKEN_MIN_REISSUE_WINDOW_MS;

        await clearStoredAccessToken();

        if (reissueAllowed) {
          await supabase.from("external_api_tokens").delete().eq("provider", TOKEN_PROVIDER);
          return kisGet(params, 1);
        }
      }

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

export async function fetchKisOverseasDividendRights(params: {
  startDate: string;
  endDate: string;
  ticker?: string;
}) {
  const config = getKisConfig();
  if (!config) {
    return [];
  }

  const results: KisJson[] = [];
  let nextKey = "";
  let nextFilter = "";

  for (let page = 0; page < 10; page += 1) {
    const json = await kisGet({
      path: "/uapi/overseas-price/v1/quotations/period-rights",
      trId: "CTRGT011R",
      trCont: page === 0 ? "" : "N",
      searchParams: {
        RGHT_TYPE_CD: "03",
        INQR_DVSN_CD: "02",
        INQR_STRT_DT: params.startDate,
        INQR_END_DT: params.endDate,
        PDNO: params.ticker ?? "",
        PRDT_TYPE_CD: "",
        CTX_AREA_NK50: nextKey,
        CTX_AREA_FK50: nextFilter,
      },
    });

    results.push(...asArray(json.output));

    nextKey = String(json.ctx_area_nk50 ?? "").trim();
    nextFilter = String(json.ctx_area_fk50 ?? "").trim();

    if (!nextKey) {
      break;
    }
  }

  return results
    .map((row) => {
      const amountCandidates = [
        { currency: String(row.crcy_cd2 ?? row.crcy_cd ?? "USD"), amount: String(row.stkp_dvdn_frcr_amt2 ?? "") },
        { currency: String(row.crcy_cd3 ?? row.crcy_cd ?? "USD"), amount: String(row.stkp_dvdn_frcr_amt3 ?? "") },
        { currency: String(row.crcy_cd4 ?? row.crcy_cd ?? "USD"), amount: String(row.stkp_dvdn_frcr_amt4 ?? "") },
        { currency: String(row.crcy_cd ?? "USD"), amount: String(row.alct_frcr_unpr ?? "") },
      ];
      const amountRow = amountCandidates.find((candidate) => candidate.amount && candidate.amount !== "0" && candidate.amount !== "0.00000");

      return {
        ticker: String(row.pdno ?? ""),
        name: String(row.prdt_name ?? ""),
        baseDate: String(row.bass_dt ?? ""),
        localRecordDate: String(row.acpl_bass_dt ?? ""),
        status: String(row.dfnt_yn ?? ""),
        perShareAmount: amountRow?.amount ?? "0",
        currency: amountRow?.currency ?? String(row.crcy_cd ?? "USD"),
        rightTypeCode: String(row.rght_type_cd ?? ""),
      };
    })
    .filter((row) => row.ticker && Number(row.perShareAmount || 0) > 0);
}

export async function fetchKisOverseasPeriodTransactions(params: {
  startDate: string;
  endDate: string;
  exchangeCode: string;
  ticker?: string;
}) {
  const config = getKisConfig();
  if (!config) {
    return [];
  }

  const results: KisJson[] = [];
  let nextKey = "";
  let nextFilter = "";

  for (let page = 0; page < 10; page += 1) {
    const json = await kisGet({
      path: "/uapi/overseas-stock/v1/trading/inquire-period-trans",
      trId: "CTOS4001R",
      trCont: page === 0 ? "" : "N",
      searchParams: {
        CANO: config.accountNo,
        ACNT_PRDT_CD: config.accountProductCode,
        ERLM_STRT_DT: params.startDate,
        ERLM_END_DT: params.endDate,
        OVRS_EXCG_CD: params.exchangeCode,
        PDNO: params.ticker ?? "",
        SLL_BUY_DVSN_CD: "00",
        LOAN_DVSN_CD: "",
        CTX_AREA_NK100: nextKey,
        CTX_AREA_FK100: nextFilter,
      },
    });

    results.push(...asArray(json.output1));

    nextKey = String(json.ctx_area_nk100 ?? "").trim();
    nextFilter = String(json.ctx_area_fk100 ?? "").trim();

    if (!nextKey) {
      break;
    }
  }

  return results.map((row) => ({
    symbol: String(row.pdno ?? ""),
    name: String(row.prdt_name ?? ""),
    tradeDate: String(row.trad_dt ?? ""),
    settlementDate: String(row.sttl_dt ?? ""),
    sideCode: String(row.sll_buy_dvsn_cd ?? ""),
    sideName: String(row.sll_buy_dvsn_name ?? ""),
    shares: String(row.amt_unit_ccld_qty ?? row.ccld_qty ?? "0"),
    currency: String(row.crcy_cd ?? "USD"),
    exchangeRate: String(row.erlm_exrt ?? "0"),
    securityType: String(row.loan_dvsn_name ?? ""),
  }));
}

export async function fetchKisOverseasBalances() {
  const config = getKisConfig();
  if (!config) {
    return [];
  }

  const json = await kisGet({
    path: "/uapi/overseas-stock/v1/trading/inquire-present-balance",
    trId: config.env === "real" ? "CTRP6504R" : "VTRP6504R",
    searchParams: {
      CANO: config.accountNo,
      ACNT_PRDT_CD: config.accountProductCode,
      WCRC_FRCR_DVSN_CD: "02",
      NATN_CD: "000",
      TR_MKET_CD: "00",
      INQR_DVSN_CD: "00",
    },
  });

  return asArray(json.output1).map((row) => ({
    symbol: String(row.pdno ?? ""),
    name: String(row.prdt_name ?? ""),
    shares: String(row.cblc_qty13 ?? row.ccld_qty_smtl1 ?? "0"),
    averagePrice: String(row.avg_unpr3 ?? "0"),
    currentPrice: String(row.ovrs_now_pric1 ?? "0"),
    evaluationAmount: String(row.frcr_evlu_amt2 ?? "0"),
    market: "US" as const,
    currency: String(row.buy_crcy_cd ?? "USD"),
    quoteMarket: String(row.item_lnkg_excg_cd ?? row.ovrs_excg_cd ?? ""),
    exchangeRate: String(row.bass_exrt ?? "0"),
    securityType: String(row.scts_dvsn_name ?? ""),
  }));
}
