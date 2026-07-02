from __future__ import annotations

import os
import re
import statistics
import time
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests

COMPANIES = [
    {"ticker": "MSFT", "name": "Microsoft", "cik": "0000789019", "fiscal_year_end_month": 6},
    {"ticker": "GOOGL", "name": "Alphabet", "cik": "0001652044", "fiscal_year_end_month": 12},
    {"ticker": "META", "name": "Meta", "cik": "0001326801", "fiscal_year_end_month": 12},
    {"ticker": "AMZN", "name": "Amazon", "cik": "0001018724", "fiscal_year_end_month": 12},
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
    fiscal_year = record.get("fiscal_year")
    fiscal_quarter = record.get("fiscal_quarter")
    if fiscal_year is not None and fiscal_quarter is not None:
        return int(fiscal_year), int(fiscal_quarter)

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

    expected_companies = len(COMPANIES)
    valid_companies = [
        company
        for company in companies
        if company.get("yoy_growth_pct") is not None and company.get("confidence") in {"high", "medium"}
    ]
    yoy_values = [company["yoy_growth_pct"] for company in valid_companies]
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
        raw_score = None
        score = None
    else:
        raw_score = 0.5 * median_score + 0.3 * (positive_ratio * 100) + 0.2 * keyword_component
        coverage = len(valid_companies) / expected_companies
        score = raw_score * coverage + 50.0 * (1.0 - coverage)
        if len(valid_companies) < 2:
            score = min(score, 55.0)

    coverage = len(valid_companies) / expected_companies
    missing = [company["ticker"] for company in companies if company.get("confidence") in {"low", "missing"}]
    status = "ok" if not missing and score is not None else "partial" if score is not None else "error"
    if len(valid_companies) < 2 and score is not None:
        status = "partial"

    return {
        "score": round(score, 1) if score is not None else None,
        "raw_capex_score": round(raw_score, 1) if raw_score is not None else None,
        "coverage": round(coverage, 4),
        "valid_companies": len(valid_companies),
        "expected_companies": expected_companies,
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
            "success_count": len(valid_companies),
            "missing": missing,
            "notes": notes,
            "coverage": round(coverage, 4),
            "valid_companies": len(valid_companies),
            "expected_companies": expected_companies,
            "raw_capex_score": round(raw_score, 1) if raw_score is not None else None,
            "tag_usage": {company["ticker"]: company.get("source_tag") for company in companies},
            "company_confidence": {company["ticker"]: company.get("confidence") for company in companies},
        },
    }


def extract_company_capex(company: dict[str, str], facts: dict[str, Any]) -> dict[str, Any]:
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    fiscal_year_end_month = int(company["fiscal_year_end_month"])
    tag_series: list[dict[str, Any]] = []

    for tag_index, tag in enumerate(CAPEX_TAGS):
        units = us_gaap.get(tag, {}).get("units", {})
        records: list[dict[str, Any]] = []
        for unit_name, unit_records in units.items():
            if unit_name.upper() != "USD":
                continue
            for fact in unit_records:
                normalized = normalize_fact(fact, tag, tag_index, fiscal_year_end_month)
                if normalized is not None:
                    records.append(normalized)
        records = dedupe_facts(records)
        quarters = derive_quarters(records)
        if quarters:
            tag_series.append(
                {
                    "tag": tag,
                    "tag_index": tag_index,
                    "quarters": quarters,
                    "latest_key": max(quarters),
                }
            )

    if not tag_series:
        return company_missing(company, "no usable capex XBRL tag")

    tag_series.sort(key=lambda item: (item["latest_key"][0], item["latest_key"][1], -item["tag_index"]), reverse=True)
    chosen = tag_series[0]
    quarters = chosen["quarters"]
    add_growth_metrics(quarters)

    ordered = [quarters[key] for key in sorted(quarters)]
    if not ordered:
        return company_missing(company, "capex facts exist but no quarterly period was usable")

    latest = ordered[-1]
    latest_quarter = quarter_from_record(latest)
    quarter_label = f"FY{latest_quarter[0]}Q{latest_quarter[1]}" if latest_quarter else latest.get("period_end")
    yoy = latest.get("yoy_growth_pct")
    qoq = latest.get("qoq_growth_pct")
    recent_quarters = [serialize_quarter(record) for record in ordered[-4:]]
    confidence = company_confidence(latest, quarters)

    status = "ok" if confidence in {"high", "medium"} else "partial"
    note = None
    if confidence == "missing":
        status = "error"
        note = "latest capex found, but reliable YoY comparison quarter is missing"
    elif confidence == "low":
        note = "latest capex exists but confidence is low"

    return {
        "ticker": company["ticker"],
        "name": company["name"],
        "cik": company["cik"],
        "fiscal_year_end_month": fiscal_year_end_month,
        "latest_quarter": quarter_label,
        "fiscal_year": latest.get("fiscal_year"),
        "fiscal_quarter": latest.get("fiscal_quarter"),
        "period_start": latest.get("period_start"),
        "period_end": latest.get("period_end"),
        "latest_capex_usd": latest.get("capex_usd"),
        "yoy_growth_pct": yoy,
        "qoq_growth_pct": qoq,
        "source_tag": chosen["tag"],
        "confidence": confidence,
        "recent_quarters": recent_quarters,
        "positive_keyword_found": None,
        "keyword_source": None,
        "status": status,
        "note": note,
    }


