import { NextResponse } from "next/server";
import { syncActualDividendsBatch } from "@/lib/dividends/sync";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  try {
    let cursor = 0;

    try {
      const body = (await request.json()) as { cursor?: number };
      if (typeof body.cursor === "number" && Number.isInteger(body.cursor)) {
        cursor = body.cursor;
      }
    } catch {
      cursor = 0;
    }

    const result = await syncActualDividendsBatch(cursor);
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
