export type SourceHealth = "ok" | "partial" | "error" | "stale" | "unknown";

export interface Subscores {
  supply_chain_revenue: number;
  hyperscaler_capex: number;
  market_confirmation: number;
}

export interface WarningFlags {
  slowdown: boolean;
  bubble_divergence: boolean;
}

export interface SupplyCompany {
  ticker: string;
  code: string;
  name: string;
  data_month?: string;
  yoy_growth_pct: number | null;
  mom_growth_pct: number | null;
  avg_3m_yoy_pct: number | null;
  avg_3m_yoy_accelerating: boolean | null;
  revenue_current: number | null;
  status: SourceHealth;
  note?: string;
}

export interface CapexCompany {
  ticker: string;
  name: string;
  cik: string;
  latest_quarter?: string;
  latest_capex_usd: number | null;
  yoy_growth_pct: number | null;
  qoq_growth_pct: number | null;
  positive_keyword_found: boolean | null;
  keyword_source?: string;
  status: SourceHealth;
  note?: string;
}

export interface MarketTicker {
  ticker: string;
  return_20d_pct: number | null;
  last_close: number | null;
  last_date?: string;
  source?: string;
  status: SourceHealth;
  note?: string;
}

export interface LatestData {
  as_of: string;
  ai_rdm_score: number;
  aird_m_score: number;
  status: string;
  status_band: string;
  subscores: Subscores;
  warnings: WarningFlags;
  interpretation_for_00988a: string;
  source_status: Record<string, SourceHealth>;
  stale?: boolean;
  stale_components?: string[];
  details: {
    supply_chain_revenue: {
      score: number;
      median_yoy_growth_pct: number | null;
      yoy_positive_ratio: number | null;
      avg_3m_yoy_acceleration_ratio: number | null;
      companies: SupplyCompany[];
    };
    hyperscaler_capex: {
      score: number;
      median_capex_yoy_growth_pct: number | null;
      capex_yoy_positive_ratio: number | null;
      positive_keyword_ratio: number | null;
      companies: CapexCompany[];
    };
    market_confirmation: {
      score: number;
      basket_return_20d_pct: number | null;
      benchmark_return_20d_pct: number | null;
      spread_pct: number | null;
      benchmark: MarketTicker | null;
      tickers: MarketTicker[];
    };
  };
  formulas?: Record<string, string>;
  disclaimer: string;
}

export interface HistoryPoint {
  as_of: string;
  ai_rdm_score: number;
  supply_chain_revenue: number;
  hyperscaler_capex: number;
  market_confirmation: number;
}

export interface HistoryData {
  updated_at: string;
  series: HistoryPoint[];
  tw_revenue_observations?: Record<string, unknown[]>;
}

export interface SourceDetail {
  status: SourceHealth;
  last_updated?: string;
  source?: string;
  success_count?: number;
  missing?: string[];
  notes?: string[];
  raw_snapshot?: string;
}

export interface SourceStatusData {
  generated_at: string;
  stale?: boolean;
  sources: Record<string, SourceDetail>;
}
