import { NextResponse } from "next/server";
import { syncActualDividendsBatch } from "@/lib/dividends/sync";

export const runtime = "nodejs";
export const maxDuration = 300;

export async function POST(request: Request) {
  try {
    let cursor: unknown = null;
    let startYear = 2026;

    try {
      const body = (await request.json()) as { cursor?: unknown; startYear?: number };
      if (body.cursor) {
        cursor = body.cursor;
      }
      if (typeof body.startYear === "number" && Number.isInteger(body.startYear)) {
        startYear = body.startYear;
      }
    } catch {
      cursor = null;
    }

    const result = await syncActualDividendsBatch(cursor as Parameters<typeof syncActualDividendsBatch>[0], {
      startYear,
    });
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
