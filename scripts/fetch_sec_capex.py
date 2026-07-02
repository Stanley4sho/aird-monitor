from __future__ import annotations

import os
import re
import statistics
import time
from datetime import date, datetime, timezone
from typing import Any

import requests

COMPANIES = [
    {"ticker": "MSFT", "name": "Microsoft", "cik": "0000789019"},
    {"ticker": "GOOGL", "name": "Alphabet", "cik": "0001652044"},
    {"ticker": "META", "name": "Meta", "cik": "0001326801"},
    {"ticker": "AMZN", "name": "Amazon", "cik": "0001018724"},
]

CAPEX_TAGS = [
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "CapitalExpenditures",
    "PropertyPlantAndEquipmentAdditions",
    "PaymentsToAcquireProductiveAssets",
]

KEYWORDS = [
    "ai infrastructure",
    "artificial intelligence infrastructure",
    "artificial intelligence",
    "data center",
    "datacenter",
    "capacity expansion",
    "capacity expansions",
    "cloud infrastructure",
    "capital expenditures",
    "accelerated computing",
]

SEC_BASE = "https://data.sec.gov"
SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sec_user_agent() -> str:
    return os.environ.get(
        "SEC_USER_AGENT",
        "ai-rdm-monitor contact example@example.com",
    )


def normalize(value: float | None, low: float, high: float) -> float | None:
    if value is None:
        return None
    if value <= low:
        return 0.0
    if value >= high:
        return 100.0
    return (value - low) / (high - low) * 100.0


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def quarter_from_record(record: dict[str, Any]) -> tuple[int, int] | None:
    end_date = parse_iso_date(record.get("end"))
    if end_date is not None:
        return end_date.year, (end_date.month - 1) // 3 + 1

    frame = str(record.get("frame") or "")
    match = re.search(r"CY(\d{4})Q([1-4])", frame)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def request_json(session: requests.Session, url: str, timeout: int = 30) -> dict[str, Any]:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": sec_user_agent(),
            "Accept-Encoding": "gzip, deflate",
        }
    )
    return session


def fetch_sec_capex(timeout: int = 30) -> dict[str, Any]:
    fetched_at = utc_now()
    session = build_session()
    companies: list[dict[str, Any]] = []
    notes: list[str] = []

    for company in COMPANIES:
        try:
            facts = request_json(
                session,
                f"{SEC_BASE}/api/xbrl/companyfacts/CIK{company['cik']}.json",
                timeout=timeout,
            )
            capex = extract_company_capex(company, facts)
            keyword_result = fetch_latest_filing_keywords(company, timeout=timeout)
            capex["positive_keyword_found"] = keyword_result["positive_keyword_found"]
            capex["keyword_source"] = keyword_result.get("keyword_source")
            if keyword_result.get("note"):
                capex["note"] = "; ".join(filter(None, [capex.get("note"), keyword_result["note"]]))
            companies.append(capex)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"{company['ticker']}: {exc}")
            companies.append(company_missing(company, f"fetch failed: {exc}"))
        time.sleep(0.25)

    yoy_values = [company["yoy_growth_pct"] for company in companies if company["yoy_growth_pct"] is not None]
    keyword_values = [
        company["positive_keyword_found"]
        for company in companies
        if company["positive_keyword_found"] is not None
    ]

    median_yoy = statistics.median(yoy_values) if yoy_values else None
    median_score = normalize(median_yoy, -10.0, 40.0)
    positive_ratio = sum(1 for value in yoy_values if value > 0) / len(yoy_values) if yoy_values else None
    keyword_ratio = (
        sum(1 for value in keyword_values if value is True) / len(keyword_values) if keyword_values else None
    )
    keyword_component = keyword_ratio * 100 if keyword_ratio is not None else 50.0
    if keyword_ratio is None:
        notes.append("最新 filing 關鍵字檢查失敗時，關鍵字項暫以中性 50 分處理。")

    if median_score is None or positive_ratio is None:
        score = None
    else:
        score = 0.5 * median_score + 0.3 * (positive_ratio * 100) + 0.2 * keyword_component

    missing = [company["ticker"] for company in companies if company["status"] != "ok"]
    status = "ok" if not missing and score is not None else "partial" if score is not None else "error"

    return {
        "score": round(score, 1) if score is not None else None,
        "status": status,
        "last_updated": fetched_at,
        "source": "SEC EDGAR companyfacts and latest 10-Q/10-K filing text",
        "median_capex_yoy_growth_pct": round(median_yoy, 2) if median_yoy is not None else None,
        "capex_yoy_positive_ratio": round(positive_ratio, 4) if positive_ratio is not None else None,
        "positive_keyword_ratio": round(keyword_ratio, 4) if keyword_ratio is not None else None,
        "companies": companies,
        "source_detail": {
            "status": status,
            "last_updated": fetched_at,
            "source": "https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json",
            "success_count": len(yoy_values),
            "missing": missing,
            "notes": notes,
        },
    }


