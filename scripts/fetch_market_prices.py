from __future__ import annotations

import csv
import io
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

TICKERS = ["NVDA", "AMD", "AVGO", "MU", "TSM", "ASML", "ANET", "VRT", "SMCI", "LITE"]
BENCHMARK = "QQQ"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize(value: float | None, low: float, high: float) -> float | None:
    if value is None:
        return None
    if value <= low:
        return 0.0
    if value >= high:
        return 100.0
    return (value - low) / (high - low) * 100.0


def headers() -> dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 AI-RDM Monitor GitHub Actions",
        "Accept": "application/json,text/csv,*/*",
    }


def fetch_market_prices(timeout: int = 30) -> dict[str, Any]:
    fetched_at = utc_now()
    tickers: list[dict[str, Any]] = []
    notes: list[str] = []

    for ticker in TICKERS:
        result = fetch_one_ticker(ticker, timeout=timeout)
        if result["status"] != "ok":
            notes.append(f"{ticker}: {result.get('note', 'missing')}")
        tickers.append(result)

    benchmark = fetch_one_ticker(BENCHMARK, timeout=timeout)
    if benchmark["status"] != "ok":
        notes.append(f"{BENCHMARK}: {benchmark.get('note', 'missing')}")

    returns = [item["return_20d_pct"] for item in tickers if item["return_20d_pct"] is not None]
    basket_return = statistics.mean(returns) if returns else None
    benchmark_return = benchmark["return_20d_pct"]
    spread = basket_return - benchmark_return if basket_return is not None and benchmark_return is not None else None
    score = normalize(spread, -10.0, 10.0)

    missing = [item["ticker"] for item in tickers if item["status"] != "ok"]
    if benchmark["status"] != "ok":
        missing.append(BENCHMARK)

    status = "ok" if not missing and score is not None else "partial" if score is not None else "error"

    return {
        "score": round(score, 1) if score is not None else None,
        "status": status,
        "last_updated": fetched_at,
        "source": "Stooq CSV, Yahoo Finance chart endpoint, Nasdaq historical fallback",
        "basket_return_20d_pct": round(basket_return, 2) if basket_return is not None else None,
        "benchmark_return_20d_pct": round(benchmark_return, 2) if benchmark_return is not None else None,
        "spread_pct": round(spread, 2) if spread is not None else None,
        "benchmark": benchmark,
        "tickers": tickers,
        "source_detail": {
            "status": status,
            "last_updated": fetched_at,
            "source": "Stooq / Yahoo Finance chart / Nasdaq historical",
            "success_count": len(returns),
            "missing": missing,
            "notes": notes,
        },
    }


def fetch_one_ticker(ticker: str, timeout: int = 30) -> dict[str, Any]:
    errors: list[str] = []
    for source_name, fetcher in (
        ("stooq", fetch_stooq_prices),
        ("yahoo", fetch_yahoo_prices),
        ("nasdaq", fetch_nasdaq_prices),
    ):
        try:
            prices = fetcher(ticker, timeout=timeout)
            metric = return_20d(prices)
            if metric is None:
                errors.append(f"{source_name}: fewer than 21 prices")
                continue
            last = prices[-1]
            return {
                "ticker": ticker,
                "return_20d_pct": round(metric, 2),
                "last_close": last["close"],
                "last_date": last["date"],
                "source": source_name,
                "status": "ok",
            }
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{source_name}: {exc}")

    return {
        "ticker": ticker,
        "return_20d_pct": None,
        "last_close": None,
        "last_date": None,
        "source": None,
        "status": "error",
        "note": "; ".join(errors[-3:]),
    }


def return_20d(prices: list[dict[str, Any]]) -> float | None:
    clean = [price for price in prices if price.get("close") is not None]
    if len(clean) < 21:
        return None
    return (clean[-1]["close"] / clean[-21]["close"] - 1.0) * 100.0


def fetch_stooq_prices(ticker: str, timeout: int = 30) -> list[dict[str, Any]]:
    symbol = f"{ticker.lower()}.us"
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=140)
    url = (
        "https://stooq.com/q/d/l/"
        f"?s={symbol}&i=d&d1={start:%Y%m%d}&d2={end:%Y%m%d}"
    )
    response = requests.get(url, headers=headers(), timeout=timeout)
    response.raise_for_status()
    text = response.text.strip()
    if not text.startswith("Date,"):
        raise ValueError("unexpected response, not CSV")
    reader = csv.DictReader(io.StringIO(text))
    prices = []
    for row in reader:
        try:
            prices.append({"date": row["Date"], "close": float(row["Close"])})
        except (KeyError, TypeError, ValueError):
            continue
    return prices


def fetch_yahoo_prices(ticker: str, timeout: int = 30) -> list[dict[str, Any]]:
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?range=4mo&interval=1d&events=history"
    response = requests.get(url, headers=headers(), timeout=timeout)
    response.raise_for_status()
    data = response.json()
    result = (data.get("chart", {}).get("result") or [None])[0]
    if not result:
        raise ValueError("empty yahoo chart result")
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators", {}).get("quote") or [{}])[0]) or {}
    adjclose = ((result.get("indicators", {}).get("adjclose") or [{}])[0]).get("adjclose") or []
    closes = adjclose or quote.get("close") or []
    prices = []
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        day = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        prices.append({"date": day, "close": float(close)})
    return prices


def fetch_nasdaq_prices(ticker: str, timeout: int = 30) -> list[dict[str, Any]]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=140)
    url = (
        f"https://api.nasdaq.com/api/quote/{ticker}/historical"
        f"?assetclass=stocks&fromdate={start:%Y-%m-%d}&todate={end:%Y-%m-%d}&limit=1000"
    )
    nasdaq_headers = headers() | {
        "Origin": "https://www.nasdaq.com",
        "Referer": "https://www.nasdaq.com/",
    }
    response = requests.get(url, headers=nasdaq_headers, timeout=timeout)
    response.raise_for_status()
    rows = response.json().get("data", {}).get("tradesTable", {}).get("rows", [])
    prices = []
    for row in rows:
        close = str(row.get("close", "")).replace("$", "").replace(",", "")
        raw_date = row.get("date")
        try:
            parsed_date = datetime.strptime(raw_date, "%m/%d/%Y").date().isoformat()
            prices.append({"date": parsed_date, "close": float(close)})
        except (TypeError, ValueError):
            continue
    prices.sort(key=lambda item: item["date"])
    return prices


if __name__ == "__main__":
    import json

    print(json.dumps(fetch_market_prices(), ensure_ascii=False, indent=2))
