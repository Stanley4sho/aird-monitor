import { useEffect, useState } from "react";
import { RdmHistoryChart } from "./charts/RdmHistoryChart";
import { DataTransparency } from "./components/DataTransparency";
import { Interpretation } from "./components/Interpretation";
import { ScoreHero } from "./components/ScoreHero";
import { SubscoreCard } from "./components/SubscoreCard";
import { Warnings } from "./components/Warnings";
import { loadDashboardData } from "./utils/data";
import type { HistoryData, LatestData, SourceStatusData } from "./utils/types";

function App() {
  const [latest, setLatest] = useState<LatestData | null>(null);
  const [history, setHistory] = useState<HistoryData | null>(null);
  const [sourceStatus, setSourceStatus] = useState<SourceStatusData | null>(null);

  useEffect(() => {
    loadDashboardData().then(({ latest: nextLatest, history: nextHistory, sourceStatus: nextStatus }) => {
      setLatest(nextLatest);
      setHistory(nextHistory);
      setSourceStatus(nextStatus);
    });
  }, []);

  if (!latest || !history || !sourceStatus) {
    return (
      <main className="grid min-h-screen place-items-center px-4 text-center">
        <div>
          <div className="mx-auto mb-4 h-12 w-12 animate-pulse rounded-lg bg-teal-600" />
          <p className="font-medium text-slate-700">載入 AI-RDM 資料中</p>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-5 px-4 py-5 pb-[calc(2rem+env(safe-area-inset-bottom))] sm:px-6 lg:px-8">
      <ScoreHero latest={latest} />

      <section className="grid gap-4 lg:grid-cols-3">
        <SubscoreCard
          title="Supply Chain Revenue Momentum"
          score={latest.subscores.supply_chain_revenue}
          weight="45%"
          description="追蹤台灣 AI 基建供應鏈月營收 YoY、MoM 與三個月平均 YoY 加速。"
        />
        <SubscoreCard
          title="Hyperscaler Capex Momentum"
          score={latest.subscores.hyperscaler_capex}
          weight="35%"
          description="追蹤 Microsoft、Alphabet、Meta、Amazon 的資本支出動能。"
        />
        <SubscoreCard
          title="Market Confirmation Spread"
          score={latest.subscores.market_confirmation}
          weight="20%"
          description="用 AI hardware basket 相對 QQQ 的 20 個交易日報酬率當輔助確認。"
        />
      </section>

      <Warnings warnings={latest.warnings} />
      <Interpretation text={latest.interpretation_for_00988a} />

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-slate-950">趨勢圖</h2>
          <p className="mt-1 text-sm text-slate-500">AI-RDM 與三個子分數 history</p>
        </div>
        <RdmHistoryChart data={history.series} />
      </section>

      <DataTransparency latest={latest} sourceStatus={sourceStatus} />
    </main>
  );
}

export default App;
