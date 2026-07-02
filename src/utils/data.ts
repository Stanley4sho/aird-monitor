import type { HistoryData, LatestData, SourceStatusData } from "./types";

const fallbackLatest: LatestData = {
  as_of: new Date().toISOString(),
  ai_rdm_score: 50,
  aird_m_score: 50,
  status: "中性震盪",
  status_band: "neutral",
  subscores: {
    supply_chain_revenue: 50,
    hyperscaler_capex: 50,
    market_confirmation: 50
  },
  warnings: {
    slowdown: false,
    bubble_divergence: false
  },
  interpretation_for_00988a: "目前尚未取得最新公開資料，請先執行資料更新 workflow。",
  source_status: {
    tw_revenue: "unknown",
    sec_capex: "unknown",
    market_prices: "unknown"
  },
  stale: true,
  details: {
    supply_chain_revenue: {
      score: 50,
      median_yoy_growth_pct: null,
      yoy_positive_ratio: null,
      avg_3m_yoy_acceleration_ratio: null,
      companies: []
    },
    hyperscaler_capex: {
      score: 50,
      median_capex_yoy_growth_pct: null,
      capex_yoy_positive_ratio: null,
      positive_keyword_ratio: null,
      companies: []
    },
    market_confirmation: {
      score: 50,
      basket_return_20d_pct: null,
      benchmark_return_20d_pct: null,
      spread_pct: null,
      benchmark: null,
      tickers: []
    }
  },
  disclaimer: "本網站僅供研究與教育用途，不是投資建議。"
};

const fallbackHistory: HistoryData = {
  updated_at: new Date().toISOString(),
  series: [
    {
      as_of: new Date().toISOString(),
      ai_rdm_score: 50,
      supply_chain_revenue: 50,
      hyperscaler_capex: 50,
      market_confirmation: 50
    }
  ]
};

const fallbackSourceStatus: SourceStatusData = {
  generated_at: new Date().toISOString(),
  stale: true,
  sources: {}
};

async function fetchJson<T>(path: string, fallback: T): Promise<T> {
  const response = await fetch(`${import.meta.env.BASE_URL}${path}`, {
    cache: "no-cache"
  });
  if (!response.ok) return fallback;
  return (await response.json()) as T;
}

export async function loadDashboardData(): Promise<{
  latest: LatestData;
  history: HistoryData;
  sourceStatus: SourceStatusData;
}> {
  const [latest, history, sourceStatus] = await Promise.all([
    fetchJson("data/latest.json", fallbackLatest).catch(() => fallbackLatest),
    fetchJson("data/history.json", fallbackHistory).catch(() => fallbackHistory),
    fetchJson("data/source_status.json", fallbackSourceStatus).catch(() => fallbackSourceStatus)
  ]);

  return { latest, history, sourceStatus };
}
