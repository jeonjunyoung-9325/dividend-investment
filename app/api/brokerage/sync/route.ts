import { NextResponse } from "next/server";
import { syncBrokerageHoldings } from "@/lib/market/sync";

export async function POST() {
  try {
    const result = await syncBrokerageHoldings();
    return NextResponse.json(result);
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