def extract_company_capex(company: dict[str, str], facts: dict[str, Any]) -> dict[str, Any]:
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    records: list[dict[str, Any]] = []

    for tag_index, tag in enumerate(CAPEX_TAGS):
        units = us_gaap.get(tag, {}).get("units", {})
        for unit_name, unit_records in units.items():
            if unit_name.upper() != "USD":
                continue
            for fact in unit_records:
                normalized = normalize_fact(fact, tag, tag_index)
                if normalized is not None:
                    records.append(normalized)

    if not records:
        return company_missing(company, "no usable capex XBRL tag")

    records.sort(key=lambda item: (item["end"], item.get("filed") or "", -item["tag_index"]))
    deduped: dict[tuple[int, int], dict[str, Any]] = {}
    for record in records:
        quarter = quarter_from_record(record)
        if quarter is None:
            continue
        existing = deduped.get(quarter)
        if existing is None or (record.get("filed") or "") >= (existing.get("filed") or ""):
            deduped[quarter] = record

    ordered = [deduped[key] for key in sorted(deduped)]
    if not ordered:
        return company_missing(company, "capex facts exist but no quarterly period was usable")

    latest = ordered[-1]
    latest_quarter = quarter_from_record(latest)
    previous = ordered[-2] if len(ordered) >= 2 else None
    yoy_record = None
    if latest_quarter is not None:
        yoy_record = deduped.get((latest_quarter[0] - 1, latest_quarter[1]))

    yoy = growth_pct(latest.get("value"), yoy_record.get("value") if yoy_record else None)
    qoq = growth_pct(latest.get("value"), previous.get("value") if previous else None)
    quarter_label = f"{latest_quarter[0]}Q{latest_quarter[1]}" if latest_quarter else latest.get("end")

    status = "ok" if yoy is not None else "partial"
    note = None if yoy is not None else "latest capex found, but YoY comparison quarter is missing"

    return {
        "ticker": company["ticker"],
        "name": company["name"],
        "cik": company["cik"],
        "latest_quarter": quarter_label,
        "latest_capex_usd": latest.get("value"),
        "yoy_growth_pct": round(yoy, 2) if yoy is not None else None,
        "qoq_growth_pct": round(qoq, 2) if qoq is not None else None,
        "positive_keyword_found": None,
        "keyword_source": None,
        "status": status,
        "note": note,
    }


def normalize_fact(fact: dict[str, Any], tag: str, tag_index: int) -> dict[str, Any] | None:
    start = parse_iso_date(fact.get("start"))
    end = parse_iso_date(fact.get("end"))
    if start is None or end is None:
        return None

    duration = (end - start).days + 1
    frame = str(fact.get("frame") or "")
    is_quarter = bool(re.search(r"CY\d{4}Q[1-4]", frame)) or 70 <= duration <= 115
    if not is_quarter:
        return None

    value = fact.get("val")
    if value is None:
        return None
    try:
        numeric_value = abs(float(value))
    except (TypeError, ValueError):
        return None

    form = str(fact.get("form") or "")
    if form not in {"10-Q", "10-K", "10-Q/A", "10-K/A"}:
        return None

    return {
        "tag": tag,
        "tag_index": tag_index,
        "start": fact.get("start"),
        "end": fact.get("end"),
        "value": numeric_value,
        "filed": fact.get("filed"),
        "form": form,
        "fp": fact.get("fp"),
        "frame": frame,
    }


def growth_pct(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return (current / previous - 1.0) * 100.0


def fetch_latest_filing_keywords(company: dict[str, str], timeout: int = 30) -> dict[str, Any]:
    session = requests.Session()
    user_agent = sec_user_agent()
    session.headers.update({"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"})
    submissions_url = f"{SEC_BASE}/submissions/CIK{company['cik']}.json"

    try:
        response = session.get(submissions_url, timeout=timeout)
        response.raise_for_status()
        filings = response.json().get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        accession_numbers = filings.get("accessionNumber", [])
        primary_docs = filings.get("primaryDocument", [])
        for index, form in enumerate(forms):
            if form not in {"10-Q", "10-K"}:
                continue
            accession = accession_numbers[index].replace("-", "")
            document = primary_docs[index]
            cik_no_zero = str(int(company["cik"]))
            url = f"{SEC_ARCHIVES}/{cik_no_zero}/{accession}/{document}"
            doc_response = session.get(url, timeout=timeout)
            doc_response.raise_for_status()
            text = doc_response.text.lower()
            found = any(keyword in text for keyword in KEYWORDS)
            return {
                "positive_keyword_found": found,
                "keyword_source": url,
            }
        return {"positive_keyword_found": None, "note": "no recent 10-Q/10-K filing found"}
    except Exception as exc:  # noqa: BLE001
        return {"positive_keyword_found": None, "note": f"keyword check failed: {exc}"}


def company_missing(company: dict[str, str], note: str) -> dict[str, Any]:
    return {
        "ticker": company["ticker"],
        "name": company["name"],
        "cik": company["cik"],
        "latest_quarter": None,
        "latest_capex_usd": None,
        "yoy_growth_pct": None,
        "qoq_growth_pct": None,
        "positive_keyword_found": None,
        "keyword_source": None,
        "status": "error",
        "note": note,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(fetch_sec_capex(), ensure_ascii=False, indent=2))