def normalize_fact(
    fact: dict[str, Any],
    tag: str,
    tag_index: int,
    fiscal_year_end_month: int,
) -> dict[str, Any] | None:
    start = parse_iso_date(fact.get("start"))
    end = parse_iso_date(fact.get("end"))
    if start is None or end is None:
        return None

    duration = (end - start).days + 1
    frame = str(fact.get("frame") or "")
    fiscal_year, fiscal_quarter = fiscal_year_quarter(end, fiscal_year_end_month)
    period_type = classify_period(start, end, fiscal_year, fiscal_quarter, fiscal_year_end_month)
    if period_type is None:
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
        "start_date": start,
        "end_date": end,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "duration_days": duration,
        "period_type": period_type,
        "fiscal_year": fiscal_year,
        "fiscal_quarter": fiscal_quarter,
        "value": numeric_value,
        "filed": fact.get("filed"),
        "form": form,
        "fp": fact.get("fp"),
        "fy": fact.get("fy"),
        "frame": frame,
    }


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def fiscal_year_quarter(end_date: date, fiscal_year_end_month: int) -> tuple[int, int]:
    fiscal_year = end_date.year if end_date.month <= fiscal_year_end_month else end_date.year + 1
    fiscal_quarter = ((end_date.month - fiscal_year_end_month - 1) % 12) // 3 + 1
    return fiscal_year, fiscal_quarter


def fiscal_year_start(fiscal_year: int, fiscal_year_end_month: int) -> date:
    start_month = fiscal_year_end_month % 12 + 1
    start_year = fiscal_year - 1 if start_month != 1 else fiscal_year
    return date(start_year, start_month, 1)


def quarter_bounds(fiscal_year: int, fiscal_quarter: int, fiscal_year_end_month: int) -> tuple[date, date]:
    start = add_months(fiscal_year_start(fiscal_year, fiscal_year_end_month), 3 * (fiscal_quarter - 1))
    end = add_months(start, 3) - timedelta(days=1)
    return start, end


def date_close(left: date, right: date, tolerance_days: int = 3) -> bool:
    return abs((left - right).days) <= tolerance_days


def classify_period(
    start: date,
    end: date,
    fiscal_year: int,
    fiscal_quarter: int,
    fiscal_year_end_month: int,
) -> str | None:
    duration = (end - start).days + 1
    expected_start, expected_end = quarter_bounds(fiscal_year, fiscal_quarter, fiscal_year_end_month)
    if 70 <= duration <= 115 and date_close(start, expected_start) and date_close(end, expected_end):
        return "quarter"

    fy_start = fiscal_year_start(fiscal_year, fiscal_year_end_month)
    if not date_close(start, fy_start):
        return None
    if fiscal_quarter == 2 and 160 <= duration <= 205:
        return "ytd_6m"
    if fiscal_quarter == 3 and 250 <= duration <= 295:
        return "ytd_9m"
    if fiscal_quarter == 4 and 330 <= duration <= 380:
        return "annual"
    return None


