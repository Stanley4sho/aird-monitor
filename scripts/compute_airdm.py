from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clamp_score(value: float | int | None) -> float:
    if value is None:
        return 50.0
    return round(max(0.0, min(100.0, float(value))), 1)


def status_from_score(score: float) -> tuple[str, str]:
    if score >= 70:
        return "強擴張", "strong_expansion"
    if score >= 55:
        return "溫和擴張", "moderate_expansion"
    if score >= 45:
        return "中性震盪", "neutral"
    if score >= 30:
        return "放緩", "slowdown"
    return "明顯轉弱", "weak"


def fallback_component(
    name: str,
    result: dict[str, Any],
    old_latest: dict[str, Any] | None,
    stale_components: list[str],
) -> float:
    score = result.get("score")
    if score is not None:
        return clamp_score(score)

    previous = (old_latest or {}).get("subscores", {}).get(name)
    if previous is not None:
        stale_components.append(name)
        return clamp_score(previous)

    stale_components.append(name)
    return 50.0


def build_latest(
    supply: dict[str, Any],
    capex: dict[str, Any],
    market: dict[str, Any],
    old_latest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stale_components: list[str] = []
    supply_score = fallback_component("supply_chain_revenue", supply, old_latest, stale_components)
    capex_score = fallback_component("hyperscaler_capex", capex, old_latest, stale_components)
    market_score = fallback_component("market_confirmation", market, old_latest, stale_components)

    total = round(0.45 * supply_score + 0.35 * capex_score + 0.20 * market_score, 1)
    status, status_band = status_from_score(total)

    slowdown = total < 45 and supply_score < 50 and capex_score < 50
    bubble_divergence = market_score > 70 and ((supply_score + capex_score) / 2) < 50

    latest = {
        "as_of": utc_now(),
        "ai_rdm_score": total,
        "aird_m_score": total,
        "status": status,
        "status_band": status_band,
        "subscores": {
            "supply_chain_revenue": supply_score,
            "hyperscaler_capex": capex_score,
            "market_confirmation": market_score,
        },
        "warnings": {
            "slowdown": slowdown,
            "bubble_divergence": bubble_divergence,
        },
        "interpretation_for_00988a": interpretation(total, supply_score, capex_score, market_score, slowdown, bubble_divergence),
        "source_status": {
            "tw_revenue": source_status(supply, "supply_chain_revenue", stale_components),
            "sec_capex": source_status(capex, "hyperscaler_capex", stale_components),
            "market_prices": source_status(market, "market_confirmation", stale_components),
        },
        "stale": bool(stale_components),
        "stale_components": stale_components,
        "details": {
            "supply_chain_revenue": {
                "score": supply_score,
                "median_yoy_growth_pct": supply.get("median_yoy_growth_pct"),
                "yoy_positive_ratio": supply.get("yoy_positive_ratio"),
                "avg_3m_yoy_acceleration_ratio": supply.get("avg_3m_yoy_acceleration_ratio"),
                "companies": supply.get("companies", []),
            },
            "hyperscaler_capex": {
                "score": capex_score,
                "raw_capex_score": capex.get("raw_capex_score"),
                "coverage": capex.get("coverage"),
                "valid_companies": capex.get("valid_companies"),
                "expected_companies": capex.get("expected_companies"),
                "median_capex_yoy_growth_pct": capex.get("median_capex_yoy_growth_pct"),
                "capex_yoy_positive_ratio": capex.get("capex_yoy_positive_ratio"),
                "positive_keyword_ratio": capex.get("positive_keyword_ratio"),
                "companies": capex.get("companies", []),
            },
            "market_confirmation": {
                "score": market_score,
                "basket_return_20d_pct": market.get("basket_return_20d_pct"),
                "benchmark_return_20d_pct": market.get("benchmark_return_20d_pct"),
                "spread_pct": market.get("spread_pct"),
                "benchmark": market.get("benchmark"),
                "tickers": market.get("tickers", []),
            },
        },
        "formulas": {
            "ai_rdm": "AI-RDM = 45% * Supply Chain Revenue Momentum + 35% * Hyperscaler Capex Momentum + 20% * Market Confirmation Spread",
            "supply_chain_revenue": "40% * YoY>0 比例 + 30% * 3-month average YoY 加速比例 + 30% * median YoY 標準化分數",
            "hyperscaler_capex": "raw_capex_score = 50% * median capex YoY 標準化分數 + 30% * capex YoY>0 比例 + 20% * AI/datacenter/capacity 關鍵字比例；final = raw * coverage + 50 * (1 - coverage)",
            "market_confirmation": "Spread = AI hardware basket 20D return - QQQ 20D return；-10% 到 +10% 線性映射為 0 到 100",
        },
        "disclaimer": "本網站僅供研究與教育用途，不構成任何投資建議、買賣建議或績效保證。",
    }
    return latest


def source_status(result: dict[str, Any], component: str, stale_components: list[str]) -> str:
    if component in stale_components:
        return "stale"
    return result.get("status") or "unknown"


def interpretation(
    total: float,
    supply: float,
    capex: float,
    market: float,
    slowdown: bool,
    bubble_divergence: bool,
) -> str:
    if bubble_divergence:
        return "目前價格表現強於基本面，需留意短線泡沫化與回檔風險。"
    if slowdown:
        return "目前雲端 capex 與供應鏈營收同步轉弱，對 00988A 偏負面。"
    if total >= 70:
        return "目前 AI 基建需求仍在擴張，對 00988A 的產業主軸偏正面，但仍需觀察市場價格是否過熱。"
    if total >= 55:
        return "目前 AI 基建需求維持溫和擴張，對 00988A 產業主軸偏正面，但動能尚未全面同步。"
    if total >= 45:
        return "目前 AI 基建實需處於中性震盪，00988A 的產業主軸仍需等待供應鏈營收與 capex 重新確認。"
    if supply < 50 and capex < 50:
        return "目前供應鏈營收與雲端 capex 同步偏弱，對 00988A 的產業主軸偏負面。"
    if market > 60 and (supply + capex) / 2 < 55:
        return "目前市場價格較強，但基本面動能尚未明顯跟上，需留意估值與情緒面的拉扯。"
    return "目前 AI 基建實需動能偏弱，對 00988A 需保守觀察後續營收與 capex 是否回升。"


def history_point(latest: dict[str, Any]) -> dict[str, Any]:
    return {
        "as_of": latest["as_of"],
        "ai_rdm_score": latest["ai_rdm_score"],
        "supply_chain_revenue": latest["subscores"]["supply_chain_revenue"],
        "hyperscaler_capex": latest["subscores"]["hyperscaler_capex"],
        "market_confirmation": latest["subscores"]["market_confirmation"],
    }
