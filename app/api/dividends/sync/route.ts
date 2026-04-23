import { NextResponse } from "next/server";
import { syncActualDividendsFromKis } from "@/lib/dividends/sync";

export async function POST() {
  try {
    const result = await syncActualDividendsFromKis();
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
