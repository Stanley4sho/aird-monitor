from __future__ import annotations

import csv
import io
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

TW_REVENUE_URL = "https://mopsfin.twse.com.tw/opendata/t187ap05_L.csv"

WATCHLIST = [
    {"ticker": "3037.TW", "code": "3037", "name": "欣興"},
    {"ticker": "2383.TW", "code": "2383", "name": "台光電"},
    {"ticker": "2454.TW", "code": "2454", "name": "聯發科"},
    {"ticker": "2330.TW", "code": "2330", "name": "台積電"},
    {"ticker": "6669.TW", "code": "6669", "name": "緯穎"},
    {"ticker": "3711.TW", "code": "3711", "name": "日月光投控"},
    {"ticker": "2308.TW", "code": "2308", "name": "台達電"},
    {"ticker": "2345.TW", "code": "2345", "name": "智邦"},
    {"ticker": "2376.TW", "code": "2376", "name": "技嘉"},
    {"ticker": "2356.TW", "code": "2356", "name": "英業達"},
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def decode_csv(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "big5", "cp950"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).replace(",", "").replace("%", "").strip()
    if text in {"", "-", "nan", "None"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(value: Any) -> int | None:
    parsed = parse_float(value)
    if parsed is None:
        return None
    return int(parsed)


def normalize(value: float | None, low: float, high: float) -> float | None:
    if value is None:
        return None
    if value <= low:
        return 0.0
    if value >= high:
        return 100.0
    return (value - low) / (high - low) * 100.0


def roc_month_to_iso(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip().replace("/", "")
    if len(text) < 5 or not text.isdigit():
        return None
    roc_year = int(text[:-2])
    month = int(text[-2:])
    return f"{roc_year + 1911:04d}-{month:02d}"


def month_key(value: str | None) -> int:
    if not value or "-" not in value:
        return -1
    year, month = value.split("-", 1)
    return int(year) * 12 + int(month)


def mean(values: list[float]) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def save_raw_snapshot(content: bytes, data_dir: Path, fetched_at: str) -> str:
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    latest_path = raw_dir / "tw_revenue_latest.csv"
    latest_path.write_bytes(content)
    stamp = fetched_at.replace(":", "").replace("-", "").replace("Z", "Z")
    snapshot_path = raw_dir / f"tw_revenue_{stamp}.csv"
    snapshot_path.write_bytes(content)
    return "data/raw/tw_revenue_latest.csv"


def _existing_observations(previous: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for code, rows in (previous or {}).items():
        if isinstance(rows, list):
            result[code] = [row for row in rows if isinstance(row, dict)]
    return result


def fetch_tw_revenue(
    previous_observations: dict[str, Any] | None = None,
    data_dir: Path | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    fetched_at = utc_now()
    observations = _existing_observations(previous_observations)
    headers = {
        "User-Agent": "AI-RDM Monitor GitHub Actions (public data collector)",
        "Accept": "text/csv,*/*",
    }

    try:
        response = requests.get(TW_REVENUE_URL, headers=headers, timeout=timeout)
        response.raise_for_status()
        text = decode_csv(response.content)
    except Exception as exc:  # noqa: BLE001
        return {
            "score": None,
            "status": "error",
            "last_updated": fetched_at,
            "source": TW_REVENUE_URL,
            "companies": _empty_companies("error", f"fetch failed: {exc}"),
            "observations": observations,
            "source_detail": {
                "status": "error",
                "last_updated": fetched_at,
                "source": TW_REVENUE_URL,
                "missing": [item["ticker"] for item in WATCHLIST],
                "notes": [str(exc)],
            },
        }

    raw_snapshot = None
    if data_dir is not None:
        raw_snapshot = save_raw_snapshot(response.content, data_dir, fetched_at)

    rows = list(csv.DictReader(io.StringIO(text)))
    by_code = {str(row.get("公司代號", "")).strip(): row for row in rows}
    companies: list[dict[str, Any]] = []
    missing: list[str] = []

    for item in WATCHLIST:
        row = by_code.get(item["code"])
        if not row:
            missing.append(item["ticker"])
            companies.append(_company_missing(item, "partial", "not found in monthly revenue csv"))
            continue

        data_month = roc_month_to_iso(row.get("資料年月"))
        yoy = parse_float(row.get("營業收入-去年同月增減(%)"))
        mom = parse_float(row.get("營業收入-上月比較增減(%)"))
        current_revenue = parse_int(row.get("營業收入-當月營收"))

        observation = {
            "data_month": data_month,
            "revenue_current": current_revenue,
            "revenue_previous_month": parse_int(row.get("營業收入-上月營收")),
            "revenue_previous_year": parse_int(row.get("營業收入-去年當月營收")),
            "yoy_growth_pct": yoy,
            "mom_growth_pct": mom,
            "fetched_at": fetched_at,
        }

        company_obs = observations.setdefault(item["code"], [])
        company_obs = [old for old in company_obs if old.get("data_month") != data_month]
        company_obs.append(observation)
        company_obs.sort(key=lambda entry: month_key(entry.get("data_month")))
        observations[item["code"]] = company_obs[-18:]

        latest_metrics = compute_company_metrics(item, observations[item["code"]])
        companies.append(latest_metrics)

    yoy_values = [company["yoy_growth_pct"] for company in companies if company["yoy_growth_pct"] is not None]
    accel_values = [
        company["avg_3m_yoy_accelerating"]
        for company in companies
        if company["avg_3m_yoy_accelerating"] is not None
    ]

    yoy_positive_ratio = (
        sum(1 for value in yoy_values if value > 0) / len(yoy_values) if yoy_values else None
    )
    accel_ratio = (
        sum(1 for value in accel_values if value is True) / len(accel_values) if accel_values else None
    )
    median_yoy = statistics.median(yoy_values) if yoy_values else None
    median_score = normalize(median_yoy, -20.0, 50.0)

    notes: list[str] = []
    accel_component = accel_ratio * 100 if accel_ratio is not None else 50.0
    if accel_ratio is None:
        notes.append("三個月平均 YoY 加速需要至少六個月觀測；資料不足時該項暫以中性 50 分處理。")

    if yoy_positive_ratio is None or median_score is None:
        score = None
    else:
        score = 0.4 * (yoy_positive_ratio * 100) + 0.3 * accel_component + 0.3 * median_score

    status = "ok" if not missing and score is not None else "partial" if score is not None else "error"

    source_detail = {
        "status": status,
        "last_updated": fetched_at,
        "source": TW_REVENUE_URL,
        "success_count": len(yoy_values),
        "missing": missing,
        "notes": notes,
    }
    if raw_snapshot:
        source_detail["raw_snapshot"] = raw_snapshot

    return {
        "score": round(score, 1) if score is not None else None,
        "status": status,
        "last_updated": fetched_at,
        "source": TW_REVENUE_URL,
        "median_yoy_growth_pct": round(median_yoy, 2) if median_yoy is not None else None,
        "yoy_positive_ratio": round(yoy_positive_ratio, 4) if yoy_positive_ratio is not None else None,
        "avg_3m_yoy_acceleration_ratio": round(accel_ratio, 4) if accel_ratio is not None else None,
        "companies": companies,
        "observations": observations,
        "source_detail": source_detail,
    }


def compute_company_metrics(item: dict[str, str], observations: list[dict[str, Any]]) -> dict[str, Any]:
    latest = observations[-1] if observations else {}
    yoy_series = [entry.get("yoy_growth_pct") for entry in observations if entry.get("yoy_growth_pct") is not None]

    avg_3m = None
    prev_avg_3m = None
    accelerating = None
    if len(yoy_series) >= 3:
        avg_3m = mean(yoy_series[-3:])
    if len(yoy_series) >= 6:
        prev_avg_3m = mean(yoy_series[-6:-3])
    if avg_3m is not None and prev_avg_3m is not None:
        accelerating = avg_3m > prev_avg_3m

    return {
        "ticker": item["ticker"],
        "code": item["code"],
        "name": item["name"],
        "data_month": latest.get("data_month"),
        "yoy_growth_pct": latest.get("yoy_growth_pct"),
        "mom_growth_pct": latest.get("mom_growth_pct"),
        "avg_3m_yoy_pct": round(avg_3m, 2) if avg_3m is not None else None,
        "avg_3m_yoy_accelerating": accelerating,
        "revenue_current": latest.get("revenue_current"),
        "status": "ok",
    }


def _company_missing(item: dict[str, str], status: str, note: str) -> dict[str, Any]:
    return {
        "ticker": item["ticker"],
        "code": item["code"],
        "name": item["name"],
        "data_month": None,
        "yoy_growth_pct": None,
        "mom_growth_pct": None,
        "avg_3m_yoy_pct": None,
        "avg_3m_yoy_accelerating": None,
        "revenue_current": None,
        "status": status,
        "note": note,
    }


def _empty_companies(status: str, note: str) -> list[dict[str, Any]]:
    return [_company_missing(item, status, note) for item in WATCHLIST]


if __name__ == "__main__":
    import json

    result = fetch_tw_revenue(data_dir=Path("public/data"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