def dedupe_facts(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for record in records:
        # Keep direct quarter, YTD, and annual facts separate even when they share
        # the same fiscal period and end date.
        key = (
            record["tag"],
            record["fiscal_year"],
            record["fiscal_quarter"],
            record["period_type"],
            record["start"],
            record["end"],
        )
        existing = deduped.get(key)
        if existing is None or (record.get("filed") or "") >= (existing.get("filed") or ""):
            deduped[key] = record
    return list(deduped.values())


def derive_quarters(records: list[dict[str, Any]]) -> dict[tuple[int, int], dict[str, Any]]:
    facts_by_type: dict[tuple[int, str], dict[str, Any]] = {}
    quarters: dict[tuple[int, int], dict[str, Any]] = {}

    for record in sorted(records, key=lambda item: (item.get("filed") or "", item["end"])):
        period_key = (record["fiscal_year"], record["period_type"])
        existing = facts_by_type.get(period_key)
        if existing is None or (record.get("filed") or "") >= (existing.get("filed") or ""):
            facts_by_type[period_key] = record
        if record["period_type"] == "quarter":
            add_quarter_candidate(quarters, record["fiscal_year"], record["fiscal_quarter"], record, record["value"], "direct", "high")

    for fiscal_year in sorted({record["fiscal_year"] for record in records}):
        q1 = quarters.get((fiscal_year, 1))
        ytd_6m = facts_by_type.get((fiscal_year, "ytd_6m"))
        ytd_9m = facts_by_type.get((fiscal_year, "ytd_9m"))
        annual = facts_by_type.get((fiscal_year, "annual"))

        if q1 and ytd_6m:
            add_derived_quarter(quarters, fiscal_year, 2, ytd_6m, q1, "ytd_6m_minus_q1")
        if ytd_6m and ytd_9m:
            add_derived_quarter(quarters, fiscal_year, 3, ytd_9m, ytd_6m, "ytd_9m_minus_ytd_6m")
        if ytd_9m and annual:
            add_derived_quarter(quarters, fiscal_year, 4, annual, ytd_9m, "annual_minus_ytd_9m")

    return quarters


def add_derived_quarter(
    quarters: dict[tuple[int, int], dict[str, Any]],
    fiscal_year: int,
    fiscal_quarter: int,
    cumulative: dict[str, Any],
    prior: dict[str, Any],
    derivation: str,
) -> None:
    value = cumulative["value"] - prior["capex_usd" if "capex_usd" in prior else "value"]
    if value < 0:
        return
    add_quarter_candidate(quarters, fiscal_year, fiscal_quarter, cumulative, value, derivation, "medium")


def add_quarter_candidate(
    quarters: dict[tuple[int, int], dict[str, Any]],
    fiscal_year: int,
    fiscal_quarter: int,
    source: dict[str, Any],
    value: float,
    derivation: str,
    confidence: str,
) -> None:
    key = (fiscal_year, fiscal_quarter)
    source_start, source_end = quarter_bounds(fiscal_year, fiscal_quarter, fiscal_year_quarter_end_month(source))
    candidate = {
        "fiscal_year": fiscal_year,
        "fiscal_quarter": fiscal_quarter,
        "period_start": source_start.isoformat(),
        "period_end": source_end.isoformat(),
        "capex_usd": value,
        "source_tag": source["tag"],
        "tag_index": source["tag_index"],
        "confidence": confidence,
        "period_type": "quarter" if derivation == "direct" else "derived_ytd",
        "derived_from_ytd": derivation != "direct",
        "derivation": derivation,
        "filed": source.get("filed"),
        "form": source.get("form"),
        "frame": source.get("frame"),
        "source_start": source.get("start"),
        "source_end": source.get("end"),
        "source_duration_days": source.get("duration_days"),
    }
    existing = quarters.get(key)
    if existing is None or quarter_candidate_preferred(candidate, existing):
        quarters[key] = candidate


def fiscal_year_quarter_end_month(record: dict[str, Any]) -> int:
    end_date = parse_iso_date(record["end"])
    fiscal_year = int(record["fiscal_year"])
    fiscal_quarter = int(record["fiscal_quarter"])
    if end_date is None:
        return 12
    # Invert fiscal_year_quarter for the small watchlist without storing extra
    # company metadata on every fact.
    for month in (6, 12):
        if fiscal_year_quarter(end_date, month) == (fiscal_year, fiscal_quarter):
            return month
    return 12


def quarter_candidate_preferred(candidate: dict[str, Any], existing: dict[str, Any]) -> bool:
    confidence_rank = {"high": 0, "medium": 1, "low": 2, "missing": 3}
    candidate_key = (
        confidence_rank.get(candidate["confidence"], 9),
        candidate["tag_index"],
        0 if not candidate["derived_from_ytd"] else 1,
        candidate.get("filed") or "",
    )
    existing_key = (
        confidence_rank.get(existing["confidence"], 9),
        existing["tag_index"],
        0 if not existing["derived_from_ytd"] else 1,
        existing.get("filed") or "",
    )
    return candidate_key[:3] < existing_key[:3] or (
        candidate_key[:3] == existing_key[:3] and candidate_key[3] >= existing_key[3]
    )


def add_growth_metrics(quarters: dict[tuple[int, int], dict[str, Any]]) -> None:
    for key, record in quarters.items():
        previous = quarters.get(previous_quarter_key(key))
        yoy_base = quarters.get((key[0] - 1, key[1]))
        qoq = growth_pct(record.get("capex_usd"), previous.get("capex_usd") if previous else None)
        yoy = growth_pct(record.get("capex_usd"), yoy_base.get("capex_usd") if yoy_base else None)
        record["qoq_growth_pct"] = round(qoq, 2) if qoq is not None else None
        record["yoy_growth_pct"] = round(yoy, 2) if yoy is not None else None


def previous_quarter_key(key: tuple[int, int]) -> tuple[int, int]:
    fiscal_year, fiscal_quarter = key
    if fiscal_quarter == 1:
        return fiscal_year - 1, 4
    return fiscal_year, fiscal_quarter - 1


def company_confidence(latest: dict[str, Any], quarters: dict[tuple[int, int], dict[str, Any]]) -> str:
    latest_key = (latest["fiscal_year"], latest["fiscal_quarter"])
    yoy_base = quarters.get((latest_key[0] - 1, latest_key[1]))
    if latest.get("yoy_growth_pct") is None or yoy_base is None:
        return "missing"
    if latest.get("confidence") == "high" and yoy_base.get("confidence") == "high":
        return "high"
    if latest.get("confidence") in {"high", "medium"} and yoy_base.get("confidence") in {"high", "medium"}:
        return "medium"
    return "low"


def serialize_quarter(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "fiscal_year": record.get("fiscal_year"),
        "fiscal_quarter": record.get("fiscal_quarter"),
        "period_start": record.get("period_start"),
        "period_end": record.get("period_end"),
        "capex_usd": record.get("capex_usd"),
        "yoy_growth_pct": record.get("yoy_growth_pct"),
        "qoq_growth_pct": record.get("qoq_growth_pct"),
        "source_tag": record.get("source_tag"),
        "confidence": record.get("confidence"),
        "period_type": record.get("period_type"),
        "derived_from_ytd": record.get("derived_from_ytd"),
        "derivation": record.get("derivation"),
        "filed": record.get("filed"),
        "form": record.get("form"),
        "source_start": record.get("source_start"),
        "source_end": record.get("source_end"),
        "source_duration_days": record.get("source_duration_days"),
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
