import { Database, Info } from "lucide-react";
import { formatDateTime, formatMoney, formatPercent, sourceClass, sourceLabel } from "../utils/format";
import type { LatestData, SourceStatusData } from "../utils/types";
import { StatusPill } from "./StatusPill";

interface DataTransparencyProps {
  latest: LatestData;
  sourceStatus: SourceStatusData;
}

export function DataTransparency({ latest, sourceStatus }: DataTransparencyProps) {
  const sources = sourceStatus.sources ?? {};

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-2">
        <Database className="h-5 w-5 text-teal-700" />
        <h2 className="text-lg font-semibold text-slate-950">資料透明區</h2>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {Object.entries({
          tw_revenue: "台灣月營收",
          sec_capex: "SEC Capex",
          market_prices: "市場價格"
        }).map(([key, label]) => {
          const source = sources[key];
          return (
            <div key={key} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-slate-950">{label}</h3>
                  <p className="mt-1 text-xs text-slate-500">{source?.source ?? "來源尚未記錄"}</p>
                </div>
                <span
                  className={`inline-flex items-center rounded border px-2 py-1 text-xs font-medium ${sourceClass(source?.status)}`}
                >
                  {sourceLabel(source?.status)}
                </span>
              </div>
              <p className="mt-3 text-sm text-slate-600">最後更新：{formatDateTime(source?.last_updated)}</p>
              {source?.missing?.length ? (
                <p className="mt-2 text-xs leading-5 text-amber-700">Missing：{source.missing.join(", ")}</p>
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm xl:col-span-1">
          <h3 className="mb-3 font-semibold text-slate-950">供應鏈營收名單</h3>
          <div className="space-y-2">
            {latest.details.supply_chain_revenue.companies.map((company) => (
              <div key={company.ticker} className="flex items-center justify-between gap-3 border-b border-slate-100 pb-2 last:border-0">
                <div>
                  <p className="text-sm font-medium text-slate-900">
                    {company.ticker} {company.name}
                  </p>
                  <p className="text-xs text-slate-500">
                    YoY {formatPercent(company.yoy_growth_pct)} · MoM {formatPercent(company.mom_growth_pct)}
                  </p>
                </div>
                <StatusPill status={company.status} />
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm xl:col-span-1">
          <h3 className="mb-3 font-semibold text-slate-950">Hyperscaler Capex</h3>
          <div className="space-y-2">
            {latest.details.hyperscaler_capex.companies.map((company) => (
              <div key={company.ticker} className="flex items-center justify-between gap-3 border-b border-slate-100 pb-2 last:border-0">
                <div>
                  <p className="text-sm font-medium text-slate-900">
                    {company.ticker} {company.name}
                  </p>
                  <p className="text-xs text-slate-500">
                    Capex {formatMoney(company.latest_capex_usd)} · YoY {formatPercent(company.yoy_growth_pct)}
                  </p>
                </div>
                <StatusPill status={company.status} />
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm xl:col-span-1">
          <h3 className="mb-3 font-semibold text-slate-950">市場 Basket</h3>
          <div className="space-y-2">
            {latest.details.market_confirmation.tickers.map((ticker) => (
              <div key={ticker.ticker} className="flex items-center justify-between gap-3 border-b border-slate-100 pb-2 last:border-0">
                <div>
                  <p className="text-sm font-medium text-slate-900">{ticker.ticker}</p>
                  <p className="text-xs text-slate-500">
                    20D {formatPercent(ticker.return_20d_pct)} · {ticker.source ?? "source n/a"}
                  </p>
                </div>
                <StatusPill status={ticker.status} />
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-2 flex items-center gap-2">
          <Info className="h-5 w-5 text-slate-600" />
          <h3 className="font-semibold text-slate-950">公式與免責聲明</h3>
        </div>
        <div className="space-y-2 text-sm leading-6 text-slate-600">
          <p>AI-RDM = 45% × 供應鏈營收 + 35% × Hyperscaler Capex + 20% × 市場確認。</p>
          <p>供應鏈營收：40% YoY 轉正比例、30% 三個月平均 YoY 加速比例、30% median YoY 標準化。</p>
          <p>Hyperscaler Capex：50% median capex YoY 標準化、30% YoY 轉正比例、20% AI / datacenter / capacity 關鍵字。</p>
          <p>市場確認：AI hardware basket 20 個交易日報酬率減 QQQ，-10% 到 +10% 線性轉為 0 到 100 分。</p>
          <p className="font-medium text-slate-800">{latest.disclaimer}</p>
        </div>
      </div>
    </section>
  );
}
