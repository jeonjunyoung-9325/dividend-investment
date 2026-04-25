import { NextResponse } from "next/server";
import { syncActualDividendsBatch } from "@/lib/dividends/sync";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  try {
    let cursor: unknown = null;

    try {
      const body = (await request.json()) as { cursor?: unknown };
      if (body.cursor) {
        cursor = body.cursor;
      }
    } catch {
      cursor = null;
    }

    const result = await syncActualDividendsBatch(cursor as Parameters<typeof syncActualDividendsBatch>[0]);
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
