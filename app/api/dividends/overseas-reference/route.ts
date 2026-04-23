import { fetchKisOverseasDividendRights, isKisConfigured } from "@/lib/market/kis";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";
import { Asset } from "@/types";

export async function POST() {
  try {
    if (!isKisConfigured()) {
      throw new Error("KIS 환경변수가 설정되지 않았습니다.");
    }

    const supabase = getSupabaseServerClient();
    const [{ data: holdingsData, error: holdingsError }, { data: fxData, error: fxError }, { data: assetsData, error: assetsError }] =
      await Promise.all([
        supabase.from("holdings").select("asset_id, synced_shares").not("synced_shares", "is", null).gt("synced_shares", 0),
        supabase.from("fx_rates").select("*").eq("pair", "USD/KRW").order("fetched_at", { ascending: false }).limit(1).maybeSingle(),
        supabase.from("assets").select("*").eq("market", "US"),
      ]);

    if (holdingsError) throw holdingsError;
    if (fxError) throw fxError;
    if (assetsError) throw assetsError;

    const assets = (assetsData ?? []) as Asset[];
    const assetMap = new Map(assets.map((asset) => [asset.id, asset]));
    const heldTickers = (holdingsData ?? [])
      .map((holding) => {
        const asset = assetMap.get(holding.asset_id);
        return asset
          ? {
              ticker: asset.ticker,
              name: asset.name,
              shares: String(holding.synced_shares ?? "0"),
            }
          : null;
      })
      .filter((row): row is NonNullable<typeof row> => Boolean(row));

    const year = new Date().getFullYear();
    const startDate = `${year}0101`;
    const endDate = `${year}1231`;
    const usdKrw = Number(fxData?.rate ?? 0);

    const eventArrays = await Promise.all(
      heldTickers.map((holding) =>
        fetchKisOverseasDividendRights({
          startDate,
          endDate,
          ticker: holding.ticker,
        }).then((events) => events.map((event) => ({ ...event, holding }))),
      ),
    );

    const events = eventArrays
      .flat()
      .map((event) => ({
        ticker: event.ticker,
        name: event.name || event.holding.name,
        baseDate: event.baseDate,
        localRecordDate: event.localRecordDate,
        status: event.status,
        perShareAmount: event.perShareAmount,
        currency: event.currency,
        currentShares: event.holding.shares,
        estimatedAmountKrw:
          event.currency === "USD"
            ? String(Number(event.perShareAmount) * Number(event.holding.shares) * usdKrw)
            : null,
      }))
      .sort((a, b) => new Date(b.localRecordDate || b.baseDate).getTime() - new Date(a.localRecordDate || a.baseDate).getTime());

    return NextResponse.json({
      events,
      note: "해외 KIS는 계좌별 원화 세전 실제 입금 row를 직접 주지 않아, 현재 보유 해외 종목 기준 배당 권리/예정 참고 내역을 보여줍니다. 참고 환산액은 현재 보유 수량 기준입니다.",
    });
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : typeof error === "string"
          ? error
          : JSON.stringify(error);
    return NextResponse.json({ message }, { status: 500 });
  }
}
