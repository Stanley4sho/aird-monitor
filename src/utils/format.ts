import type { SourceHealth } from "./types";

export function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "缺資料";
  return value.toLocaleString("zh-TW", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits
  });
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "缺資料";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${formatNumber(value, digits)}%`;
}

export function formatMoney(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "缺資料";
  if (Math.abs(value) >= 1_000_000_000) return `${formatNumber(value / 1_000_000_000, 1)}B`;
  if (Math.abs(value) >= 1_000_000) return `${formatNumber(value / 1_000_000, 1)}M`;
  return formatNumber(value, 0);
}

export function formatDateTime(value?: string): string {
  if (!value) return "缺資料";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Taipei"
  }).format(date);
}

export function scoreColor(score: number): string {
  if (score >= 70) return "#0f766e";
  if (score >= 55) return "#2563eb";
  if (score >= 45) return "#64748b";
  if (score >= 30) return "#d97706";
  return "#dc2626";
}

export function sourceLabel(status: SourceHealth | undefined): string {
  switch (status) {
    case "ok":
      return "正常";
    case "partial":
      return "部分成功";
    case "stale":
      return "沿用舊資料";
    case "error":
      return "失敗";
    default:
      return "未知";
  }
}

export function sourceClass(status: SourceHealth | undefined): string {
  switch (status) {
    case "ok":
      return "border-teal-200 bg-teal-50 text-teal-800";
    case "partial":
      return "border-amber-200 bg-amber-50 text-amber-800";
    case "stale":
      return "border-slate-200 bg-slate-50 text-slate-700";
    case "error":
      return "border-rose-200 bg-rose-50 text-rose-800";
    default:
      return "border-slate-200 bg-white text-slate-600";
  }
}
