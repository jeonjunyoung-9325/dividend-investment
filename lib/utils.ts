import { ClassValue, clsx } from "clsx";
import Decimal from "decimal.js";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function toDecimal(value: Decimal.Value | null | undefined) {
  if (value === null || value === undefined || value === "") {
    return new Decimal(0);
  }

  return new Decimal(value);
}

export function formatKRW(
  value: Decimal.Value,
  options?: {
    minimumFractionDigits?: number;
    maximumFractionDigits?: number;
    withSuffix?: boolean;
  },
) {
  const decimal = toDecimal(value);
  const maximumFractionDigits = options?.maximumFractionDigits ?? 0;
  const minimumFractionDigits = options?.minimumFractionDigits ?? 0;
  const suffix = options?.withSuffix ?? true ? "원" : "";

  return `${new Intl.NumberFormat("ko-KR", {
    minimumFractionDigits,
    maximumFractionDigits,
  }).format(decimal.toNumber())}${suffix}`;
}

export function formatShares(value: Decimal.Value, digits = 6) {
  const decimal = toDecimal(value);
  return new Intl.NumberFormat("ko-KR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  }).format(decimal.toNumber());
}

export function formatRelativeTimeFromNow(value: string) {
  const date = new Date(value);

  return new Intl.DateTimeFormat("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
