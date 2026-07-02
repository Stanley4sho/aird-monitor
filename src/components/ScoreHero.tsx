import type { CSSProperties } from "react";
import { Activity, AlertTriangle, Clock3 } from "lucide-react";
import { formatDateTime, formatNumber, scoreColor } from "../utils/format";
import type { LatestData } from "../utils/types";

interface ScoreHeroProps {
  latest: LatestData;
}

export function ScoreHero({ latest }: ScoreHeroProps) {
  const color = scoreColor(latest.ai_rdm_score);

  return (
    <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-panel">
      <div className="grid gap-0 lg:grid-cols-[1fr_360px]">
        <div className="p-5 sm:p-7">
          <div className="mb-4 flex items-center gap-3">
            <img className="h-12 w-12 rounded-lg" src={`${import.meta.env.BASE_URL}icons/icon.svg`} alt="" />
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-teal-700">AI-RDM Monitor</p>
              <h1 className="text-2xl font-bold text-slate-950 sm:text-3xl">
                00988A AI 基建實需動能監測器
              </h1>
            </div>
          </div>

          <p className="max-w-3xl text-sm leading-6 text-slate-600 sm:text-base">
            AI Infrastructure Real-Demand Momentum Index 追蹤供應鏈營收、雲端資本支出與市場確認訊號，
            用公開免費資料判斷 AI 基建需求是否仍在擴張。
          </p>

          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
                <Activity className="h-4 w-4" />
                狀態燈
              </div>
              <p className="mt-2 text-lg font-semibold" style={{ color }}>
                {latest.status}
              </p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
                <Clock3 className="h-4 w-4" />
                更新時間
              </div>
              <p className="mt-2 text-lg font-semibold text-slate-900">{formatDateTime(latest.as_of)}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
                <AlertTriangle className="h-4 w-4" />
                資料狀態
              </div>
              <p className="mt-2 text-lg font-semibold text-slate-900">
                {latest.stale ? "部分過期" : "可用"}
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-center border-t border-slate-200 bg-gradient-to-br from-teal-50 via-white to-amber-50 p-6 lg:border-l lg:border-t-0">
          <div
            className="score-ring grid h-56 w-56 place-items-center rounded-full"
            style={{ "--score": latest.ai_rdm_score, "--ring-color": color } as CSSProperties}
          >
            <div className="grid h-36 w-36 place-items-center rounded-full bg-white text-center shadow-sm">
              <div>
                <div className="text-5xl font-bold text-slate-950">{formatNumber(latest.ai_rdm_score, 1)}</div>
                <div className="mt-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">0-100</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
