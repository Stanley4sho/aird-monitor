import { AlertTriangle, CheckCircle2 } from "lucide-react";
import type { WarningFlags } from "../utils/types";

interface WarningsProps {
  warnings: WarningFlags;
}

export function Warnings({ warnings }: WarningsProps) {
  const active = [
    warnings.slowdown ? "AI 基建實需放緩風險升高" : null,
    warnings.bubble_divergence ? "市場價格強，但基本面跟不上，泡沫化風險升高" : null
  ].filter(Boolean);

  if (active.length === 0) {
    return (
      <section className="rounded-lg border border-teal-200 bg-teal-50 p-4 text-teal-900">
        <div className="flex items-start gap-3">
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <h2 className="font-semibold">未觸發主要風險警示</h2>
            <p className="mt-1 text-sm leading-6 text-teal-800">仍需搭配資料透明區檢查來源是否完整與即時。</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-950">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
        <div>
          <h2 className="font-semibold">風險警示</h2>
          <ul className="mt-2 space-y-1 text-sm leading-6">
            {active.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
