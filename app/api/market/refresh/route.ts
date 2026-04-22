import { NextResponse } from "next/server";
import { refreshMarketData } from "@/lib/market/sync";

export async function POST() {
  try {
    const result = await refreshMarketData();
    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "market refresh failed";
    return NextResponse.json({ message }, { status: 500 });
  }
}
